"""Choosing and pinning the stored records a calculation will read.  Blueprint: Section 05 section 13, PG-PC-AC-16, 17, 20.

`gather` reads the store ONCE and returns (refs, params): the exact revision of every record the calculation may use, and the parameters.  Nothing is pinned as "the latest" for
later: each pin is (kind, key, revision, payload hash).  Which project a record belongs to is decided by snap.project_of, the same function the calculations use, and a record
whose project cannot be told is pinned for every project (so a calculation can never be missing a record that might matter)."""
from ..repro import InputRef, pin_latest, ReproError
from .. import policy_approval as PA
from . import policy as P
from .snap import BASE_KINDS, FIN_KINDS, TENANT_KINDS, project_of


def _lookup(scoped):
    def look(kind, key):
        r = scoped.get(kind, key)
        return r.payload if r is not None else None
    return look


def gather(scoped, project, as_of, policy_version, extra_params=None):
    """-> (refs, params).  Raises ReproError('INPUT_MISSING') if the policy version is not stored."""
    look = _lookup(scoped)
    refs = {}

    def pin(kind, key):
        if (kind, key) not in refs:
            refs[(kind, key)] = pin_latest(scoped, kind, key)

    pin(P.POLICY_KIND, policy_version)
    for kind in BASE_KINDS + FIN_KINDS:
        for rec in scoped.query(kind):
            p = project_of(kind, rec.payload, look)
            if kind == 'project':
                p = rec.key
            if p is None or p == project:
                pin(kind, rec.key)
                if kind in BASE_KINDS and scoped.get('recon_state', f'{kind}/{rec.key}') is not None:
                    pin('recon_state', f'{kind}/{rec.key}')
    for kind in TENANT_KINDS:
        for rec in scoped.query(kind):
            pin(kind, rec.key)
    params = {'project': project, 'as_of': as_of, 'policy': policy_version, 'pins': {f'{k}/{key}': r.revision for (k, key), r in sorted(refs.items())},
              'approvals_confirmed': PA.confirmations(scoped, sorted(refs))}            # APG-F67: the approvals the audit log confirms, pinned for replay
    params.update(extra_params or {})
    return [refs[k] for k in sorted(refs)], params
