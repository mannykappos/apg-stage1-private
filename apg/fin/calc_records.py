"""Immutable calculation records: run a financial calculation over pinned records and store the result; replay it later; explain it; compare two runs.
Blueprint: Section 05 section 13 (formula version, input snapshot, reproducibility), PG-PC-AC-16, 17, 18, 20, 21; CAP-31.

This sits on the M2 reproducibility module (apg/repro.py): a record pins the exact revision and payload hash of every input, the formula id and version and a hash of the code that
ran, the parameters (including the policy version) and the canonical result.  M4 adds:
  * the formula registry for the financial core, whose code hash covers EVERY calculation module (so changing any of them without bumping a formula version is caught on replay as
    FORMULA_DRIFT, not silently accepted);
  * `gather`-based runs (which records are pinned is decided by the same project rule the calculations use);
  * `check_record`: replay + figure invariants + a cross-check that the revisions the figure cites are the revisions that were pinned;
  * `diff_records`: says whether two results differ because of INPUT changes, RULE changes (formula or policy) or neither (PG-PC-AC-18)."""
import hashlib, inspect
from .. import canon, repro
from ..repro import FormulaRegistry, InputRef, ReproError, pin_latest
from . import (bridge, cash_states, cashview, commitments, costs, figure, fmath, forecast, gather as G, margins, policy as P, revenue, snap)
from .figure import validate_figure, FigureError, FigureBuilder

MODULES = (figure, fmath, P, snap, costs, commitments, revenue, forecast, margins, cash_states, cashview, bridge)


def code_hash():
    h = hashlib.sha256()
    for m in MODULES:
        h.update(inspect.getsource(m).encode('utf-8'))
    return h.hexdigest()


def _facts(inputs, params):
    return snap.Facts(inputs, params)


def f_actual_cost(inputs, params):
    return costs.build_actual(_facts(inputs, params), params['project'], params['as_of'], view='actual')


def f_commitments(inputs, params):
    return commitments.build_commitments(_facts(inputs, params), params['project'], params['as_of'])


def f_revenue(inputs, params):
    return revenue.build_revenue(_facts(inputs, params), params['project'], params['as_of'])


def f_forecast(inputs, params):
    return forecast.build_forecast(_facts(inputs, params), params['project'], params['as_of'])


def f_recognised(inputs, params):
    return margins.build_recognised(_facts(inputs, params), params['project'], params['as_of'])


def f_cash_position(inputs, params):
    F = _facts(inputs, params)
    what = params.get('what')
    if what == 'retention':
        return cashview.build_retention(F, params['project'], params['as_of'])
    if what == 'security':
        return cashview.build_security(F, params['project'], params['as_of'])
    if what in ('retention_carrying', 'security_carrying'):
        return cashview.build_carrying(F, params['project'], params['as_of'], what.split('_')[0])
    raise ValueError('unknown cash position part: %r' % (what,))


def f_cash_adjusted(inputs, params):
    return cashview.build_cash_adjusted(_facts(inputs, params), params['project'], params['as_of'])


def f_margin_pct(inputs, params):
    """Percentage of a stored margin result.  inputs: the margin record and the revenue basis record it names."""
    m = inputs['repro_record/' + params['margin_run']]['result']
    if params['denominator'] == 'recognised_revenue':
        rev = m['classified'].get('recognised_revenue_cents')
        label = 'RECOGNISED_REVENUE'
    elif params['denominator'] == 'forecast_revenue':
        rev = m['classified'].get('ffr_cents')
        label = 'FORECAST_REVENUE'
    else:                                                  # a selector nobody defined is refused, never quietly replaced by another denominator
        fb = FigureBuilder(params['name'], m['view'], 'fin.margin_pct', 1, m['scope'], m['as_of'], {'version': m['policy']['version'], '_approved': m['policy']['approved']})
        return fb.cannot('UNKNOWN_DENOMINATOR:' + str(params['denominator']))
    return margins.pct_figure(params['name'], m, rev, label)


def f_bridge(inputs, params):
    return bridge.build_bridge(inputs['repro_record/' + params['older']]['result'], inputs['repro_record/' + params['newer']]['result'])


FORMULAS = {'fin.actual_cost': f_actual_cost, 'fin.commitments': f_commitments, 'fin.revenue': f_revenue, 'fin.forecast': f_forecast, 'fin.recognised_margin': f_recognised,
            'fin.cash_position': f_cash_position, 'fin.cash_adjusted': f_cash_adjusted, 'fin.margin_pct': f_margin_pct, 'fin.movement_bridge': f_bridge}
VERSIONS = {k: 1 for k in FORMULAS}


def fin_registry(registry=None):
    reg = registry or FormulaRegistry()
    h = code_hash()
    for fid, fn in FORMULAS.items():
        reg.register(fid, VERSIONS[fid], fn, code_hash=h)
    return reg


