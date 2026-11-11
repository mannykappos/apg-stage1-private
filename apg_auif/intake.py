"""From AUIF deliveries to APG records, with lineage, under the SAME rules as M3.  Blueprint: Section 04 (the M3 delivery rules); M8 authorisation (lineage; no fallback).

A closed batch (apg_auif.module.Batch) is checked, converted and written in ONE atomic call:

1. Integrity checks.  Every delivered object must be: for this tenant (context, object and observation agree); VALID; of the concept this record type maps to; from the
   integration, target system, environment and connector the batch was opened for; translated by the PINNED pack (id, version and hash) under the manifest the integration
   was ACTIVE with when the batch opened; with a provenance chain AUIF itself can reconstruct (auif.canonical.verify_chain) that names this object's observation; carrying
   every attribute of its definition, each as text; and its attributes must rebuild exactly the source record AUIF observed (the observation's payload hash) and its
   source identity.  The transport report must show a complete read with nothing invalid, ambiguous or failed, and AUIF's count of delivered objects must equal APG's.
   Any failure: NOTHING from the batch is written to the record collections; the batch is recorded as blocked with its reasons, and the assessment cannot proceed.
2. Conversion.  Each object is turned back into the template's row (source column -> text) and the UNCHANGED M3 mapping rules are applied to the rows in delivery order
   (apg.ingest.mapping.apply_template), so every value is parsed by exactly the code M3 uses.  The tenant screen M3 applies to every row is applied too.
3. Delivery decisions.  The functions M3 and M4 use (apg.ingest.pipeline: decide, intrinsic_findings, _record_payload, _conflict_payload, _contender, content_hash,
   parse_revision; apg.fin.intake.intrinsic) decide new / revision / duplicate / stale / conflict and the intrinsic outcome.  No new policy.
4. Record.  The record payload is the M3 payload; its `provenance` is the AUIF lineage (`lineage`).  The receipt goes to `ingest_receipt` like an M3 file receipt, so the
   existing source and quality views see it.
Record-level outcomes that M3 applies and reports (a rejected row, an optional value that could not be parsed, a stale delivery) are written as M3 writes them, and they ALSO
stop the assessment (apg_auif.gate).  Conflicts, duplicates and held records stay what they are in M3: exclusions that every figure lists.

Event deliveries (mode 'events') differ in one way, because AUIF never delivers an applied event twice: the in-order events of a call are written even while other events
of the stream wait (queued or deferred) or need reconciliation; those are recorded as outstanding and the assessment cannot proceed until none is left."""
import csv, io
from apg import canon, tenancy
from apg.ingest import INGEST_VERSION, mapping, pipeline
from apg.fin import intake as FI
from apg.ports import ConflictError

KIND_STATE, KIND_ALERT, KIND_BATCH, KIND_LATEST, KIND_COUNTER = 'auif_integration_state', 'auif_alert', 'auif_batch', 'auif_latest', 'auif_counter'
ERROR_CODES = {'TRANSLATION_INVALID': 'TRANSLATION_INVALID', 'AMBIGUOUS': 'AMBIGUOUS', 'TRANSLATION_FAILURE': 'TRANSLATION_FAILURE', 'PACK_INTEGRITY_FAILURE': 'PACK_INTEGRITY_FAILURE',
               'SOURCE_UNAVAILABLE': 'SOURCE_UNAVAILABLE', 'SOURCE_DATA_INVALID': 'SOURCE_DATA_INVALID', 'EVENT_REJECTED': 'EVENT_REJECTED',
               'IDENTITY_MISSING': 'IDENTITY_MISSING', 'RECORD_REFUSED': 'RECORD_REFUSED', 'CANONICAL_CONFLICT': 'CANONICAL_CONFLICT',      # APG-M8.1: AUIF rev14 reports these
               'MODULE_DELIVERY_FAILED': 'ADAPTER_ERROR'}                                                                                # per record instead of raising (M8-F6)
NOTICE = 'EVENT_NOT_APPLIED'                 # APG-M8.1: AUIF rev14 tells the module about every event it did not deliver (finding M8-F3 corrected); read in apply_batch
PENDING_STATES = {'QUEUED_AWAITING_PREDECESSOR': 'EVENTS_WAITING', 'DEFERRED': 'EVENTS_WAITING', 'RECONCILIATION_PENDING': 'EVENT_RECONCILIATION_PENDING',
                  'REJECTED_BY_POLICY': 'EVENT_REJECTED', 'NOT_APPLIED': 'EVENT_NOT_APPLIED'}      # NOT_APPLIED (M8.1): an in-order event AUIF has no entity mapping for
