"""Continuous monitoring: event-triggered re-evaluation, scheduled sweeps, and observable failure.  Blueprint: Section 06 section 10; PG-AI-AC-02, 03, 18.

  on_event   a new or revised stored record (or a changed policy) re-runs detection for exactly the scopes it can affect.  The same event twice gives the same pinned inputs and so
             the same run: ingestion is a no-op the second time (event replay is safe).
  sweep      re-runs every project and the tenant scope for a given as-of date.  Conditions that depend on the passing of time (a retention date, a variation's age, an expiry, hire days)
             generate NO record change, so only a sweep can find them.
  health     says when the last successful sweep was, which runs failed, which rules did not run and why, and how many notifications are undelivered.  It states, every time, that the
             absence of an alert is not evidence that nothing is wrong.
A failed run is never swallowed: it is written to the monitoring log with its error code, the other scopes still run, and `health` reports it until a later run for that scope succeeds."""
from .. import canon, repro
from ..fin.fmath import days_between
from ..fin.snap import project_of
from . import detect as D, findings as FD, gather as G, policy as DP

LOG_KIND = 'det_monitor_run'
TENANT_EVENT_KINDS = ('compliance', 'supplier', 'supplier_quote')
POLICY_KINDS = (DP.POLICY_KIND, 'fin_policy')
STATEMENT = 'The absence of an alert is not evidence that nothing is wrong: a rule that did not run, a failed run or a record held back all produce no alert.'


def project_ids(scoped):
    return sorted(r.key for r in scoped.query('project'))


def scopes_for_event(scoped, event):
    """-> (project ids, include tenant).  event = {'kind', 'key'}."""
    kind, key = event['kind'], event['key']
    if kind in POLICY_KINDS:
        return project_ids(scoped), True
    look = lambda k, kk: (lambda r: r.payload if r is not None else None)(scoped.get(k, kk))
    rec = scoped.get(kind, key)
    tenant = kind in TENANT_EVENT_KINDS or kind == 'purchase_order'
    if rec is None:
        return project_ids(scoped), True                        # an event about a record that cannot be found affects everything: safest
    if kind == 'project':
        return [key], tenant
    if kind in G.TENANT_DET_KINDS and kind not in ('purchase_order',):
        return [], True
    p = project_of(kind, rec.payload, look)
    return ([p] if p is not None else project_ids(scoped)), tenant


def _log(scoped, clock, trigger, as_of, scopes, results, failures):
    n = len(scoped.query(LOG_KIND)) + 1
    status = 'ok' if not failures else ('failed' if not results else 'partial')
    rec = {'run_no': n, 'trigger': trigger, 'as_of': as_of, 'started_at': clock.now(), 'status': status, 'scopes': scopes, 'results': results, 'failures': failures}
    scoped.put(LOG_KIND, '%06d' % n, rec, expected_revision=0)
    scoped.log('monitor.run', f'{LOG_KIND}/{n:06d}', 'ok' if status == 'ok' else 'failed', reason=trigger, detail={'status': status, 'failures': len(failures)})
    return rec


def _one(scoped, clock, registry, scope, as_of, fin_policy, det_policy):
    if scope == 'tenant':
        rec = D.run_tenant(scoped, registry, clock, as_of, det_policy)
    else:
        rec = D.run_project(scoped, registry, clock, scope, as_of, fin_policy, det_policy)
    summary = FD.ingest_run(scoped, clock, registry, rec['run_key'])
    return {'scope': scope, 'run_key': rec['run_key'], 'created': len(summary['created']), 'updated': len(summary['updated']), 'reopened': len(summary['reopened']),
            'rules_not_run': summary['rules_not_run'], 'replay': summary['replay']}


def run_scopes(scoped, clock, registry, scopes, as_of, fin_policy, det_policy, trigger):
    results, failures = [], []
    for sc in scopes:
        try:
            results.append(_one(scoped, clock, registry, sc, as_of, fin_policy, det_policy))
        except Exception as e:                                      # every failure is recorded with a code; none is swallowed
            failures.append({'scope': sc, 'code': getattr(e, 'code', type(e).__name__), 'detail': str(e)[:300]})
    return _log(scoped, clock, trigger, as_of, list(scopes), results, failures)


def on_event(scoped, clock, registry, event, as_of, fin_policy, det_policy):
    projects, tenant = scopes_for_event(scoped, event)
    scopes = list(projects) + (['tenant'] if tenant else [])
    return run_scopes(scoped, clock, registry, scopes, as_of, fin_policy, det_policy, 'event:%s/%s' % (event['kind'], event['key']))


def sweep(scoped, clock, registry, as_of, fin_policy, det_policy):
    return run_scopes(scoped, clock, registry, project_ids(scoped) + ['tenant'], as_of, fin_policy, det_policy, 'sweep')


def health(scoped, as_of=None):
    logs = [canon.deep_copy(r.payload) for r in scoped.query(LOG_KIND)]
    last_ok_sweep, last_state = None, {}
    for r in logs:                                                  # oldest first
        ok_scopes = {x['scope'] for x in r['results']}
        for sc in r['scopes']:
            last_state[sc] = ('ok', r['run_no']) if sc in ok_scopes else ('failed', r['run_no'])
        if r['trigger'] == 'sweep' and r['status'] == 'ok':
            last_ok_sweep = r['as_of']
    failing = {sc: {'run_no': n, 'failure': next((f for f in logs[n - 1]['failures'] if f['scope'] == sc), None)} for sc, (st, n) in sorted(last_state.items()) if st == 'failed'}
    rules_not_run = {}
    for r in reversed(logs):
        for x in r['results']:
            if x['scope'] not in rules_not_run:
                rules_not_run[x['scope']] = x['rules_not_run']
    return {'runs_logged': len(logs), 'last_successful_sweep_as_of': last_ok_sweep, 'days_since_successful_sweep': (days_between(last_ok_sweep, as_of) if last_ok_sweep and as_of else None),
            'scopes_currently_failing': failing, 'rules_not_run_in_latest_run': {k: v for k, v in sorted(rules_not_run.items()) if v},
            'undelivered_notifications': len(FD.outstanding_notifications(scoped)), 'statement': STATEMENT}