def run_calc(scoped, registry, clock, formula_id, project, as_of, policy_version, extra=None):
    """Pin the records, run, store.  -> the stored record payload (its 'result' is the figure)."""
    refs, params = G.gather(scoped, project, as_of, policy_version, extra)
    rec = repro.run(scoped, registry, clock, formula_id, VERSIONS[formula_id], refs, params)
    validate_figure(rec['result'])
    return rec


def run_derived(scoped, registry, clock, formula_id, project, run_keys, extra):
    """Calculations whose inputs are earlier stored results (percentages, the movement bridge)."""
    refs = [pin_latest(scoped, repro.KIND, k) for k in run_keys]
    params = {'project': project}
    params.update(extra)
    rec = repro.run(scoped, registry, clock, formula_id, VERSIONS[formula_id], refs, params)
    validate_figure(rec['result'])
    return rec


def run_bridge(scoped, registry, clock, older_run, newer_run):
    project = scoped.get(repro.KIND, newer_run).payload['result']['scope'].get('project')
    return run_derived(scoped, registry, clock, 'fin.movement_bridge', project, [older_run, newer_run], {'older': older_run, 'newer': newer_run})


def run_pct(scoped, registry, clock, margin_run, denominator, name):
    project = scoped.get(repro.KIND, margin_run).payload['result']['scope'].get('project')
    return run_derived(scoped, registry, clock, 'fin.margin_pct', project, [margin_run], {'margin_run': margin_run, 'denominator': denominator, 'name': name})


def check_record(scoped, registry, run_key):
    """Everything a reviewer can verify about a stored calculation, without trusting it:
       replay            re-run from the pinned revisions and compare the result hash (repro.replay)
       figure_valid      the stored figure obeys the figure rules
       pins_consistent   every revision the params claim was pinned is the revision that was pinned
       drift             inputs that have NEWER revisions now (informational: the old result stays valid for what it pinned)"""
    rec = scoped.get(repro.KIND, run_key)
    if rec is None:
        return {'replay': repro.ReplayResult(False, 'RECORD_MISSING', run_key), 'figure_valid': False, 'pins_consistent': False, 'drift': []}
    p = rec.payload
    rp = repro.replay(scoped, registry, run_key)
    try:
        validate_figure(p['result'])
        valid = True
    except (FigureError, KeyError, TypeError):
        valid = False
    claimed = p['params'].get('pins')
    pinned = {f"{i['kind']}/{i['key']}": i['revision'] for i in p['inputs']}
    consistent = True if claimed is None else all(pinned.get(k) == v for k, v in claimed.items()) and set(claimed) <= set(pinned)
    return {'replay': rp, 'figure_valid': valid, 'pins_consistent': consistent, 'drift': repro.drift_report(scoped, run_key)}


def diff_records(a, b):
    """-> why two stored results differ.  a, b: record payloads.  Rule changes (formula version, code, policy version/revision) are reported apart from input changes."""
    rules, inputs = [], []
    if (a['formula_id'], a['formula_version']) != (b['formula_id'], b['formula_version']):
        rules.append('formula %s v%s -> %s v%s' % (a['formula_id'], a['formula_version'], b['formula_id'], b['formula_version']))
    elif a['formula_code_hash'] != b['formula_code_hash']:
        rules.append('formula code changed under the same version')
    ia = {f"{i['kind']}/{i['key']}": i for i in a['inputs']}
    ib = {f"{i['kind']}/{i['key']}": i for i in b['inputs']}
    for k in sorted(set(ia) | set(ib)):
        x, y = ia.get(k), ib.get(k)
        if x == y:
            continue
        if k.startswith(P.POLICY_KIND + '/'):
            rules.append('policy ' + k.split('/', 1)[1] + ('' if x and y else ' added or removed') + (' revision %s -> %s' % (x['revision'], y['revision']) if x and y else ''))
        else:
            inputs.append({'input': k, 'from': None if x is None else x['revision'], 'to': None if y is None else y['revision']})
    for key in ('as_of', 'project', 'forecast_version', 'what'):
        if a['params'].get(key) != b['params'].get(key):
            inputs.append({'parameter': key, 'from': a['params'].get(key), 'to': b['params'].get(key)})
    return {'rule_changes': rules, 'input_changes': inputs, 'result_changed': a['result_hash'] != b['result_hash'],
            'kind': 'identical' if not rules and not inputs else ('rule' if rules and not inputs else ('input' if inputs and not rules else 'both'))}


def explain(scoped, run_key):
    """-> {'figure', 'pins', 'history'}: the figure with, for every record it cites, the pinned revision and the earlier revisions that were superseded."""
    rec = scoped.get(repro.KIND, run_key).payload
    pins = {f"{i['kind']}/{i['key']}": i for i in rec['inputs']}
    history = {}
    for ref, i in pins.items():
        if i['revision'] > 1:
            history[ref] = [{'revision': h.revision, 'payload_hash': h.payload_hash} for h in scoped.history(i['kind'], i['key'])]
    return {'figure': rec['result'], 'pins': pins, 'history': history, 'formula': (rec['formula_id'], rec['formula_version']), 'params': rec['params']}