RECORD_LEVEL = ('ROW_REJECTED', 'VALUE_INVALID', 'STALE_DELIVERY')


class Binding:
    """One AUIF tenant bound to one APG tenant-scoped store.  integrations: {integration_id: {'source', 'pack_ref', 'fingerprints', 'target_system_id', 'environment_id',
    'connector_id', 'entities': {entity: {'family', 'template', 'policy', 'revision_field', 'concept', 'definition', 'file', 'model_version'}}}}."""
    def __init__(self, scoped, clock, integrations):
        self.scoped, self.clock, self.integrations = scoped, clock, integrations

    def expected(self):
        return [(iid, e) for iid, i in sorted(self.integrations.items()) for e in i['entities']]

    # ---- the per-tenant sequence: every state, alert and batch gets the next number in the same atomic write
    def _seq_op(self):
        cur = self.scoped.get(KIND_COUNTER, 'seq')
        n = (cur.payload['value'] if cur else 0) + 1
        return n, (KIND_COUNTER, 'seq', {'value': n}, cur.revision if cur else 0)

    def record_state(self, state):
        iid = state.get('integration_id')
        if iid not in self.integrations:
            return self.alert(None, 'UNKNOWN_INTEGRATION', 'state for %s' % str(iid)[:60])
        n, op = self._seq_op()
        mr = state.get('manifest_ref') or {}
        p = {'integration_id': iid, 'state': str(state.get('state')), 'state_since': str(state.get('state_since')), 'seq': n,
             'manifest_ref': {k: str(mr.get(k)) for k in ('id', 'version', 'hash')},
             'trust_basis': {k: bool(v) for k, v in (state.get('trust_basis') or {}).items()}, 'recorded_at': self.clock.now()}
        if state.get('last_failure'):
            p['last_failure_code'] = str(state['last_failure'].get('code'))
        if state.get('drift_evidence'):
            p['drift_id'] = str(state['drift_evidence'].get('drift_id'))
        cur = self.scoped.get(KIND_STATE, iid)
        self.scoped.atomic([op, (KIND_STATE, iid, p, cur.revision if cur else 0)])

    def alert(self, integration_id, code, detail):
        n, op = self._seq_op()
        self.scoped.atomic([op, (KIND_ALERT, '%08d' % n, {'integration_id': integration_id, 'code': code, 'detail': str(detail)[:200], 'seq': n, 'at': self.clock.now()}, 0)])
        self.scoped.log('auif.alert', integration_id or '-', 'blocked', reason=code, detail={'detail': str(detail)[:200]})

    def state(self, iid):
        r = self.scoped.get(KIND_STATE, iid)
        return r.payload if r else None


# ---------------------------------------------------------------- checks
def _step(chain, kind):
    s = [x for x in chain if isinstance(x, dict) and x.get('step_kind') == kind]
    return s[0] if len(s) == 1 else None


def _sha(o):
    from auif.util import sha
    return sha(o)


