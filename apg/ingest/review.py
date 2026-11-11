"""People's decisions on held records.  Blueprint: Section 04 sections 9 (promotion needs resolution, approvals and a recorded disposition), 11, 12.

Every function here takes the APPROVER'S OWN scoped store (their verified context).  Roles, human-only and distinct-approver rules come from the M2 QuarantineQueue.
A decision is stored; nothing is applied until `reconcile` runs again, and it applies only while the blocking facts are the ones the person saw."""
from .. import canon
from ..source_authority import AuthorityError
from .reconcile import ReviewQueue

ENTITY_ROLE = 'entity_steward'


def decide(scoped, ref, action, note, corrected_cents=None):
    """Accept / correct / reject / retain a held record.  A held record with SEVERAL different candidate values cannot simply be accepted: a person must say which value."""
    q = ReviewQueue(scoped)
    item = scoped.get(q.KIND, ref)
    if item is None:
        raise AuthorityError('no such held record')
    values = {c[1] for c in item.payload['candidates']}
    if action == 'accept' and len(values) > 1:
        scoped.log('quarantine.refused', ref, 'refused', reason='several different values: a person must correct or reject')
        raise AuthorityError('this record has several different values; choose one with a correction or reject it')
    return q.dispose(scoped.ctx, ref, action, note, corrected_cents)


def resolve_supplier(scoped, kind, key, supplier_id, note):
    """A person (human, role entity_steward) says which supplier a record means.  Stored with who/why; it applies only while the supplier text on the record is unchanged."""
    ctx = scoped.ctx
    if ctx.actor_kind != 'human' or ENTITY_ROLE not in ctx.roles:
        scoped.log('entity.refused', f'{kind}/{key}', 'refused', reason='supplier resolution needs a human entity steward')
        raise AuthorityError('supplier resolution needs a human holding the entity_steward role')
    if not isinstance(note, str) or not note.strip():
        raise AuthorityError('a note is required')
    rec = scoped.get(kind, key)
    sup = scoped.get('supplier', supplier_id) if isinstance(supplier_id, str) else None
    if rec is None or sup is None:
        raise AuthorityError('unknown record or supplier')
    from .specs import SPECS
    text = rec.payload['fields'].get(SPECS[kind]['supplier_field'] or '')
    if text is None:
        raise AuthorityError('this record has no supplier text to resolve')
    out = scoped.put('entity_resolution', f'{kind}/{key}', {'kind': kind, 'key': key, 'text': text, 'supplier_id': supplier_id, 'by': ctx.user_id, 'note': note})
    scoped.log('entity.resolved', f'{kind}/{key}', 'ok', reason=supplier_id)
    return out


def propose_alias(scoped, text, supplier_id):
    ctx = scoped.ctx
    if scoped.get('supplier', supplier_id) is None:
        raise AuthorityError('unknown supplier')
    return scoped.put('entity_alias', canon.digest(text)[:24], {'text': text, 'supplier_id': supplier_id, 'status': 'proposed', 'proposed_by': ctx.user_id, 'approved_by': None})


def approve_alias(scoped, text, note):
    ctx = scoped.ctx
    if ctx.actor_kind != 'human' or ENTITY_ROLE not in ctx.roles:
        raise AuthorityError('approving an alias needs a human entity steward')
    cur = scoped.get('entity_alias', canon.digest(text)[:24])
    if cur is None or cur.payload['status'] != 'proposed':
        raise AuthorityError('no proposed alias')
    if cur.payload['proposed_by'] == ctx.user_id:
        scoped.log('entity.refused', text[:40], 'refused', reason='the proposer cannot approve their own alias')
        raise AuthorityError('the proposer cannot approve their own alias')
    p = canon.deep_copy(cur.payload)
    p.update(status='approved', approved_by=ctx.user_id, note=note)
    return scoped.put('entity_alias', canon.digest(text)[:24], p, expected_revision=cur.revision)
