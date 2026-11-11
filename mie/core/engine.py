"""The inbound operations OP-01 to OP-12 (MIE1_SPEC sections 9 and 10; MIE1_PORTS.csv).  Every operation takes a context that the TenantContextPort verifies; a payload
never names a tenant.  The sequence for every operation with a verified context (section 9.2):
  1 validate the request   2 compute the outcome without side effects   3 append the audit event (OK, ACCEPTED, REFUSED or FAILED)
  4 only then commit state through the store ports   5 return the result.
If step 3 fails the operation returns AUDIT_UNAVAILABLE with no result and no state change, reads included.  If a store fails at step 4 the operation returns
STORE_UNAVAILABLE and one attempt is made to append a FAILED event; any other exception there is INTERNAL_ERROR_FAIL_CLOSED with one attempted FAILED event (MIE-1.1).
An audit sink that fails in any way is AUDIT_UNAVAILABLE.  An unexpected exception becomes INTERNAL_ERROR_FAIL_CLOSED.  An unverifiable context names no tenant, so
it produces no tenant audit event.  Atomicity between the audit append and the commit is a host property (MIE-OQ-23, BLK-01, EDR-37)."""
import re
from . import canon, observations as O, pack as P, signals as S, timing as T, values as V, vocab as Y
from .ports import AuditFailure, ContextInvalid, ContextMissing, StoreFailure
from .vocab import MieError

RESULT_RE = re.compile(r'^RS-[0-9a-f]{64}$')


class _Done:
    """What a computed operation hands to the audit-and-commit step."""
    def __init__(self, result, refs, commit=None):
        self.result, self.refs, self.commit = result, refs, commit