def check_delivery(bnd, batch, kind, obj, ob, integ, ent):
    """-> list of (code, detail) for one delivered object.  Empty = it may be converted."""
    from auif.canonical import verify_chain
    bad = []
    t = batch.tenant
    cid = str(obj.get('canonical_id'))[:80]
    if obj.get('tenant_id') != t or ob.get('tenant_id') != t:
        bad.append(('WRONG_TENANT', '%s: the object or its observation names another tenant' % cid))
    if obj.get('validation_state') != 'VALID':
        bad.append(('TRANSLATION_INVALID', '%s was delivered as %s' % (cid, obj.get('validation_state'))))
    if obj.get('canonical_type') != ent['concept'] or obj.get('canonical_model_version') != ent['model_version']:
        bad.append(('TYPE_MISMATCH', '%s is %s %s, not %s %s' % (cid, obj.get('canonical_type'), obj.get('canonical_model_version'), ent['concept'], ent['model_version'])))
    want = (integ['target_system_id'], integ['environment_id'], integ['connector_id'], 'apg', batch.entity)
    got = (ob.get('target_system_id'), ob.get('environment_id'), ob.get('connector_id'), ob.get('anchor_module'), (ob.get('source_object') or {}).get('object_type'))
    if got != want:
        bad.append(('LINEAGE_MISMATCH', '%s came from %s, not %s' % (cid, got, want)))
    chain = obj.get('provenance_chain') or []
    probs = verify_chain(chain)
    pk, fp, so, osv = _step(chain, 'TRANSLATION_PACK'), _step(chain, 'SCHEMA_FINGERPRINT'), _step(chain, 'SOURCE_OBJECT'), _step(chain, 'OBSERVATION')
    if probs or not (pk and fp and so and osv):
        bad.append(('LINEAGE_INCOMPLETE', '%s: %s' % (cid, (probs or ['a provenance step is missing or repeated'])[0])))
    else:
        pin = integ['pack_ref']
        if (pk.get('ref'), pk.get('version'), pk.get('hash')) != (pin['id'], pin['version'], pin['hash']) or (ob.get('translation_pack_id'), ob.get('translation_pack_version')) != (pin['id'], pin['version']):
            bad.append(('PACK_NOT_PINNED', '%s was translated by %s@%s, not the pinned %s@%s' % (cid, pk.get('ref'), pk.get('version'), pin['id'], pin['version'])))
        if fp.get('hash') != ob.get('schema_fingerprint') or ob.get('schema_fingerprint') not in integ['fingerprints']:
            bad.append(('SCHEMA_DRIFT', '%s: schema fingerprint is not one the pinned pack accepts' % cid))
        if osv.get('ref') != ob.get('observation_id') or so.get('ref') != '%s/%s' % (batch.entity, (ob.get('source_object') or {}).get('object_id')):
            bad.append(('LINEAGE_MISMATCH', '%s: the chain does not name this observation and source object' % cid))
    mv = ob.get('manifest_version')                                   # AUIF puts the whole manifest reference {id, version, hash} in this field
    if not isinstance(mv, dict) or {k: mv.get(k) for k in ('id', 'version', 'hash')} != batch.expect['manifest_ref']:
        bad.append(('STALE_MANIFEST', '%s carries manifest %s; the integration was ACTIVE with %s' % (cid, (mv or {}).get('version') if isinstance(mv, dict) else mv, batch.expect['manifest_ref']['version'])))
    if ob.get('ordering_state') != 'IN_ORDER':
        bad.append(('OUT_OF_ORDER', '%s was delivered %s' % (cid, ob.get('ordering_state'))))
    attrs = obj.get('attributes') or {}
    names = [a['name'] for a in ent['definition']['attributes']]
    missing, extra = [n for n in names if n not in attrs], sorted(set(attrs) - set(names))
    if missing:
        bad.append(('MISSING_FIELD', '%s lacks %s' % (cid, missing[:5])))
    if extra:
        bad.append(('UNEXPECTED_FIELD', '%s carries %s' % (cid, extra[:5])))
    if any(not isinstance(attrs.get(n), str) for n in names if n in attrs):
        bad.append(('TYPE_MISMATCH', '%s: an attribute is not text' % cid))
    if not bad:                                                      # the attributes must rebuild exactly what AUIF observed
        rec = source_record(ent, attrs)
        if _sha(rec) != ob.get('payload_hash'):
            bad.append(('PAYLOAD_MISMATCH', '%s does not rebuild the observed source record' % cid))
        keys = ent['template']['natural_key']
        sid = source_identity([rec[k] for k in keys])
        if (ob.get('source_object') or {}).get('object_id') != sid:
            bad.append(('IDENTITY_MISMATCH', '%s: source identity %r is not %r' % (cid, (ob.get('source_object') or {}).get('object_id'), sid)))
    return bad


def source_identity(values):
    """The source identity AUIF rev14 must have given the record, computed here independently from the record's own natural-key values (APG-M8.1): one value as its text;
    several as their texts in key order, joined by "|", with "\\" and "|" escaped (AUIF rev14's composite identity).  A different identity is IDENTITY_MISMATCH."""
    vals = [str(v) for v in values]
    return vals[0] if len(vals) == 1 else '|'.join(v.replace('\\', '\\\\').replace('|', '\\|') for v in vals)


def source_record(ent, attrs):
    """attributes -> {source column: text} (the record AUIF read: the pack maps each column to the attribute of the same field, one to one)."""
    return {a['constraints']['source_column']: attrs[a['name']] for a in ent['definition']['attributes'] if a['name'] in attrs}


