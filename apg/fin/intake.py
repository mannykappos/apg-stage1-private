"""Intake of the records the financial core needs that M3 did not ingest: projects, contracts, variations, cost-to-complete forecast lines, retention, security
instruments, the funding facility and bank transactions.  Blueprint: Section 04 (same rules as M3), Section 05 section 4, Section 12 section 4.

It reuses the M3 mapping, delivery decision (new / duplicate / revision / stale / conflict) and record format exactly; only the entity rules differ.  M3 files are NOT
changed (M3 stays as delivered); the loop below mirrors `apg.ingest.pipeline.ingest_file` for the new entities.  Consolidating the two loops behind one `specs` argument
is a recommended refactor after M4 (logged as finding F-16), because a second copy of a delivery loop is a place where the two can drift.

Whether a stored fin record may be USED is decided by its intrinsic outcome (accepted / accepted_with_warnings / pending_reconciliation / quarantined).  Cross-record
checks (does the project exist, do two sources agree) are made by the calculations and show up in the figure as disputed or unknown inputs."""
from dataclasses import dataclass, field
from .. import canon, tenancy
from ..ports import ConflictError
from ..source_authority import ACCEPTED, ACCEPTED_W, PENDING, QUARANTINED
from ..ingest import INGEST_VERSION, mapping, pipeline
from ..ingest.mapping import Limits

FIN_SPECS = {
    'project': dict(material=(), positive=(), nonnegative=('contract_value_cents',), dates=()),
    'contract': dict(material=('original_contract_cents',), positive=('original_contract_cents',), dates=()),
    'variation': dict(material=(), positive=(), dates=('raised_date',)),
    'ctc_line': dict(material=('cost_to_complete_cents',), positive=(), nonnegative=('cost_to_complete_cents',), dates=('forecast_date',)),
    'retention': dict(material=('retention_held_cents',), positive=(), nonnegative=('retention_held_cents',), dates=()),
    'security': dict(material=('face_value_cents',), positive=('face_value_cents',), dates=()),
    'facility': dict(material=('limit_cents', 'drawn_cents', 'rate_bps'), positive=(), nonnegative=('limit_cents', 'drawn_cents', 'rate_bps'), dates=('statement_date',)),
    'bank_txn': dict(material=('amount_cents',), positive=(), dates=('txn_date',)),
}
FIN_ENTITIES = tuple(FIN_SPECS)
USABLE = (ACCEPTED, ACCEPTED_W)


@dataclass(frozen=True)
class FinIntakePolicy:
    """warn_unknown: {entity: (field, ...)} optional fields whose absence is only a warning.  A MATERIAL field is never relaxable."""
    warn_unknown: dict = field(default_factory=dict)
    future_days_allowed: int = 0
    limits: Limits = field(default_factory=Limits)

    def tolerates_missing(self, entity, fld, specs=None):
        return fld not in (specs or FIN_SPECS)[entity]['material'] and fld in self.warn_unknown.get(entity, ())


def intrinsic(entity, row, policy, received_date, specs):
    spec = specs[entity]
    pending, warn = [], []
    for p in row.problems:
        if p['severity'] == 'hold':
            pending.append(f'INVALID_VALUE:{p["field"]}:{p["code"]}')
    for f, reason in sorted(row.unknown.items()):
        if f in spec['material']:
            pending.append(f'MATERIAL_VALUE_UNKNOWN:{f}')
        elif reason == 'invalid':
            continue
        elif policy.tolerates_missing(entity, f, specs):
            warn.append(f'VALUE_MISSING:{f}')
        else:
            pending.append(f'CRITICAL_VALUE_MISSING:{f}')
    for f in spec['positive']:
        v = row.mapped.get(f)
        if isinstance(v, int) and not isinstance(v, bool) and v <= 0:
            pending.append(f'SIGN_CONVENTION:{f}')
    for f in spec.get('nonnegative', ()):                  # zero is a real value (nothing withheld); below zero is a sign or entry error and is held, never used
        v = row.mapped.get(f)
        if isinstance(v, int) and not isinstance(v, bool) and v < 0:
            pending.append(f'SIGN_CONVENTION:{f}')
    limit = pipeline._add_days(received_date, policy.future_days_allowed)
    for f in spec['dates']:
        v = row.mapped.get(f)
        if isinstance(v, str) and v > limit:
            pending.append(f'FUTURE_DATED:{f}')
    for w in row.warnings:
        warn.append(f'{w["code"]}:{w["field"]}')
    return sorted(set(pending)), sorted(set(warn))


