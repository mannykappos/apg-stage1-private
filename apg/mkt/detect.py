"""The M6 procurement run: a reproducible formula over pinned records.  Blueprint: Section 05 section 13 (reproducibility), Section 06 sections 5.1, 10, 16, Section 08 sections 8, 14.

`mkt.assess_project` and `mkt.assess_tenant` are registered with the M2 reproducibility module beside the financial and detection formulas.  A stored result holds
  signals       the procurement signals, in the form the M5 finding lifecycle already accepts (identity, history, human-only transitions, noise control)
  rule_runs     one record per rule, including rules that did not run and why
  analyses      the reproducible analyses behind the signals: requirements with coverage, rankings with every gate record, scenarios, reference rates, duplicates, supplier profiles, portfolio
  events        `apg-event-1` records (observation time, effective period, sources, identifiers) for the later cross-domain engine; M6 draws no conclusion from them
and is replayable.  The code hash covers every procurement module, the detection and financial modules they call, and the rule table.  A run changes no stored record; signals become findings only
through `findings.ingest_run`, a separate audited service step.  No result here recommends a purchase, a supplier or a substitution."""
import hashlib, inspect
from .. import repro
from ..fin import snap
from ..det import common as DC, detect as DD, policy as DP, signal as S
from . import analysis as AN, common as C, compare, demand, events as EV, fresh, fx, gather as G, intake as MI, intl, landed, opportunity, policy as MP, purchasing, rules as R, scenarios, spec, suppliers

MKT_VERSION = 'apg-mkt-1'
MODULES = DD.MODULES + (DD, DC, MI, MP, C, EV, fx, fresh, spec, landed, intl, compare, demand, scenarios, suppliers, opportunity, purchasing, AN, R, G)
FORMULA_IDS = ('mkt.assess_project', 'mkt.assess_tenant')


def code_hash():
    h = hashlib.sha256()
    for m in MODULES:
        h.update(inspect.getsource(m).encode('utf-8'))
    h.update(inspect.getsource(_run).encode('utf-8'))
    h.update(repr([(rid, fn.__module__, fn.__name__) for rid, fn in R.PROJECT_RULES + R.TENANT_RULES]).encode('utf-8'))
    return h.hexdigest()


def _run(inputs, params, rules, scope):
    F = snap.Facts(inputs, params)
    mp, sp, dp = C.mkt_policy(F), C.mkt_spec(F), DC.det_policy(F)
    project, as_of = params.get('project'), params['as_of']
    authorised = set(params['authorised_projects']) if params.get('authorised_projects') is not None else None
    A = AN.Analysis(F, mp, sp, as_of, project, authorised)
    signals, runs = [], {}
    for rid, fn in rules:
        sigs, run = fn(A, F, mp, as_of, project)
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
    evs = {}
    for s in signals:
        for e in s['extra'].get('events', []):
            EV.validate(e)
            evs[e['event_id']] = e
    if mp is not None:
        for r in A.demands():
            e = EV.make('demand_required', r['id'], r['observed_at'] or (as_of + 'T00:00:00Z'), r['required_date'], r['sources'], project=r['project'], material=r['material'])
            evs[e['event_id']] = e
    fp = F.policy
    analyses = A.block() if mp is not None else {'requirements': {}, 'not_assessed': [{'subject': 'scope', 'analysis': 'all', 'missing_parameter': 'mkt_policy'}]}
    return {'mkt_version': MKT_VERSION, 'scope': scope, 'as_of': as_of,
            'authorised_projects': sorted(authorised) if authorised is not None else None,
            'det_policy': {'version': params.get('det_policy'), 'approved': bool(dp and dp['_approved'])} if dp is not None else {'version': params.get('det_policy'), 'approved': False},
            'fin_policy': {'version': fp['version'], 'approved': fp['_approved']} if fp is not None else None,
            'mkt_policy': {'version': params.get('mkt_policy'), 'approved': bool(mp is not None and mp.get('_approved'))} if mp is not None else {'version': params.get('mkt_policy'), 'approved': False},
            'mkt_spec': {'version': params.get('mkt_spec'), 'approved': bool(sp and sp['_approved'])} if sp is not None else {'version': params.get('mkt_spec'), 'approved': False},
            'rule_runs': {k: runs[k] for k in sorted(runs)}, 'signals': signals, 'analyses': analyses, 'events': [evs[k] for k in sorted(evs)],
            'counts': {'signals': len(signals), 'rules': len(runs), 'rules_not_run': sum(1 for r in runs.values() if r['status'] != 'evaluated'), 'events': len(evs)},
            'statement': 'Procurement analysis from stored records. No quote is recommended, no supplier chosen, no substitution approved and no saving realised; every purchase decision needs a person.'}