def batch_checks(bnd, batch, report, integ):
    """Transport, notification and state checks for the batch as a whole.  -> (integrity reasons, pending reasons)."""
    bad, pending = [], []
    if batch.mode == 'sync':
        r = report or {}
        if report is None:
            bad.append(('SYNC_FAILED', 'no transport report'))
        else:
            if r.get('not_allowed'):
                bad.append(('SYNC_NOT_ALLOWED', 'AUIF did not allow reading %s in the integration\'s state' % batch.entity))
            if r.get('failed'):
                bad.append(('SYNC_FAILED', 'the read failed: %s' % r['failed']))
            if r.get('invalid'):
                bad.append(('TRANSLATION_INVALID', '%d object(s) were TRANSLATION_INVALID' % r['invalid']))
            if r.get('ambiguous'):
                bad.append(('AMBIGUOUS', '%d object(s) were AMBIGUOUS' % r['ambiguous']))
            for k, code in (('refused', 'RECORD_REFUSED'), ('conflict', 'CANONICAL_CONFLICT'), ('module_failed', 'ADAPTER_ERROR')):      # APG-M8.1: AUIF rev14's report
                if r.get(k):
                    bad.append((code, 'AUIF reported %d record(s) as %s' % (r[k], k)))
            read_nothing = not batch.deliveries and not r.get('invalid') and not r.get('ambiguous') and not r.get('failed') and not r.get('not_allowed') and \
                not r.get('refused') and not r.get('conflict') and not r.get('module_failed')
            if r.get('empty') or read_nothing:                           # M8-R1 (finding M8-F7): an empty source is not current data; records stored earlier are not made current by it
                bad.append(('SOURCE_EMPTY', 'AUIF read no records of %s (%s): an empty source cannot stand for current data' % (batch.entity, 'NO_DATA' if r.get('empty') else 'zero records delivered')))
            if not r.get('failed') and not r.get('not_allowed') and r.get('complete') is not True:    # APG-M8.1: AUIF rev14 says whether the read reached the end (M8-F5 corrected)
                bad.append(('SYNC_INCOMPLETE', 'AUIF does not report the read of %s as complete%s' % (batch.entity, ' (stopped at the page limit)' if r.get('stopped_at_page_limit') else '')))
            if r.get('delivered') != len(batch.deliveries):
                bad.append(('SYNC_INCOMPLETE', 'AUIF reported %s delivered objects; APG received %d' % (r.get('delivered'), len(batch.deliveries))))
    else:
        for res in report or []:
            st = res.get('ordering_state')
            if st in PENDING_STATES:
                pending.append((PENDING_STATES[st], 'event %s is %s' % (str(res.get('event_id'))[:60], st)))
    for e in batch.errors:
        if e.get('kind') == NOTICE and batch.mode == 'events':
            continue                                                     # not an integrity failure: apply_batch reads it against AUIF's ordering results
        why = e.get('reason') or e.get('canonical_id') or (e.get('error') if isinstance(e.get('error'), dict) else {}).get('code') or ''
        bad.append((ERROR_CODES.get(e.get('kind'), 'AUIF_ERROR'), '%s: %s' % (e.get('kind'), str(why)[:160])))
    for s in batch.states:
        if s.get('state') != 'ACTIVE':
            bad.append(('INTEGRATION_NOT_ACTIVE', 'the integration moved to %s during the import' % s.get('state')))
    now = bnd.state(batch.integration_id)
    if now is None or now['state'] != 'ACTIVE':
        bad.append(('INTEGRATION_NOT_ACTIVE', 'the integration is %s' % (now or {}).get('state', 'unknown')))
    elif now['manifest_ref'] != batch.expect['manifest_ref']:
        bad.append(('STALE_MANIFEST', 'the manifest changed during the import (%s -> %s)' % (batch.expect['manifest_ref']['version'], now['manifest_ref']['version'])))
    bad += list(batch.refusals)
    return bad, pending


def notice_problems(batch, results):
    """APG-M8.1: AUIF rev14 reports an event that was not applied twice - in the ordering results the caller receives and as an EVENT_NOT_APPLIED notice to the module.
    Both must agree: every notice names an event of these results with the same ordering state, and every waiting, deferred or reconciliation-pending result has its
    notice.  A disagreement does not undo what AUIF applied (AUIF never delivers an applied event twice); it is recorded as a pending reason, so the assessment waits."""
    told = {}
    for e in batch.errors:
        if e.get('kind') == NOTICE:
            told[str(e.get('event_id'))] = e.get('ordering_state')
    got = {str(r.get('event_id')): r.get('ordering_state') for r in results}
    out = []
    for eid, st in sorted(told.items()):
        if got.get(eid) != st:
            out.append(('EVENT_NOTICE_MISMATCH', 'AUIF told the module that event %s is %s; its ordering result says %s' % (eid[:60], st, got.get(eid))))
    for eid, st in sorted(got.items()):
        if st in ('QUEUED_AWAITING_PREDECESSOR', 'DEFERRED', 'RECONCILIATION_PENDING') and told.get(eid) != st:      # (a rejection by AUIF's input guard has its own error)
            out.append(('EVENT_NOTICE_MISMATCH', 'event %s is %s but AUIF did not tell the module' % (eid[:60], st)))
    return out


