"""The assessment gate: whether APG may assess at all from what AUIF has delivered.  M8 authorisation: "for invalid, ambiguous, stale, deferred, partial, wrong-tenant,
missing-field and type-mismatched data, and degraded states, the assessment is 'cannot assess' with a reason; no old, default or partial value is shown as current."

It reads only the tenant's own APG store (what apg_auif.intake and the module wrote), so its answer survives a restart.  It can assess only when ALL of these hold:
  * every expected integration's latest recorded AUIF state is ACTIVE                                   (else INTEGRATION_NOT_ACTIVE / NO_STATE)
  * every expected record type has an import, and its latest import was applied with no reason          (else NOT_IMPORTED, or the batch's own reasons: integrity
    reasons such as TRANSLATION_INVALID, AMBIGUOUS, SCHEMA_DRIFT, LINEAGE_*, WRONG_TENANT, MISSING_FIELD, TYPE_MISMATCH, SYNC_*, SOURCE_EMPTY (M8-R1), STALE_MANIFEST, PACK_NOT_PINNED; record-level
    reasons ROW_REJECTED, VALUE_INVALID, STALE_DELIVERY; event reasons EVENTS_WAITING, EVENT_RECONCILIATION_PENDING, EVENT_REJECTED)
  * that import was made under the integration's CURRENT manifest                                         (else STALE_MANIFEST: the integration was revalidated since)
  * no alert (an unsolicited delivery, an AUIF error outside an import, an adapter failure) is newer than the integration's latest imports   (else the alert's code)
  * the module has recorded no handler failure                                                           (else ADAPTER_ERROR)
The record-level reasons are the builder's reading of "partial" and "type-mismatched" (interpretation I-136): a rejected row or an unreadable optional value means the figures
would silently lack or mis-state an input; a stale delivery means the source and APG disagree on which version is current.  Conflicts, duplicates and held records are NOT
reasons: under the existing M3 contract they are exclusions that every figure lists."""
from .intake import KIND_ALERT, KIND_LATEST, KIND_STATE, record_reasons

CAN, CANNOT = 'can_assess', 'cannot_assess'


def _r(code, scope, detail):
    return {'code': code, 'scope': scope, 'detail': str(detail)[:240]}


def assessment_status(scoped, expected, module=None):
    """expected: [(integration id, record type)] this tenant's assessment needs.  -> {'status', 'reasons': [{code, scope, detail}], 'checked': {...}}."""
    reasons = []
    states = {r.key: r.payload for r in scoped.query(KIND_STATE)}
    ptrs = {r.key: r.payload for r in scoped.query(KIND_LATEST)}
    iids = sorted({i for i, _ in expected})
    if not expected:
        reasons.append(_r('NOTHING_EXPECTED', '-', 'no integration is configured for this assessment'))
    for iid in iids:
        st = states.get(iid)
        if st is None:
            reasons.append(_r('NO_STATE', iid, 'AUIF has reported no state for this integration'))
        elif st['state'] != 'ACTIVE':
            reasons.append(_r('INTEGRATION_NOT_ACTIVE', iid, 'the integration is %s' % st['state']))
    seq = {}
    for iid, ent in expected:
        p = ptrs.get('%s/%s' % (iid, ent))
        scope = '%s/%s' % (iid, ent)
        if p is None:
            reasons.append(_r('NOT_IMPORTED', scope, 'no import of this record type has been applied'))
            continue
        seq.setdefault(iid, []).append(p['seq'])
        if p['status'] not in ('applied', 'applied_with_reasons') or p['reasons']:
            for code, detail in p['reasons'] or [('BLOCKED', 'the latest import was %s' % p['status'])]:
                reasons.append(_r(code, scope, detail))
        st = states.get(iid)
        if st is not None and p['manifest_ref'] != st['manifest_ref']:
            reasons.append(_r('STALE_MANIFEST', scope, 'imported under manifest %s; the integration is now under %s' % (p['manifest_ref'].get('version'), st['manifest_ref'].get('version'))))
    for r in scoped.query(KIND_ALERT):
        a = r.payload
        scope_ids = [a['integration_id']] if a.get('integration_id') in iids else iids
        floor = min((min(seq[i]) for i in scope_ids if i in seq), default=0)
        if any(i not in seq for i in scope_ids) or a['seq'] > floor:
            reasons.append(_r(a['code'], a.get('integration_id') or '-', a['detail']))
    if module is not None and getattr(module, 'handler_errors', None):
        reasons.append(_r('ADAPTER_ERROR', '-', '%d module handler failure(s)' % len(module.handler_errors)))
    uniq = sorted({(x['code'], x['scope'], x['detail']) for x in reasons})
    return {'status': CANNOT if uniq else CAN, 'reasons': [{'code': c, 'scope': s, 'detail': d} for c, s, d in uniq],
            'checked': {'integrations': iids, 'record_types': len(expected)}}


def receipt_status(receipts, expected_names):
    """The same gate for the M3 file path (used to compare assessment status between the two paths): every expected file was ingested and its receipt carries no
    record-level reason.  receipts: {file name: receipt}."""
    reasons = []
    for n in expected_names:
        r = receipts.get(n)
        if r is None:
            reasons.append(_r('NOT_IMPORTED', n, 'no receipt'))
            continue
        if r.get('status') == 'blocked':
            for code, detail in r.get('reasons', []):
                reasons.append(_r(code, n, detail))
            continue
        for code, detail in record_reasons(r):
            reasons.append(_r(code, n, detail))
    uniq = sorted({(x['code'], x['scope'], x['detail']) for x in reasons})
    return {'status': CANNOT if uniq else CAN, 'reasons': [{'code': c, 'scope': s, 'detail': d} for c, s, d in uniq]}