def f_project(inputs, params):
    return _run(inputs, params, R.PROJECT_RULES, {'level': 'project', 'project': params['project']})


def f_tenant(inputs, params):
    return _run(inputs, params, R.TENANT_RULES, {'level': 'tenant', 'project': None})


FORMULAS = {'mkt.assess_project': f_project, 'mkt.assess_tenant': f_tenant}
VERSIONS = {k: 1 for k in FORMULAS}


def mkt_registry(registry=None):
    reg = DD.det_registry(registry)
    h = code_hash()
    for fid, fn in FORMULAS.items():
        reg.register(fid, VERSIONS[fid], fn, code_hash=h)
    return reg


def validate_result(res):
    DD.validate_result(res)
    for e in res['events']:
        EV.validate(e)
    if 'analyses' not in res or 'not_assessed' not in res['analyses']:
        raise ValueError('analyses block')
    if res['scope']['level'] == 'tenant' and res.get('authorised_projects') is None:
        raise ValueError('a tenant run names the projects it may show')
    return True


def run_project(scoped, registry, clock, project, as_of, fin_policy_version, det_policy_version, mkt_policy_version, mkt_spec_version):
    if scoped.get('project', project) is None:
        raise repro.ReproError('PROJECT_UNKNOWN', 'no stored project ' + str(project) + ': a run for it would be empty and look clean')
    refs, params = G.gather_project(scoped, project, as_of, fin_policy_version, det_policy_version, mkt_policy_version, mkt_spec_version)
    rec = repro.run(scoped, registry, clock, 'mkt.assess_project', VERSIONS['mkt.assess_project'], refs, params)
    validate_result(rec['result'])
    return rec


def run_tenant(scoped, registry, clock, as_of, fin_policy_version, det_policy_version, mkt_policy_version, mkt_spec_version, authorised_projects):
    refs, params = G.gather_tenant(scoped, as_of, fin_policy_version, det_policy_version, mkt_policy_version, mkt_spec_version, authorised_projects)
    rec = repro.run(scoped, registry, clock, 'mkt.assess_tenant', VERSIONS['mkt.assess_tenant'], refs, params)
    validate_result(rec['result'])
    return rec


def check_record(scoped, registry, run_key):
    """Everything a reviewer can verify about a stored procurement run without trusting it (replay, validity, pins consistent, drift)."""
    rec = scoped.get(repro.KIND, run_key)
    if rec is None:
        return {'replay': repro.ReplayResult(False, 'RECORD_MISSING', run_key), 'result_valid': False, 'pins_consistent': False, 'drift': []}
    p = rec.payload
    rp = repro.replay(scoped, registry, run_key)
    try:
        validate_result(p['result'])
        valid = True
    except (ValueError, KeyError, TypeError, S.SignalError, EV.EventError):
        valid = False
    claimed = p['params'].get('pins')
    pinned = {'%s/%s' % (i['kind'], i['key']): i['revision'] for i in p['inputs']}
    ok = True if claimed is None else all(pinned.get(k) == v for k, v in claimed.items()) and set(claimed) <= set(pinned)
    return {'replay': rp, 'result_valid': valid, 'pins_consistent': ok, 'drift': repro.drift_report(scoped, run_key)}