# ---------------------------------------------------------------- conversion
def rows_csv(template, records):
    """The rows as the template's file layout, every cell quoted, so the M3 parser reads back exactly these texts."""
    b = io.StringIO()
    w = csv.writer(b, delimiter=template['file']['delimiter'], quoting=csv.QUOTE_ALL, lineterminator='\n')
    cols = [c['source_column'] for c in template['columns']]
    w.writerow(cols)
    for rec in records:
        w.writerow([rec[c] for c in cols])
    return b.getvalue().encode(template['file']['encoding'])


def _blank(rec):
    return all(str(v).strip() == '' for v in rec.values())


def effective(ent, mapped):
    f = ent['definition']['effective_time']['field']
    if not f:
        return None, 'none: this record type carries no business date'
    v = mapped.get(f)
    return (v, 'field:' + f) if isinstance(v, str) else (None, 'unknown: %s is blank or could not be read' % f)


def lineage(bnd, batch, integ, ent, kind, obj, ob, row_no, mapped, now):
    chain = obj['provenance_chain']
    pk = _step(chain, 'TRANSLATION_PACK')
    eff, basis = effective(ent, mapped)
    out = {'path': 'auif', 'integration_id': batch.integration_id, 'source_system': ob['source_system'], 'source_record_id': ob['source_object']['object_id'],
           'source_object_type': ob['source_object']['object_type'], 'translation_pack_id': pk['ref'], 'translation_pack_version': pk['version'],
           'translation_pack_hash': pk['hash'], 'canonical_id': obj['canonical_id'], 'canonical_type': obj['canonical_type'], 'canonical_model_version': obj['canonical_model_version'],
           'validation_state': obj['validation_state'], 'observation_id': ob['observation_id'], 'observed_at': ob['observed_at'], 'auif_received_at': ob['received_at'],
           'effective_at': eff, 'effective_time_basis': basis, 'manifest_id': ob['manifest_version']['id'], 'manifest_version': ob['manifest_version']['version'],
           'manifest_hash': ob['manifest_version']['hash'],
           'schema_fingerprint': ob['schema_fingerprint'], 'connector_id': ob['connector_id'], 'target_system_id': ob['target_system_id'], 'environment_id': ob['environment_id'],
           'payload_hash': ob['payload_hash'], 'adapter_sequence': ob['adapter_sequence'], 'ordering_state': ob['ordering_state'], 'delivery': kind,
           'provenance_chain': [{k: v for k, v in s.items()} for s in chain],
           'template_id': ent['template']['template_id'], 'mapping_version': mapping.template_digest(ent['template']), 'ingest_version': INGEST_VERSION, 'received_at': now,
           'uploaded_by': bnd.scoped.ctx.user_id, 'uploader_kind': bnd.scoped.ctx.actor_kind, 'source': integ['source'], 'file_name': ent['file'], 'row_no': row_no,
           'batch_id': batch.batch_id}
    if ob.get('source_sequence') is not None:
        out['source_sequence'] = ob['source_sequence']
    if (ob.get('causal') or {}).get('event_id'):
        out['causal_event_id'] = ob['causal']['event_id']
    return out


LINEAGE_FIELDS = ('integration_id', 'source_system', 'source_record_id', 'translation_pack_id', 'translation_pack_hash', 'canonical_id', 'observed_at', 'effective_time_basis',
                  'validation_state', 'observation_id', 'manifest_version', 'payload_hash', 'provenance_chain', 'batch_id')


def record_reasons(receipt):
    """The record-level outcomes in a receipt that stop the assessment (also used for an M3 file receipt).  -> [(code, detail)]."""
    out = []
    if receipt.get('status') != 'ingested':
        out.append(('FILE_REJECTED', '%s: %s' % (receipt.get('file_name') or receipt.get('entity'), receipt.get('code'))))
        return out
    c = receipt['counts']
    if c.get('rejected'):
        out.append(('ROW_REJECTED', '%s: %d row(s) rejected' % (receipt['entity'], c['rejected'])))
    if c.get('stale'):
        out.append(('STALE_DELIVERY', '%s: %d delivery(ies) older than the stored revision' % (receipt['entity'], c['stale'])))
    inv = sorted({r['key'] for r in receipt.get('results', []) if any(p.startswith('INVALID_VALUE:') for p in r.get('pending', []))})
    if inv:
        out.append(('VALUE_INVALID', '%s: an optional value could not be read in %s' % (receipt['entity'], ', '.join(inv[:5]))))
    return out