def ingest_fin_file(scoped, clock, template, data, source, file_name='', policy=None, revision_field=None, specs=None):
    """-> receipt dict (also stored).  Same semantics as the M3 ingest_file; see the module note.  `specs` (default FIN_SPECS) lets a later milestone add entities
    with the same delivery rules instead of copying this loop (M5 passes its own, closing finding F-16)."""
    specs = specs or FIN_SPECS
    policy = policy or FinIntakePolicy()
    if not isinstance(source, str) or not source.strip():
        raise pipeline.IngestError('a source identity is required')
    entity = template.get('target_entity') if isinstance(template, dict) else None
    if entity not in specs:
        raise pipeline.IngestError(f'no financial-core intake rules for entity {entity!r}')
    ctx, now = scoped.ctx, clock.now()
    corr = f'ingest:{now}'
    try:
        parse = mapping.apply_template(template, data, policy.limits)
    except mapping.FileRejected as e:
        scoped.log('ingest.file_rejected', file_name or 'file', 'rejected', reason=e.code, correlation_id=corr, detail={'detail': e.detail[:200], 'template': template.get('template_id', '')})
        return {'status': 'file_rejected', 'code': e.code, 'detail': e.detail, 'replay': False}
    rkey = pipeline.receipt_key(parse.file_sha256, parse.mapping_version, source)
    prior = scoped.get('ingest_receipt', rkey)
    if prior is not None:
        scoped.log('ingest.replay', rkey, 'no_change', reason='same file, template and source already ingested', correlation_id=corr, detail={'file_sha256': parse.file_sha256})
        out = dict(prior.payload)
        out['replay'] = True
        return out
    stripped, clean_raw = set(), {}
    for r in parse.rows:
        clean, claims = tenancy.screen_payload(ctx, r.raw, scoped._audit)
        clean_raw[r.row_no] = clean
        stripped.update(c[0].split('.')[-1] for c in claims)
    stripped.update(h for h in parse.header if tenancy.is_claim_key(h))
    received_date = now[:10]
    base_prov = {'file_sha256': parse.file_sha256, 'file_name': file_name, 'template_id': parse.template_id, 'mapping_version': parse.mapping_version, 'ingest_version': INGEST_VERSION,
                 'received_at': now, 'uploaded_by': ctx.user_id, 'uploader_kind': ctx.actor_kind, 'source': source}
    overlay, base_rev, ops_extra, results = {}, {}, [], []
    counts = {'rows': len(parse.rows), 'new': 0, 'revision': 0, 'duplicate': 0, 'stale': 0, 'conflict': 0, 'rejected': 0, 'held_at_intake': 0}

    def latest(key):
        if key in overlay:
            return overlay[key]
        rec = scoped.get(entity, key)
        base_rev[key] = rec.revision if rec else 0
        overlay[key] = canon.deep_copy(rec.payload) if rec else None
        return overlay[key]

    for r in parse.rows:
        if r.rejected:
            counts['rejected'] += 1
            ops_extra.append(('ingest_reject', f'{parse.file_sha256}:{r.row_no}', {'entity': entity, 'row_no': r.row_no, 'raw': clean_raw[r.row_no], 'problems': [dict(p) for p in r.problems],
                                                                                  'provenance': dict(base_prov)}, 0))
            results.append({'row': r.row_no, 'key': r.natural_key, 'result': 'rejected', 'codes': sorted({p['code'] for p in r.problems})})
            continue
        rev = pipeline.parse_revision(r.mapped.get(revision_field)) if revision_field else None
        pending, warn = intrinsic(entity, r, policy, received_date, specs)
        if revision_field and r.mapped.get(revision_field) is not None and rev is None:
            warn = sorted(set(warn) | {'REVISION_UNPARSED'})
        prov = dict(base_prov, row_no=r.row_no)
        ch = pipeline.content_hash(r)
        existing = latest(r.natural_key)
        decision, detail = pipeline.decide(existing, ch, rev)
        row2 = mapping.RowResult(r.row_no, clean_raw[r.row_no], r.mapped, r.unknown, r.problems, r.warnings, r.natural_key, r.row_hash)
        payload = pipeline._record_payload(entity, source, row2, prov, rev, pending, warn)
        if decision in ('new', 'revision'):
            overlay[r.natural_key] = payload
            counts[decision] += 1
            counts['held_at_intake'] += 1 if pending else 0
        elif decision == 'duplicate':
            counts['duplicate'] += 1
            ops_extra.append(('ingest_duplicate', f'{parse.file_sha256}:{r.row_no}', {'entity': entity, 'duplicate_of': r.natural_key, 'content_hash': ch, 'raw': clean_raw[r.row_no], 'provenance': prov}, 0))
        elif decision == 'stale':
            counts['stale'] += 1
            ops_extra.append(('ingest_stale', f'{parse.file_sha256}:{r.row_no}', {'entity': entity, 'key': r.natural_key, 'incoming_revision': rev, 'stored_revision': existing['source_revision'],
                                                                                 'content_hash': ch, 'raw': clean_raw[r.row_no], 'provenance': prov}, 0))
        else:
            counts['conflict'] += 1
            cons = existing['conflict']['contenders'] if existing.get('conflict') else [pipeline._contender(existing)]
            if not any(c['content_hash'] == ch and c['source_revision'] == rev for c in cons):
                cons = cons + [pipeline._contender(payload)]
            overlay[r.natural_key] = pipeline._conflict_payload(entity, source, r.natural_key, cons)
        results.append({'row': r.row_no, 'key': r.natural_key, 'result': decision, 'detail': detail, 'pending': pending, 'warnings': warn})
    ops = [(entity, key, payload, base_rev.get(key, 0)) for key, payload in sorted(overlay.items()) if payload is not None]
    receipt = {'status': 'ingested', 'entity': entity, 'template_id': parse.template_id, 'mapping_version': parse.mapping_version, 'ingest_version': INGEST_VERSION, 'source': source,
               'file_name': file_name, 'file_sha256': parse.file_sha256, 'size': parse.size, 'received_at': now, 'uploaded_by': ctx.user_id, 'counts': counts,
               'blank_rows': parse.blank_rows, 'unmapped_columns': list(parse.unmapped_columns), 'stripped_scope_columns': sorted(stripped), 'results': results}
    ops.extend(ops_extra)
    ops.append(('ingest_receipt', rkey, receipt, 0))
    try:
        scoped.atomic(ops)
    except ConflictError:
        scoped.log('ingest.conflict_retry', rkey, 'not_applied', reason='a record changed while the file was being processed; nothing was written', correlation_id=corr)
        raise
    scoped.log('ingest.file_ingested', rkey, 'ok', reason=parse.template_id, correlation_id=corr, detail=dict(counts, file_sha256=parse.file_sha256))
    out = dict(receipt)
    out['replay'] = False
    return out


def outcome(payload):
    """The usable-or-not outcome of a stored fin record: a conflict marker is quarantined; otherwise the intrinsic outcome."""
    if payload.get('conflict'):
        return QUARANTINED
    return payload['intrinsic']['outcome']


def usable(payload):
    return outcome(payload) in USABLE
