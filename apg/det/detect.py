"""The detection run: a reproducible formula over pinned records.  Blueprint: Section 06 sections 5.1 (deterministic first), 10 (monitoring: failed runs observable, no alert is
not proof of no issue), 16; Section 05 section 13 (reproducibility); PG-AI-AC-01, 05, 18, 19.

`det.detect_project` and `det.detect_tenant` are registered with the M2 reproducibility module like the financial formulas, so a detection result is stored with the pinned
input revisions, the formula version, a hash of ALL the code it ran (the detection modules, the financial modules it calls and the CR-02 materiality model) and the policy
version, and can be replayed.  The result is a SIGNAL list plus a RULE RUN record for every rule, including the rules that did not run and why (not configured, switched off,
cannot assess): silence is never the only answer a rule can give.

A detection run changes no stored financial or finding record.  Turning signals into findings is a separate, audited step (findings.py)."""
import hashlib, inspect
from .. import canon, materiality, repro
from ..fin import calc_records as FC, snap
from ..repro import FormulaRegistry
from . import common as C, gather as G, intake as DI, policy as DP, rules_commercial as RC, rules_cost as RK, rules_ops as RO, signal as S

DETECT_VERSION = 'apg-det-1'
PROJECT_RULES = (('R01', RK.r01_budget), ('R02', RK.r02_amendment), ('R03', RK.r03_invoice_vs_order), ('R04', RC.r04_variation), ('R04B', RC.r04b_instruction), ('R05', RC.r05_retention),
                 ('R08', RO.r08_hire), ('R09', RK.r09_forecast_movement), ('AGG', RK.agg_split_orders), ('DLY', RO.dly_overlap), ('LAB', RO.lab_productivity), ('DEF', RO.def_recurrence),
                 ('D01', RK.d01_held_cost_records), ('D02', RO.d02_held_records(G.PROJECT_DET_KINDS)))
TENANT_RULES = (('R06', RC.r06_compliance), ('R07', RC.r07_quote_vs_reference), ('D02', RO.d02_held_records(('compliance',))))
MODULES = FC.MODULES + (materiality, DI, DP, S, C, G, RC, RK, RO)           # this module's own source is covered by the formula registry entry below (see code_hash)


def code_hash():
    h = hashlib.sha256()
    for m in MODULES:
        h.update(inspect.getsource(m).encode('utf-8'))
    h.update(inspect.getsource(_run).encode('utf-8'))
    h.update(repr([(rid, fn.__module__, fn.__name__) for rid, fn in PROJECT_RULES + TENANT_RULES] + [G.PROJECT_DET_KINDS]).encode('utf-8'))
    return h.hexdigest()


def _run(inputs, params, rules, scope):
    F = snap.Facts(inputs, params)
    dp = C.det_policy(F)
    project, as_of = params.get('project'), params['as_of']
    signals, runs = [], {}
    for rid, fn in rules:
        sigs, run = fn(F, dp, project, as_of)
        if run['status'] not in C.RUN_STATES or run['rule'] != rid:
            raise ValueError('rule run record is malformed: ' + rid)
        run['signals'] = len(sigs)
        for s in sigs:
            S.validate_signal(s)
            imp = s['priority']['potential_impact_cents']
            signals.append(S.with_severity(s, DP.severity_of(dp, abs(imp) if imp is not None else None)) if dp is not None else s)
        runs[rid] = run
    ids = [s['identity'] for s in signals]
    if len(set(ids)) != len(ids):
        raise ValueError('two signals share one identity')
    signals.sort(key=lambda s: s['identity'])
    fp = F.policy
    return {'detect_version': DETECT_VERSION, 'scope': scope, 'as_of': as_of,
            'det_policy': {'version': params.get('det_policy'), 'approved': bool(dp and dp['_approved'])} if dp is not None else {'version': params.get('det_policy'), 'approved': False},
            'fin_policy': {'version': fp['version'], 'approved': fp['_approved']} if fp is not None else None,
            'rule_runs': {k: runs[k] for k in sorted(runs)}, 'signals': signals,
            'counts': {'signals': len(signals), 'rules': len(runs), 'rules_not_run': sum(1 for r in runs.values() if r['status'] != 'evaluated')}}


def f_project(inputs, params):
    return _run(inputs, params, PROJECT_RULES, {'level': 'project', 'project': params['project']})


def f_tenant(inputs, params):
    return _run(inputs, params, TENANT_RULES, {'level': 'tenant', 'project': None})


FORMULAS = {'det.detect_project': f_project, 'det.detect_tenant': f_tenant}
MKT_FORMULA_IDS = ('mkt.assess_project', 'mkt.assess_tenant')       # registered by apg.mkt.detect (M6); their results use the same signal contract, so the same finding lifecycle ingests them
VERSIONS = {k: 1 for k in FORMULAS}


def det_registry(registry=None):
    reg = FC.fin_registry(registry)
    h = code_hash()
    for fid, fn in FORMULAS.items():
        reg.register(fid, VERSIONS[fid], fn, code_hash=h)
    return reg


def validate_result(res):
    ids = set()
    for s in res['signals']:
        S.validate_signal(s)
        if s['identity'] in ids:
            raise ValueError('duplicate identity')
        ids.add(s['identity'])
    for k, r in res['rule_runs'].items():
        if r['status'] not in C.RUN_STATES or r['rule'] != k:
            raise ValueError('rule run record')
        if r['status'] != 'evaluated' and r['signals']:
            raise ValueError('a rule that did not run cannot have signals')
    canon.canonical(res)
    return True


def run_project(scoped, registry, clock, project, as_of, fin_policy_version, det_policy_version):
    if scoped.get('project', project) is None:
        raise repro.ReproError('PROJECT_UNKNOWN', 'no stored project ' + str(project) + ': a run for it would be empty and look clean')
    refs, params = G.gather_project(scoped, project, as_of, fin_policy_version, det_policy_version)
    rec = repro.run(scoped, registry, clock, 'det.detect_project', VERSIONS['det.detect_project'], refs, params)
    validate_result(rec['result'])
    return rec


def run_tenant(scoped, registry, clock, as_of, det_policy_version):
    refs, params = G.gather_tenant(scoped, as_of, det_policy_version)
    rec = repro.run(scoped, registry, clock, 'det.detect_tenant', VERSIONS['det.detect_tenant'], refs, params)
    validate_result(rec['result'])
    return rec


def check_record(scoped, registry, run_key):
    """Everything a reviewer can verify about a stored detection run without trusting it: replay, result validity, pinned revisions consistent, newer revisions (drift)."""
    rec = scoped.get(repro.KIND, run_key)
    if rec is None:
        return {'replay': repro.ReplayResult(False, 'RECORD_MISSING', run_key), 'result_valid': False, 'pins_consistent': False, 'drift': []}
    p = rec.payload
    rp = repro.replay(scoped, registry, run_key)
    try:
        validate_result(p['result'])
        valid = True
    except (ValueError, KeyError, TypeError, S.SignalError):
        valid = False
    claimed = p['params'].get('pins')
    pinned = {f"{i['kind']}/{i['key']}": i['revision'] for i in p['inputs']}
    ok = True if claimed is None else all(pinned.get(k) == v for k, v in claimed.items()) and set(claimed) <= set(pinned)
    return {'replay': rp, 'result_valid': valid, 'pins_consistent': ok, 'drift': repro.drift_report(scoped, run_key)}