def _intrinsic(ent, row, received_date):
    if ent['family'] == 'm3':
        return pipeline.intrinsic_findings(ent['template']['target_entity'], row, ent['policy'], received_date)
    from apg.det.intake import DET_SPECS
    specs = FI.FIN_SPECS if ent['family'] == 'fin' else DET_SPECS
    return FI.intrinsic(ent['template']['target_entity'], row, ent['policy'], received_date, specs)


# ---------------------------------------------------------------- apply
def apply_batch(bnd, batch, report=None, sequencer_pending=()):
    """-> summary dict {'status': 'applied' | 'replay' | 'blocked', 'reasons', 'receipt', 'batch_key'}.  Writes atomically; never raises for bad data."""
    scoped, now = bnd.scoped, bnd.clock.now()
    cur = scoped.get(KIND_COUNTER, 'seq')
    batch.batch_id = '%08d' % ((cur.payload['value'] if cur else 0) + 1)          # the sequence number this batch's own write will take
    integ = bnd.integrations[batch.integration_id]
    ent = integ['entities'][batch.entity]
    entity, tpl = ent['template']['target_entity'], ent['template']
    bad, pending = batch_checks(bnd, batch, report, integ)
    deliveries = []
    for kind, obj, ob in batch.deliveries:
        probs = check_delivery(bnd, batch, kind, obj, ob, integ, ent)
        bad += probs
        if not probs:
            deliveries.append((kind, obj, ob, source_record(ent, obj['attributes'])))
    prev = scoped.get(KIND_LATEST, '%s/%s' % (batch.integration_id, batch.entity))
    outstanding = dict((prev.payload.get('outstanding_events') or {}) if prev else {})
    if batch.mode == 'events':
        for res in report or []:
            eid, st = str(res.get('event_id')), res.get('ordering_state')
            if st == 'IN_ORDER':
                outstanding.pop(eid, None)
            elif st in PENDING_STATES:
                outstanding[eid] = st
        for eid in sequencer_pending:
            outstanding.setdefault(str(eid), 'QUEUED_AWAITING_PREDECESSOR')
        mismatch = notice_problems(batch, report or [])
        for e in batch.errors:                                           # an in-order event AUIF did not apply (no entity mapping): outstanding until resolved
            if e.get('kind') == NOTICE and e.get('ordering_state') == 'IN_ORDER':
                outstanding[str(e.get('event_id'))] = 'NOT_APPLIED'
        pending = [(PENDING_STATES[st], 'event %s is %s' % (eid, st)) for eid, st in sorted(outstanding.items())] + mismatch
    if bad:
        return _blocked(bnd, batch, bad, outstanding, now)
    records = [d[3] for d in deliveries]
    try:
        parse = mapping.apply_template(tpl, rows_csv(tpl, records), ent['policy'].limits)
    except mapping.FileRejected as e:
        return _blocked(bnd, batch, [('FILE_LIMIT', '%s: %s' % (e.code, e.detail[:120]))], outstanding, now)
    except (UnicodeEncodeError, ValueError) as e:
        return _blocked(bnd, batch, [('ADAPTER_ERROR', 'a value cannot be written in the template encoding: %s' % type(e).__name__)], outstanding, now)
    nonblank = [d for d in deliveries if not _blank(d[3])]
    if len(nonblank) != len(parse.rows):
        return _blocked(bnd, batch, [('ADAPTER_ERROR', 'rows and deliveries do not line up')], outstanding, now)
    ctx = scoped.ctx
    stripped, clean_raw = set(), {}
    try:
        for r in parse.rows:
            clean, claims = tenancy.screen_payload(ctx, r.raw, scoped._audit)
            clean_raw[r.row_no] = clean
            stripped.update(c[0].split('.')[-1] for c in claims)
    except tenancy.TenantMismatch as e:
        return _blocked(bnd, batch, [('WRONG_TENANT', 'a delivered value names another tenant (%s)' % str(e)[:120])], outstanding, now)
    stripped.update(h for h in parse.header if tenancy.is_claim_key(h))
    rev_field = ent['revision_field']
    digest = canon.digest({'integration': batch.integration_id, 'entity': entity, 'pack': integ['pack_ref'], 'mapping_version': parse.mapping_version, 'source': integ['source'],
                           'revision_field': rev_field, 'mode': batch.mode, 'payloads': [d[2]['payload_hash'] for d in deliveries]})
    rkey = 'auif:%s:%s:%s' % (digest, parse.mapping_version[:16], integ['source'])
    prior = scoped.get('ingest_receipt', rkey)
    if prior is not None:
        scoped.log('ingest.replay', rkey, 'no_change', reason='the same AUIF delivery was already applied', detail={'integration': batch.integration_id, 'entity': entity})
        return _done(bnd, batch, 'replay', dict(prior.payload), [], record_reasons(prior.payload), pending, outstanding, now, rkey)
    received_date = now[:10]
    overlay, base_rev, ops_extra, results = {}, {}, [], []
    counts = {'rows': len(parse.rows), 'new': 0, 'revision': 0, 'duplicate': 0, 'stale': 0, 'conflict': 0, 'rejected': 0, 'held_at_intake': 0}

    def latest(key):
        if key in overlay:
            return overlay[key]
        rec = scoped.get(entity, key)
        base_rev[key] = rec.revision if rec else 0
        overlay[key] = canon.deep_copy(rec.payload) if rec else None
        return overlay[key]

    for r, (kind, obj, ob, _) in zip(parse.rows, nonblank):
        prov = lineage(bnd, batch, integ, ent, kind, obj, ob, r.row_no, r.mapped, now)
        if r.rejected:
            counts['rejected'] += 1
            ops_extra.append(('ingest_reject', '%s:%d' % (batch.batch_id, r.row_no), {'entity': entity, 'row_no': r.row_no, 'raw': clean_raw[r.row_no],
                                                                                       'problems': [dict(p) for p in r.problems], 'provenance': prov}, 0))
            results.append({'row': r.row_no, 'key': r.natural_key, 'result': 'rejected', 'codes': sorted({p['code'] for p in r.problems})})
            continue
        rev = pipeline.parse_revision(r.mapped.get(rev_field)) if rev_field else None
        pend, warn = _intrinsic(ent, r, received_date)
        if rev_field and r.mapped.get(rev_field) is not None and rev is None:
            warn = sorted(set(warn) | {'REVISION_UNPARSED'})
        ch = pipeline.content_hash(r)
        existing = latest(r.natural_key)
        decision, detail = pipeline.decide(existing, ch, rev)
        row2 = mapping.RowResult(r.row_no, clean_raw[r.row_no], r.mapped, r.unknown, r.problems, r.warnings, r.natural_key, r.row_hash)
        payload = pipeline._record_payload(entity, integ['source'], row2, prov, rev, pend, warn)
        if decision in ('new', 'revision'):
            overlay[r.natural_key] = payload
            counts[decision] += 1
            counts['held_at_intake'] += 1 if pend else 0
        elif decision == 'duplicate':
            counts['duplicate'] += 1
            ops_extra.append(('ingest_duplicate', '%s:%d' % (batch.batch_id, r.row_no), {'entity': entity, 'duplicate_of': r.natural_key, 'content_hash': ch, 'raw': clean_raw[r.row_no],
                                                                                          'provenance': prov}, 0))
        elif decision == 'stale':
            counts['stale'] += 1
            ops_extra.append(('ingest_stale', '%s:%d' % (batch.batch_id, r.row_no), {'entity': entity, 'key': r.natural_key, 'incoming_revision': rev,
                                                                                      'stored_revision': existing['source_revision'], 'content_hash': ch, 'raw': clean_raw[r.row_no], 'provenance': prov}, 0))
        else:
            counts['conflict'] += 1
            cons = existing['conflict']['contenders'] if existing.get('conflict') else [pipeline._contender(existing)]
            if not any(c['content_hash'] == ch and c['source_revision'] == rev for c in cons):
                cons = cons + [pipeline._contender(payload)]
            overlay[r.natural_key] = pipeline._conflict_payload(entity, integ['source'], r.natural_key, cons)
        results.append({'row': r.row_no, 'key': r.natural_key, 'result': decision, 'detail': detail, 'pending': pend, 'warnings': warn})
    ops = [(entity, key, payload, base_rev.get(key, 0)) for key, payload in sorted(overlay.items()) if payload is not None]
    receipt = {'status': 'ingested', 'entity': entity, 'template_id': parse.template_id, 'mapping_version': parse.mapping_version, 'ingest_version': INGEST_VERSION,
               'source': integ['source'], 'file_name': ent['file'], 'file_sha256': None, 'size': None, 'received_at': now, 'uploaded_by': ctx.user_id, 'counts': counts,
               'blank_rows': len(deliveries) - len(nonblank), 'unmapped_columns': [], 'stripped_scope_columns': sorted(stripped), 'results': results,
               'auif': {'integration_id': batch.integration_id, 'batch_id': batch.batch_id, 'mode': batch.mode, 'pack_ref': dict(integ['pack_ref']),
                        'manifest_ref': dict(batch.expect['manifest_ref']), 'deliveries': len(deliveries), 'delivery_digest': digest}}
    ops.extend(ops_extra)
    ops.append(('ingest_receipt', rkey, receipt, 0))
    return _done(bnd, batch, 'applied', receipt, ops, record_reasons(receipt), pending, outstanding, now, rkey)


