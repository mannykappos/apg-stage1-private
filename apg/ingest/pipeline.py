"""Receive -> validate -> normalise -> store with provenance.  Blueprint: Section 04 sections 3, 7, 8, 10, 13, 15, 17, 18; acceptance PG-DI-AC-08, 09, 10, 11, 15, 17.

`ingest_file` takes the bytes of one file and a mapping template.  Everything it learns about a delivery is judged against what is ALREADY stored:

  same key, same content, same revision        -> DUPLICATE DELIVERY: no new record, no second effect (evidence of the delivery is kept)
  same key, higher declared source revision    -> REVISION: a new revision of the record; the older one stays in history
  same key, lower declared source revision     -> STALE: recorded, the newer state is NOT reverted
  same key, different content, no way to order -> CONFLICT: the record becomes a QUARANTINED conflict marker holding every contender (sorted, so arrival order
                                                  cannot change the result); a later, higher revision may supersede it, a person may correct or reject it
  a row that cannot be a record at all         -> REJECTED row, kept with its raw text and reasons

All writes of one file (records, rejects, duplicate evidence and the receipt) go in ONE atomic call with expected-revision checks.  A crash or a concurrent writer
therefore leaves no half-applied file, and running the same file again is a recorded no-op.  Whether a stored record may be USED is decided afterwards by
`reconcile`, which is a pure function of what is stored; the pipeline only decides what was DELIVERED.
The original text of every cell, the file hash, the row number, the template and mapping version and the uploader are stored with each record."""
import re
from .. import canon, tenancy
from ..ports import ConflictError
from ..source_authority import ACCEPTED, ACCEPTED_W, PENDING, QUARANTINED, REJECTED
from . import INGEST_VERSION, mapping
from .specs import SPECS, IngestPolicy

REVISION = re.compile(r'(?:R|r)?([0-9]{1,9})')


class IngestError(Exception):
    pass


def parse_revision(text):
    """'3' and 'R3' are revision 3.  Anything else has no usable order (None)."""
    if isinstance(text, int) and not isinstance(text, bool):
        return text
    if isinstance(text, str):
        m = REVISION.fullmatch(text.strip())
        if m:
            return int(m.group(1))
    return None


def _date(ts):
    return ts[:10]


def _add_days(iso, days):
    import datetime
    return (datetime.date.fromisoformat(iso) + datetime.timedelta(days=days)).isoformat()


def intrinsic_findings(entity, row, policy, received_date):
    """What is wrong with this row on its own (no other record needed).  -> (pending_codes, warning_codes)."""
    spec = SPECS[entity]
    pending, warn = [], []
    for p in row.problems:                                            # 'hold' problems (a bad optional value)
        if p['severity'] == 'hold':
            pending.append(f'INVALID_VALUE:{p["field"]}:{p["code"]}')
    for f, reason in sorted(row.unknown.items()):
        if f in spec['material']:
            pending.append(f'MATERIAL_VALUE_UNKNOWN:{f}')
        elif reason == 'invalid':
            continue                                                  # already reported above
        elif policy.tolerates_missing(entity, f):
            warn.append(f'VALUE_MISSING:{f}')
        else:
            pending.append(f'CRITICAL_VALUE_MISSING:{f}')
    for f in spec['positive']:
        v = row.mapped.get(f)
        if isinstance(v, int) and not isinstance(v, bool) and v <= 0:
            pending.append(f'SIGN_CONVENTION:{f}')
    limit = _add_days(received_date, policy.future_days_allowed)
    for f in spec['dates']:
        v = row.mapped.get(f)
        if isinstance(v, str) and v > limit:
            pending.append(f'FUTURE_DATED:{f}')
    if entity == 'supplier_quote' and row.mapped.get('valid_until') and row.mapped.get('issue_date') and row.mapped['valid_until'] < row.mapped['issue_date']:
        pending.append('DATE_ORDER:valid_until_before_issue_date')
    for w in row.warnings:
        warn.append(f'{w["code"]}:{w["field"]}')
    return sorted(set(pending)), sorted(set(warn))