class Engine:
    def __init__(self, context, observations, registry, results, audit, audit_query, approvals, hooks, limits):
        self.context, self.obs, self.registry, self.results = context, observations, registry, results
        self.audit, self.audit_query, self.approvals, self.hooks, self.limits_port = audit, audit_query, approvals, hooks, limits

    # ------------------------------------------------------------------ the shared sequence
    def _tenant(self, ctx):
        try:
            return self.context.resolve(ctx)
        except ContextMissing:
            raise MieError('TENANT_CONTEXT_MISSING')
        except ContextInvalid:
            raise MieError('TENANT_CONTEXT_INVALID')
        except Exception:
            raise MieError('TENANT_CONTEXT_INVALID')

    def _append(self, tenant, op, outcome, code, refs):
        """An audit sink that fails in any way is an unavailable audit sink (MIE-1.1, F-70): nothing may proceed on an event that may not have been recorded."""
        try:
            self.audit.append(tenant, {'operation': op, 'outcome': outcome, 'code': code, 'correlation_id': refs.get('correlation_id'),
                                       'refs': {k: v for k, v in refs.items() if k != 'correlation_id'}})
        except AuditFailure:
            raise
        except Exception:
            raise AuditFailure()

    def _run(self, op, ctx, request, compute):
        tenant = self._tenant(ctx)
        refs = {'correlation_id': _correlation(op, request)}
        try:
            if O.tenant_claim(request):
                raise MieError('REQUEST_MALFORMED', 'a payload never names a tenant')
            done = compute(tenant, refs)
        except MieError as e:
            if e.code not in Y.OPERATION_ERRORS[op]:           # the per-operation error lists are exact (AU-11): anything else fails closed
                self._try_append(tenant, op, 'FAILED', 'INTERNAL_ERROR_FAIL_CLOSED', refs, must=True)
                raise MieError('INTERNAL_ERROR_FAIL_CLOSED', 'an error outside the operation contract')
            outcome = 'FAILED' if e.code in ('STORE_UNAVAILABLE', 'INTERNAL_ERROR_FAIL_CLOSED') else 'REFUSED'
            self._try_append(tenant, op, outcome, e.code, refs, must=True)
            raise
        except StoreFailure:
            self._try_append(tenant, op, 'FAILED', 'STORE_UNAVAILABLE', refs, must=True)
            raise MieError('STORE_UNAVAILABLE')
        except Exception:
            self._try_append(tenant, op, 'FAILED', 'INTERNAL_ERROR_FAIL_CLOSED', refs, must=False)
            raise MieError('INTERNAL_ERROR_FAIL_CLOSED')
        refs.update(done.refs)
        try:
            self._append(tenant, op, 'ACCEPTED' if done.commit else 'OK', None, refs)
        except AuditFailure:
            raise MieError('AUDIT_UNAVAILABLE')
        if done.commit:
            try:
                done.commit()
            except StoreFailure:
                self._try_append(tenant, op, 'FAILED', 'STORE_UNAVAILABLE', refs, must=False)
                raise MieError('STORE_UNAVAILABLE')
            except Exception:                                     # MIE-1.1, F-70: any other failure of the commit fails closed, with one FAILED event
                self._try_append(tenant, op, 'FAILED', 'INTERNAL_ERROR_FAIL_CLOSED', refs, must=False)
                raise MieError('INTERNAL_ERROR_FAIL_CLOSED')
        return canon.copy(done.result)

    def _try_append(self, tenant, op, outcome, code, refs, must):
        try:
            self._append(tenant, op, outcome, code, refs)
        except AuditFailure:
            if must:
                raise MieError('AUDIT_UNAVAILABLE')

    def _limits(self, *keys):
        lim = self.limits_port.limits()
        if not isinstance(lim, dict) or any(not V.is_int(lim.get(k)) or lim[k] < 0 for k in keys):
            raise MieError('LIMIT_NOT_CONFIGURED', 'the host supplied no value for %s' % ', '.join(k for k in keys if not isinstance(lim, dict) or not V.is_int(lim.get(k))))
        return lim

    def _pin(self, pin):
        why = P.pin_problem(pin)
        if why:
            raise MieError('REQUEST_MALFORMED', why)

    def _pack(self, pin, absent):
        """-> (document, registry entry).  absent is the code for a pack that is not registered."""
        self._pin(pin)
        e = self.registry.get(pin['pack_id'], pin['pack_version'])
        if e is None:
            raise MieError(absent)
        if e['pin']['pack_hash'] != pin['pack_hash']:
            raise MieError('PACK_HASH_MISMATCH')
        return canon.loads(e['bytes']), e

    def _active(self, tenant, pin):
        """The pack must be registered, pinned exactly, not withdrawn and activated by this tenant.  A refused pack was never stored, so it is not active (section 6.6)."""
        doc, e = self._pack(pin, 'PACK_NOT_ACTIVE')
        if self.registry.withdrawal(pin) is not None:
            raise MieError('PACK_WITHDRAWN')
        acts = self.registry.activations(tenant, pin)
        if not acts:
            raise MieError('PACK_NOT_ACTIVE')
        return doc, acts[-1]

    def _date(self, d, what='evaluation_date'):
        if V.parse_date(d) is None:
            raise MieError('REQUEST_MALFORMED', '%s must be an ISO calendar date' % what)
        return d

    # ------------------------------------------------------------------ OP-01
    def describe(self, ctx):
        def compute(tenant, refs):
            return _Done({'versions': dict(Y.VERSIONS), 'operations': list(Y.OPERATIONS), 'operation_errors': {k: list(v) for k, v in Y.OPERATION_ERRORS.items()},
                          'signals': list(Y.SIGNALS), 'outcomes': {k: list(v) for k, v in Y.OUTCOMES.items()}, 'event_classes': list(Y.EVENT_CLASSES),
                          'errors': list(Y.ERRORS), 'reasons': list(Y.REASONS), 'limit_keys': list(Y.LIMIT_KEYS),
                          'statement': 'The core records assessments; it orders, commits and notifies nothing.'}, {})
        return self._run('describe', ctx, {}, compute)

    # ------------------------------------------------------------------ OP-02, OP-03
    def validate_pack(self, ctx, pack_bytes):
        def compute(tenant, refs):
            lim = self._limits('max_pack_bytes', 'max_rules', 'max_string_length')
            doc, pin = P.validate(pack_bytes, lim)
            return _Done({'valid': True, 'pin': pin}, {'pack': pin})
        return self._run('validate_pack', ctx, {}, compute)

    def register_pack(self, ctx, pack_bytes):
        def compute(tenant, refs):
            lim = self._limits('max_pack_bytes', 'max_rules', 'max_string_length')
            doc, pin = P.validate(pack_bytes, lim)
            e = self.registry.get(pin['pack_id'], pin['pack_version'])
            if e is not None:
                if e['pin']['pack_hash'] != pin['pack_hash']:
                    raise MieError('PACK_VERSION_CONFLICT', '%s %s is bound to another hash' % (pin['pack_id'], pin['pack_version']))
                return _Done({'pin': pin, 'registered': 'already'}, {'pack': pin})
            canonical = canon.dumps(doc)
            return _Done({'pin': pin, 'registered': 'now'}, {'pack': pin}, commit=lambda: self.registry.put(pin, canonical, tenant))
        return self._run('register_pack', ctx, {}, compute)

    # ------------------------------------------------------------------ OP-04, OP-05, OP-06
    def get_pack(self, ctx, pin):
        def compute(tenant, refs):
            doc, e = self._pack(pin, 'NOT_FOUND')
            return _Done({'pin': e['pin'], 'pack': doc, 'withdrawal': self.registry.withdrawal(pin)}, {'pack': e['pin']})
        return self._run('get_pack', ctx, {'pin': pin}, compute)

    def withdraw_pack(self, ctx, pin, reason_ref):
        def compute(tenant, refs):
            doc, e = self._pack(pin, 'NOT_FOUND')
            if e['publisher'] != tenant:
                raise MieError('NOT_FOUND')
            if V.text_problem(reason_ref, 512) or not reason_ref.strip():
                raise MieError('REQUEST_MALFORMED', 'a withdrawal names its reason reference')
            rec = {'pin': e['pin'], 'reason_ref': reason_ref}
            if self.registry.withdrawal(pin) is not None:
                return _Done({'withdrawal': self.registry.withdrawal(pin), 'withdrawn': 'already'}, {'pack': e['pin']})
            return _Done({'withdrawal': rec, 'withdrawn': 'now'}, {'pack': e['pin']}, commit=lambda: self.registry.withdraw(pin, rec))
        return self._run('withdraw_pack', ctx, {'pin': pin, 'reason_ref': reason_ref}, compute)

    def activate_pack(self, ctx, pin, approval_ref):
        def compute(tenant, refs):
            doc, e = self._pack(pin, 'NOT_FOUND')
            if self.registry.withdrawal(pin) is not None:
                raise MieError('PACK_WITHDRAWN')
            if not isinstance(approval_ref, str) or not approval_ref.strip() or V.text_problem(approval_ref, 512):
                raise MieError('PACK_APPROVAL_MISSING', 'an activation needs an owner approval reference')
            if not self.approvals.verify(tenant, approval_ref, e['pin'], doc):
                raise MieError('PACK_APPROVAL_MISSING', 'the approval reference was not verified for this pack')
            rec = {'pin': e['pin'], 'approval_ref': approval_ref}
            acts = self.registry.activations(tenant, pin)
            if acts and acts[-1] == rec:
                return _Done({'activation': rec, 'activated': 'already'}, {'pack': e['pin'], 'approval_ref_digest': canon.digest(approval_ref)})
            return _Done({'activation': rec, 'activated': 'now'}, {'pack': e['pin'], 'approval_ref_digest': canon.digest(approval_ref)},
                         commit=lambda: self.registry.activate(tenant, pin, rec))
        return self._run('activate_pack', ctx, {'pin': pin, 'approval_ref': approval_ref}, compute)

    # ------------------------------------------------------------------ OP-07
    def submit_observations(self, ctx, pin, batch):
        def compute(tenant, refs):
            if not isinstance(batch, list):
                raise MieError('REQUEST_MALFORMED', 'a batch is a list of observations')
            lim = self._limits('max_batch_items', 'max_string_length', 'max_abs_exponent', 'max_mantissa_digits')
            if len(batch) > lim['max_batch_items']:
                raise MieError('LIMIT_EXCEEDED', 'more observations in the batch than the configured bound')
            doc, act = self._active(tenant, pin)
            seen = {}
            receipts, new = [], []

            def known(oid):
                """-> the observation this tenant already holds (or submitted earlier in this batch) under that identifier, or None."""
                return seen.get(oid) or self.obs.get(tenant, oid)
            for i, item in enumerate(batch):
                r, ob = O.check(item, doc, lim, known)
                r['index'] = i
                receipts.append(r)
                if ob is not None:
                    seen[r['observation_id']] = ob
                    new.append((r['observation_id'], ob))
            counts = {s: sum(1 for r in receipts if r['status'] == s) for s in ('ACCEPTED', 'DUPLICATE', 'REJECTED')}

            def commit():
                self.obs.append_batch(tenant, new)                # MIE-1.1, F-70: all of the batch or none of it
            return _Done({'receipts': receipts, 'counts': counts}, {'pack': P_pin(pin), 'counts': counts,
                                                                    'accepted_ids': [oid for oid, _ in new]}, commit=commit if new else None)
        return self._run('submit_observations', ctx, {'batch': batch}, compute)

    # ------------------------------------------------------------------ OP-08
    def get_signals(self, ctx, pin, subject_id, evaluation_date):
        def compute(tenant, refs):
            lim = self._limits('max_series_points', 'max_string_length')
            if not isinstance(subject_id, str):
                raise MieError('REQUEST_MALFORMED', 'subject_id required')
            self._date(evaluation_date)
            doc, act = self._active(tenant, pin)
            sid = P.canonical_subject(doc, subject_id)
            if sid is None:
                raise MieError('NOT_FOUND')
            obs = self._evidence(tenant, doc, sid, lim)
            ev = S.assess_evidence(doc, obs, sid, evaluation_date, None)
            out = {'record': 'mie-signal-view', 'versions': dict(Y.VERSIONS), 'pack': P_pin(pin), 'subject_id': sid, 'evaluation_date': evaluation_date,
                   'signals': ev['signals'], 'gaps': ev['gaps'], 'qualification': ev['qualification'], 'evidence': ev['evidence'], 'uncertainty': ev['uncertainty'],
                   'decision_profile': doc['decision_profile'], 'note': 'a context view of observed evidence; it states no intention and no outcome'}
            return _Done(out, {'pack': P_pin(pin), 'subject_digest': canon.digest(sid), 'evidence_count': len(obs)})
        return self._run('get_signals', ctx, {'subject_id': subject_id, 'evaluation_date': evaluation_date}, compute)

    def _evidence(self, tenant, doc, sid, lim):
        subj = {s['subject_id']: s for s in doc['vocabulary']['subjects']}[sid]
        convs = {c['conversion_id']: c for c in doc['conversions']}
        wanted = [sid] + [convs[c]['subject_id'] for c in subj['conversions']]
        obs = self.obs.for_subjects(tenant, wanted)
        if len(obs) > lim['max_series_points']:
            raise MieError('LIMIT_EXCEEDED', 'more observations for the subject than the configured bound')
        return obs

    # ------------------------------------------------------------------ OP-09
    def assess_timing(self, ctx, pin, subject_id, intention, constraints, scenarios, evaluation_date, freshness_limits=None):
        req_in = {'subject_id': subject_id, 'intention': intention, 'constraints': constraints, 'scenarios': scenarios, 'evaluation_date': evaluation_date,
                  'freshness_limits': freshness_limits}

        def compute(tenant, refs):
            lim = self._limits('max_series_points', 'max_string_length', 'max_scenarios', 'max_abs_exponent', 'max_mantissa_digits')
            request = self._timing_request(subject_id, intention, constraints, scenarios, evaluation_date, freshness_limits, lim)
            doc, act = self._active(tenant, pin)
            if intention not in doc['allowed_intentions']:
                raise MieError('INTENTION_NOT_ALLOWED', 'the pack allows %s' % ', '.join(doc['allowed_intentions']))
            sid = P.canonical_subject(doc, subject_id)
            if sid is None:
                raise MieError('PACK_INCOMPLETE', 'the pack declares no subject %r' % subject_id)
            for k in request['freshness_limits']:
                if any(f['observation_class'] == k for f in doc['freshness_limits']):
                    raise MieError('REQUEST_MALFORMED', 'the pack already sets the freshness limit for %s; a request cannot replace a policy limit' % k)
            for sc in request['scenarios']:
                why = T.scenario_problem(sc, doc, lim)
                if why:
                    raise MieError('SCENARIO_INVALID', why)
            obs = self._evidence(tenant, doc, sid, lim)
            body, rid = self._compute_result(doc, P_pin(pin), dict(request, subject_id=sid), obs, act['approval_ref'])
            return _Done(body, {'pack': P_pin(pin), 'result_id': rid, 'evidence_count': len(obs), 'outcome': body['outcome']},
                         commit=lambda: self.results.put(tenant, rid, body))
        return self._run('assess_timing', ctx, req_in, compute)

    def _timing_request(self, subject_id, intention, constraints, scenarios, evaluation_date, freshness_limits, lim):
        if not isinstance(subject_id, str) or V.text_problem(subject_id, lim['max_string_length']):
            raise MieError('REQUEST_MALFORMED', 'subject_id required')
        if intention not in Y.INTENTIONS:
            raise MieError('REQUEST_MALFORMED', 'the intention is BUY or SELL')
        self._date(evaluation_date)
        if constraints is None:
            constraints = {}
        if not isinstance(constraints, dict) or set(constraints) - {'need_by'}:
            raise MieError('REQUEST_MALFORMED', 'constraints are {need_by}')
        if constraints.get('need_by') is not None:
            self._date(constraints['need_by'], 'need_by')
        cons = {'need_by': constraints['need_by']} if constraints.get('need_by') is not None else {}
        if scenarios is None:
            scenarios = []
        if not isinstance(scenarios, list):
            raise MieError('SCENARIO_INVALID', 'scenarios are a list')
        if len(scenarios) > lim['max_scenarios']:
            raise MieError('LIMIT_EXCEEDED', 'more scenarios than the configured bound')
        if freshness_limits is None:
            freshness_limits = {}
        if not isinstance(freshness_limits, dict) or any(k not in Y.OBSERVATION_CLASSES for k in freshness_limits):
            raise MieError('REQUEST_MALFORMED', 'request freshness limits are {observation class: days}')
        fl = {k: (v if V.is_int(v) and v >= 0 else 'INVALID_NOT_USED') for k, v in freshness_limits.items() if v is not None}
        return {'subject_id': subject_id, 'intention': intention, 'constraints': cons, 'scenarios': scenarios, 'evaluation_date': evaluation_date, 'freshness_limits': fl}

    def _compute_result(self, doc, pin, request, obs, approval_ref):
        rl = {k: v for k, v in request['freshness_limits'].items() if V.is_int(v)}
        ev = S.assess_evidence(doc, obs, request['subject_id'], request['evaluation_date'], rl)
        try:
            body = T.build(doc, pin, request, obs, ev, approval_ref)
        except T.FailClosed:
            raise MieError('INTERNAL_ERROR_FAIL_CLOSED', 'the evaluator refused to emit an unlabelled signal-influenced result')
        rid = T.result_id(pin, request, list(obs))
        body = dict(body, result_id=rid, request=request, evidence_set=sorted(obs))
        return body, rid

    # ------------------------------------------------------------------ OP-10, OP-11
    def get_result(self, ctx, result_id):
        def compute(tenant, refs):
            if not isinstance(result_id, str) or not RESULT_RE.match(result_id):
                raise MieError('REQUEST_MALFORMED', 'a result identifier is RS- and 64 hex characters')
            body = self.results.get(tenant, result_id)
            if body is None:
                raise MieError('NOT_FOUND')
            return _Done(body, {'result_id': result_id})
        return self._run('get_result', ctx, {'result_id': result_id}, compute)

    def replay_result(self, ctx, result_id, alternative_pack=None):
        """Recompute a stored result from its stored evidence (by identifier, never the latest data) and its pinned pack, and compare byte for byte.  With an alternative
        pack, report the drift instead; the stored result is never overwritten."""
        def compute(tenant, refs):
            if not isinstance(result_id, str) or not RESULT_RE.match(result_id):
                raise MieError('REQUEST_MALFORMED', 'a result identifier is RS- and 64 hex characters')
            stored = self.results.get(tenant, result_id)
            if stored is None:
                raise MieError('NOT_FOUND')
            pin = alternative_pack if alternative_pack is not None else stored['pack']
            if alternative_pack is not None:
                self._pin(alternative_pack)
            e = self.registry.get(pin['pack_id'], pin['pack_version'])
            if e is None or e['pin']['pack_hash'] != pin['pack_hash']:
                raise MieError('REPLAY_PACK_UNAVAILABLE')
            doc = canon.loads(e['bytes'])
            obs = {}
            for oid in stored['evidence_set']:
                o = self.obs.get(tenant, oid)
                if o is None:
                    raise MieError('REPLAY_EVIDENCE_UNAVAILABLE', oid)
                obs[oid] = o
            body, rid = self._compute_result(doc, e['pin'], stored['request'], obs, stored['activation_approval_ref'])
            if alternative_pack is None and stored['versions'] == Y.VERSIONS:
                same = canon.dumps(body) == canon.dumps(stored)
                out = {'result_id': result_id, 'identical': same, 'stored_digest': canon.digest(stored), 'replayed_digest': canon.digest(body)}
            else:
                out = {'result_id': result_id, 'drift_report': True, 'replayed_under': {'pack': e['pin'], 'versions': dict(Y.VERSIONS)},
                       'stored_under': {'pack': stored['pack'], 'versions': stored['versions']}, 'replayed_result_id': rid,
                       'differences': _diff(stored, body), 'stored_result_unchanged': True}
            return _Done(out, {'result_id': result_id})
        return self._run('replay_result', ctx, {'result_id': result_id, 'alternative_pack': alternative_pack}, compute)

    # ------------------------------------------------------------------ OP-12
    def list_audit(self, ctx, from_seq=1, limit=None):
        """Reads this tenant's events up to a cutoff fixed first, then appends exactly one AUDIT_READ event, which is not in its own result (no recursion)."""
        tenant = self._tenant(ctx)
        refs = {'correlation_id': _correlation('list_audit', {'from_seq': from_seq, 'limit': limit})}
        try:
            lim = self._limits('max_audit_page')
            if not V.is_int(from_seq) or from_seq < 1 or not V.is_int(limit) or limit < 1:
                raise MieError('REQUEST_MALFORMED', 'from_seq and limit are whole numbers of 1 or more')
            if limit > lim['max_audit_page']:
                raise MieError('LIMIT_EXCEEDED', 'more events than the configured page bound')
        except MieError as e:
            self._try_append(tenant, 'list_audit', 'REFUSED', e.code, refs, must=True)
            raise
        try:
            cutoff = self.audit_query.last_seq(tenant)
            events = self.audit_query.read(tenant, from_seq, cutoff, limit)
            check = self.audit_query.verify(tenant)
            self.audit.append(tenant, {'operation': 'list_audit', 'outcome': 'OK', 'code': None, 'correlation_id': refs['correlation_id'],
                                       'refs': {'type': Y.AUDIT_READ, 'cutoff_seq': cutoff, 'returned': len(events)}})
        except AuditFailure:
            raise MieError('AUDIT_UNAVAILABLE')
        except Exception:
            self._try_append(tenant, 'list_audit', 'FAILED', 'INTERNAL_ERROR_FAIL_CLOSED', refs, must=False)
            raise MieError('INTERNAL_ERROR_FAIL_CLOSED')
        return {'events': events, 'cutoff_seq': cutoff, 'chain': check}


def P_pin(pin):
    return {'pack_id': pin['pack_id'], 'pack_version': pin['pack_version'], 'pack_hash': pin['pack_hash']}


def _correlation(op, request):
    try:
        return canon.digest({'operation': op, 'request': _hashable(request)})[:32]
    except Exception:
        return None


def _hashable(v, depth=0):
    if depth > 30:
        return None
    if isinstance(v, dict):
        return {str(k): _hashable(x, depth + 1) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_hashable(x, depth + 1) for x in v]
    if v is None or isinstance(v, (bool, int)):
        return v
    if isinstance(v, str):
        try:
            canon.dumps(v)
            return v
        except canon.CanonError:
            return None
    return repr(type(v).__name__)


def _diff(a, b, path='$', out=None):
    out = [] if out is None else out
    if type(a) != type(b):
        out.append(path)
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append('%s.%s' % (path, k))
            else:
                _diff(a[k], b[k], '%s.%s' % (path, k), out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(path)
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                _diff(x, y, '%s[%d]' % (path, i), out)
    elif a != b:
        out.append(path)
    return out
