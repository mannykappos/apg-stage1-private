"""One authoritative forecast per project, scope and as-of state; scenarios and history kept apart.  Blueprint: Section 05 section 8 and PG-PC-AC-03, 12, 19 (concurrency);
Section 12 section 5 ("scenario values remain isolated from the authoritative forecast unless a controlled, audited approval process explicitly promotes them").

A SLOT is the record `fin_forecast_slot/<project>|<scope>|<as_of>`.  It names at most one authoritative forecast run and keeps every earlier one in its history; scenario runs are
filed under their scenario name and are never returned as 'the forecast'.  Rules:
  * only a stored forecast calculation that REPLAYS cleanly and is not 'cannot_assess' can be adopted; a provisional forecast may be adopted and stays marked provisional;
  * adoption needs a human with the role 'forecast_owner' who did not run the calculation;
  * adopting a second forecast supersedes the first (it stays in the history, never deleted);
  * a scenario run (one made with a scenario label) is adopted only by an explicit promotion, which is recorded as such;
  * the slot is written with the expected revision, so two people adopting at once cannot both succeed (the second gets a conflict and must look again)."""
from .. import repro
from ..ports import ConflictError          # noqa: F401  (re-exported for callers)
from . import calc_records as C

SLOT_KIND = 'fin_forecast_slot'
OWNER_ROLE = 'forecast_owner'


class BookError(ValueError):
    def __init__(self, code, msg=''):
        super().__init__(f'{code}: {msg}')
        self.code = code


def slot_key(project, as_of, scope='project'):
    return f'{project}|{scope}|{as_of}'


def _new_slot(project, scope, as_of):
    return {'project': project, 'scope': scope, 'as_of': as_of, 'authoritative': None, 'history': [], 'scenarios': {}}


def _check_run(scoped, registry, run_key, project, as_of):
    rec = scoped.get(repro.KIND, run_key)
    if rec is None:
        raise BookError('RUN_NOT_FOUND', run_key)
    p = rec.payload
    if p['formula_id'] != 'fin.forecast':
        raise BookError('NOT_A_FORECAST', p['formula_id'])
    if p['params'].get('project') != project or p['params'].get('as_of') != as_of:
        raise BookError('RUN_IS_FOR_A_DIFFERENT_PROJECT_OR_DATE')
    fig = p['result']
    if fig['state'] == 'cannot_assess':
        raise BookError('CANNOT_ADOPT_A_FORECAST_THAT_CANNOT_BE_ASSESSED')
    chk = C.check_record(scoped, registry, run_key)
    if not chk['replay'].ok or not chk['figure_valid'] or not chk['pins_consistent']:
        raise BookError('FORECAST_DOES_NOT_REPRODUCE', chk['replay'].code or 'figure or pins')
    return p


def register_scenario(scoped, project, as_of, run_key, scenario, scope='project'):
    """File a scenario run in the slot.  It is never the authoritative forecast and never changes it."""
    if not scenario or not isinstance(scenario, str):
        raise BookError('SCENARIO_NAME_REQUIRED')
    key = slot_key(project, as_of, scope)
    cur = scoped.get(SLOT_KIND, key)
    slot = _new_slot(project, scope, as_of) if cur is None else dict(cur.payload)
    p = scoped.get(repro.KIND, run_key)
    if p is None or p.payload['formula_id'] != 'fin.forecast' or p.payload['params'].get('scenario') != scenario:
        raise BookError('RUN_IS_NOT_A_FORECAST_MADE_FOR_THIS_SCENARIO', 'a scenario run is made with params.scenario = the scenario name')
    sc = {k: list(v) for k, v in slot['scenarios'].items()}
    if run_key not in sc.setdefault(scenario, []):
        sc[scenario].append(run_key)
    slot['scenarios'] = sc
    return scoped.put(SLOT_KIND, key, slot, expected_revision=0 if cur is None else cur.revision)


def adopt(scoped, registry, clock, project, as_of, run_key, scope='project', promote_scenario=None, note=''):
    """Make `run_key` the authoritative forecast of the slot.  -> the stored slot record."""
    ctx = scoped.ctx
    if ctx.actor_kind != 'human' or OWNER_ROLE not in ctx.roles:
        raise BookError('FORECAST_OWNER_REQUIRED', 'adoption needs a human with the role ' + OWNER_ROLE)
    p = _check_run(scoped, registry, run_key, project, as_of)
    if p['created_by'] == ctx.user_id:
        raise BookError('SELF_APPROVAL_REFUSED', 'the person who ran the calculation cannot adopt it')
    is_scenario = bool(p['params'].get('scenario'))
    if is_scenario and promote_scenario != p['params']['scenario']:
        raise BookError('SCENARIO_NEEDS_EXPLICIT_PROMOTION', p['params']['scenario'])
    if promote_scenario and not is_scenario:
        raise BookError('NOT_A_SCENARIO_RUN')
    key = slot_key(project, as_of, scope)
    cur = scoped.get(SLOT_KIND, key)
    slot = _new_slot(project, scope, as_of) if cur is None else {k: (list(v) if isinstance(v, list) else v) for k, v in cur.payload.items()}
    if slot['authoritative'] == run_key:
        return cur
    slot['history'] = list(slot['history']) + [{'event': 'promoted_scenario' if is_scenario else 'adopted', 'run_key': run_key, 'by': ctx.user_id, 'at': clock.now(), 'note': note,
                                               'supersedes': slot['authoritative'], 'state': p['result']['state'], 'scenario': p['params'].get('scenario')}]
    slot['authoritative'] = run_key
    rec = scoped.put(SLOT_KIND, key, slot, expected_revision=0 if cur is None else cur.revision)
    scoped.log('forecast.adopted', f'{SLOT_KIND}/{key}', 'ok', detail={'run_key': run_key, 'supersedes': slot['history'][-1]['supersedes'], 'scenario': bool(is_scenario)})
    return rec


def current(scoped, project, as_of, scope='project'):
    """-> the authoritative forecast's stored record payload, or None.  Scenario runs are never returned here."""
    cur = scoped.get(SLOT_KIND, slot_key(project, as_of, scope))
    if cur is None or cur.payload['authoritative'] is None:
        return None
    return scoped.get(repro.KIND, cur.payload['authoritative']).payload


def verify_slot(scoped, project, as_of, scope='project'):
    """-> list of problems (empty = consistent): at most one authoritative run, every history entry's run exists, the chain of 'supersedes' is unbroken, scenarios are not the
    authoritative run unless promoted."""
    cur = scoped.get(SLOT_KIND, slot_key(project, as_of, scope))
    if cur is None:
        return []
    s, bad = cur.payload, []
    prev = None
    for h in s['history']:
        if scoped.get(repro.KIND, h['run_key']) is None:
            bad.append('HISTORY_RUN_MISSING:' + h['run_key'])
        if h['supersedes'] != prev:
            bad.append('HISTORY_CHAIN_BROKEN_AT:' + h['run_key'])
        prev = h['run_key']
    if (s['history'] and s['history'][-1]['run_key'] != s['authoritative']) or (not s['history'] and s['authoritative'] is not None):
        bad.append('AUTHORITATIVE_DIFFERS_FROM_LAST_ADOPTION')
    for name, runs in s['scenarios'].items():
        if s['authoritative'] in runs and not any(h['run_key'] == s['authoritative'] and h['event'] == 'promoted_scenario' for h in s['history']):
            bad.append('SCENARIO_IS_AUTHORITATIVE_WITHOUT_PROMOTION:' + name)
    return bad