def _content(row):
    return {'fields': row.mapped, 'unknown': row.unknown}


def content_hash(row):
    return canon.digest(_content(row))


def _contender(payload):
    return {k: payload[k] for k in ('content_hash', 'source_revision', 'fields', 'unknown', 'raw', 'provenance')}


def decide(existing, incoming_hash, incoming_rev):
    """-> (decision, detail) for a delivery of a key that may already exist.  `existing` is the latest stored payload or None."""
    if existing is None:
        return 'new', ''
    if existing.get('conflict'):
        cons = existing['conflict']['contenders']
        if any(c['content_hash'] == incoming_hash and c['source_revision'] == incoming_rev for c in cons):
            return 'duplicate', 'already one of the conflicting versions'
        revs = [c['source_revision'] for c in cons]
        if incoming_rev is not None and all(r is not None for r in revs) and incoming_rev > max(revs):
            return 'revision', f'revision {incoming_rev} is higher than every conflicting version'
        return 'conflict', 'another version of an unresolved conflict'
    er = existing['source_revision']
    if existing['content_hash'] == incoming_hash and (er == incoming_rev or er is None or incoming_rev is None):
        return 'duplicate', ''
    if er is not None and incoming_rev is not None:
        if incoming_rev > er:
            return 'revision', f'revision {incoming_rev} supersedes {er}'
        if incoming_rev < er:
            return 'stale', f'revision {incoming_rev} is older than the stored revision {er}'
        return 'conflict', f'different content at the same revision {er}'
    return 'conflict', 'different content and the order of the versions is unknown'


def _record_payload(entity, source, row, provenance, rev, pending, warn):
    return {'entity': entity, 'source': source, 'fields': row.mapped, 'unknown': row.unknown, 'raw': row.raw, 'provenance': provenance, 'source_revision': rev,
            'row_hash': row.row_hash, 'content_hash': content_hash(row), 'conflict': None,
            'intrinsic': {'outcome': PENDING if pending else (ACCEPTED_W if warn else ACCEPTED), 'pending': pending, 'warnings': warn}}


def _conflict_payload(entity, source, key, contenders):
    cons = sorted(contenders, key=lambda c: (c['content_hash'], -1 if c['source_revision'] is None else c['source_revision']))
    return {'entity': entity, 'source': source, 'fields': {}, 'unknown': {}, 'raw': {}, 'provenance': {}, 'source_revision': None, 'row_hash': '', 'content_hash': '',
            'conflict': {'key': key, 'contenders': cons},
            'intrinsic': {'outcome': QUARANTINED, 'pending': ['CONFLICT_SAME_KEY'], 'warnings': []}}


def receipt_key(file_sha, mapping_version, source):
    return f'{file_sha}:{mapping_version[:16]}:{source}'