def _pointer(batch, status, reasons, outstanding, n, now, rkey=None):
    return {'integration_id': batch.integration_id, 'entity': batch.entity, 'batch': '%08d' % n, 'status': status, 'mode': batch.mode,
            'reasons': [list(x) for x in reasons], 'manifest_ref': dict(batch.expect['manifest_ref']), 'outstanding_events': dict(sorted(outstanding.items())),
            'receipt': rkey, 'seq': n, 'at': now}


def _write(bnd, batch, ops, status, reasons, outstanding, now, rkey=None, extra=None):
    scoped = bnd.scoped
    n, cop = bnd._seq_op()
    if '%08d' % n != batch.batch_id:
        raise ConflictError('another write took sequence number %s' % batch.batch_id)
    ptr_key = '%s/%s' % (batch.integration_id, batch.entity)
    cur = scoped.get(KIND_LATEST, ptr_key)
    rec = dict(_pointer(batch, status, reasons, outstanding, n, now, rkey), **(extra or {}))
    all_ops = [cop] + list(ops) + [(KIND_BATCH, '%08d' % n, dict(rec, batch_id=batch.batch_id), 0), (KIND_LATEST, ptr_key, rec, cur.revision if cur else 0)]
    scoped.atomic(all_ops)
    return n


def _blocked(bnd, batch, reasons, outstanding, now):
    reasons = sorted({(c, d) for c, d in reasons})
    detail = {'deliveries': len(batch.deliveries), 'errors': len(batch.errors), 'refused': [{'code': c, 'detail': d} for c, d in reasons[:50]]}
    try:
        _write(bnd, batch, [], 'blocked', reasons, outstanding, now, extra={'detail': detail})
    except ConflictError:
        cur = bnd.scoped.get(KIND_COUNTER, 'seq')
        batch.batch_id = '%08d' % ((cur.payload['value'] if cur else 0) + 1)
        _write(bnd, batch, [], 'blocked', reasons + [('COMMIT_CONFLICT', 'retried after a concurrent write')], outstanding, now, extra={'detail': detail})
    bnd.scoped.log('auif.batch_blocked', '%s/%s' % (batch.integration_id, batch.entity), 'blocked', reason=reasons[0][0], detail={'reasons': [c for c, _ in reasons][:20]})
    return {'status': 'blocked', 'reasons': reasons, 'receipt': None}


def _done(bnd, batch, status, receipt, ops, rec_reasons, pending, outstanding, now, rkey):
    reasons = sorted(set(map(tuple, rec_reasons)) | set(map(tuple, pending)))
    try:
        _write(bnd, batch, ops, 'applied' if not reasons else 'applied_with_reasons', reasons, outstanding, now, rkey)
    except ConflictError:
        bnd.scoped.log('ingest.conflict_retry', rkey, 'not_applied', reason='a record changed while the AUIF batch was being applied; nothing was written')
        return _blocked(bnd, batch, [('COMMIT_CONFLICT', 'a record changed while the batch was being applied; nothing was written')], outstanding, now)
    bnd.scoped.log('ingest.auif_batch_applied' if status == 'applied' else 'ingest.replay', rkey, 'ok', reason=receipt.get('template_id', ''),
                   detail=dict(receipt.get('counts', {}), integration=batch.integration_id))
    out = dict(receipt)
    out['replay'] = status == 'replay'
    return {'status': status, 'reasons': reasons, 'receipt': out}