def ingest_file(scoped, clock, template, data, source, file_name='', policy=None, revision_field=None):
    """-> receipt dict (also stored).  `replay` is True when this exact file, template and source were already ingested (nothing changes).
    Raises tenancy errors for a tenant claim naming another tenant (the whole file is refused and the refusal is audited)."""
    policy = policy or IngestPolicy()
    if not isinstance(source, str) or not source.strip():
        raise IngestError('a source identity is required')
    entity = template.get('target_entity') if isinstance(template, dict) else None
    if entity not in SPECS:
        raise IngestError(f'no ingestion rules for entity {entity!r}')
    ctx, now = scoped.ctx, clock.now()
    corr = f'ingest:{now}'
    try:
        parse = mapping.apply_template(template, data, policy.limits)
    except mapping.FileRejected as e:
        scoped.log('ingest.file_rejected', file_name or 'file', 'rejected', reason=e.code, correlation_id=corr, detail={'detail': e.detail[:200], 'template': template.get('template_id', '')})
        return {'status': 'file_rejected', 'code': e.code, 'detail': e.detail, 'replay': False}
    rkey = receipt_key(parse.file_sha256, parse.mapping_version, source)
    prior = scoped.get('ingest_receipt', rkey)
    if prior is not None:
        scoped.log('ingest.replay', rkey, 'no_change', reason='same file, template and source already ingested', correlation_id=corr, detail={'file_sha256': parse.file_sha256})
        out = dict(prior.payload)
        out['replay'] = True
        return out
    # tenant claims anywhere in the file: refuse the whole file before anything is written; strip matching ones
    stripped = set()
    clean_raw = {}
    for r in parse.rows:
        clean, claims = tenancy.screen_payload(ctx, r.raw, scoped._audit)
        clean_raw[r.row_no] = clean
        stripped.update(c[0].split('.')[-1] for c in claims)
    if any(h for h in parse.header if tenancy.is_claim_key(h)):
        stripped.update(h for h in parse.header if tenancy.is_claim_key(h))
    received_date = _date(now)
    base_prov = {'file_sha256': parse.file_sha256, 'file_name': file_name, 'template_id': parse.template_id, 'mapping_version': parse.mapping_version,
                 'ingest_version': INGEST_VERSION, 'received_at': now, 'uploaded_by': ctx.user_id, 'uploader_kind': ctx.actor_kind, 'source': source}
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
        rev = None
        if revision_field:
            rv = r.mapped.get(revision_field)
            rev = parse_revision(rv)
        pending, warn = intrinsic_findings(entity, r, policy, received_date)
        if revision_field and r.mapped.get(revision_field) is not None and rev is None:
            warn = sorted(set(warn) | {'REVISION_UNPARSED'})
        prov = dict(base_prov, row_no=r.row_no)
        ch = content_hash(r)
        existing = latest(r.natural_key)
        decision, detail = decide(existing, ch, rev)
        row2 = mapping.RowResult(r.row_no, clean_raw[r.row_no], r.mapped, r.unknown, r.problems, r.warnings, r.natural_key, r.row_hash)
        payload = _record_payload(entity, source, row2, prov, rev, pending, warn)
        if decision == 'new' or decision == 'revision':
            overlay[r.natural_key] = payload
            counts['new' if decision == 'new' else 'revision'] += 1
            counts['held_at_intake'] += 1 if pending else 0
        elif decision == 'duplicate':
            counts['duplicate'] += 1
            ops_extra.append(('ingest_duplicate', f'{parse.file_sha256}:{r.row_no}', {'entity': entity, 'duplicate_of': r.natural_key, 'content_hash': ch, 'raw': clean_raw[r.row_no], 'provenance': prov}, 0))
        elif decision == 'stale':
            counts['stale'] += 1
            ops_extra.append(('ingest_stale', f'{parse.file_sha256}:{r.row_no}', {'entity': entity, 'key': r.natural_key, 'incoming_revision': rev, 'stored_revision': existing['source_revision'],
                                                                                 'content_hash': ch, 'raw': clean_raw[r.row_no], 'provenance': prov}, 0))
        else:                                                             # conflict
            counts['conflict'] += 1
            cons = existing['conflict']['contenders'] if existing.get('conflict') else [_contender(existing)]
            if not any(c['content_hash'] == ch and c['source_revision'] == rev for c in cons):
                cons = cons + [_contender(payload)]
            overlay[r.natural_key] = _conflict_payload(entity, source, r.natural_key, cons)
        results.append({'row': r.row_no, 'key': r.natural_key, 'result': decision, 'detail': detail, 'pending': pending, 'warnings': warn})
    ops = []
    for key, payload in sorted(overlay.items()):
        if payload is None:
            continue
        ops.append((entity, key, payload, base_rev.get(key, 0)))
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
