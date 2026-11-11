"""Choosing and pinning the stored records an M6 procurement run will read.  Blueprint: Section 05 section 13 (immutable input snapshots), Section 08 section 14 (every market-dependent finding keeps its
sources and dates), Section 06 section 13 (portfolio intelligence respects boundaries).

Same discipline as the financial and detection gatherers: the store is read ONCE and the exact revision of every record the run may use is pinned.

PROJECT run  pins the project's purchase orders (and any whose project cannot be told), their deliveries, the project's material demand and specification requirements, and the tenant-wide reference
             records no project owns (quotes with their readings, tiers, terms, assumptions and import checks; the material master; FX rates; market observations).  It sees no other project's order.
TENANT run   pins every purchase order of the tenant (a boundary can only be detected by looking), all deliveries, demand and requirements, and the same reference records.  Which projects the
             result may SHOW is the `authorised_projects` parameter: it is part of the pinned parameters, so a different authorised set is a different, separately reproducible run.

Like the other gatherers this lists every record of a kind and filters in memory: fine for Builder Zero, wrong at the size of a real builder (EDR-24)."""
from ..repro import pin_latest
from ..fin.snap import project_of
from ..fin import policy as FP
from . import policy as MP
from .. import policy_approval as PA

REFERENCE_KINDS = ('supplier_quote', 'quote_reading', 'quote_tier', 'quote_term', 'landed_assumption', 'import_check', 'material', 'fx_rate', 'market_observation', 'supplier')
RECON_KINDS = ('supplier_quote', 'purchase_order')
PROJECT_OWNED = ('material_demand', 'spec_requirement')


def _look(scoped):
    def look(kind, key):
        r = scoped.get(kind, key)
        return r.payload if r is not None else None
    return look


def _gather(scoped, project, as_of, fin_policy_version, det_policy_version, mkt_policy_version, mkt_spec_version, authorised):
    look = _look(scoped)
    pins = {}

    def pin(kind, key):
        if (kind, key) not in pins:
            pins[(kind, key)] = pin_latest(scoped, kind, key)
    pin(FP.POLICY_KIND, fin_policy_version)
    pin(MP.POLICY_KIND, mkt_policy_version)
    if mkt_spec_version:
        pin(MP.SPEC_KIND, mkt_spec_version)
    if det_policy_version:
        from ..det import policy as DP
        pin(DP.POLICY_KIND, det_policy_version)
    po_keys = set()
    for rec in scoped.query('purchase_order'):
        p = project_of('purchase_order', rec.payload, look)
        if project is None or p is None or p == project:
            pin('purchase_order', rec.key)
            po_keys.add(rec.key)
            if scoped.get('recon_state', 'purchase_order/%s' % rec.key) is not None:
                pin('recon_state', 'purchase_order/%s' % rec.key)
    for rec in scoped.query('delivery'):
        po = (rec.payload.get('fields') or {}).get('purchase_order_ref') if not rec.payload.get('conflict') else None
        if project is None or po is None or po in po_keys:
            pin('delivery', rec.key)
    for kind in PROJECT_OWNED:
        for rec in scoped.query(kind):
            p = project_of(kind, rec.payload, look)
            if project is None or p is None or p == project:
                pin(kind, rec.key)
    for kind in REFERENCE_KINDS:
        for rec in scoped.query(kind):
            pin(kind, rec.key)
            if kind in RECON_KINDS and scoped.get('recon_state', '%s/%s' % (kind, rec.key)) is not None:
                pin('recon_state', '%s/%s' % (kind, rec.key))
    params = {'scope': 'project' if project else 'tenant', 'project': project, 'as_of': as_of, 'policy': fin_policy_version, 'det_policy': det_policy_version,
              'mkt_policy': mkt_policy_version, 'mkt_spec': mkt_spec_version, 'authorised_projects': sorted(authorised) if authorised is not None else None,
              'pins': {'%s/%s' % (k, key): r.revision for (k, key), r in sorted(pins.items())},
              'approvals_confirmed': PA.confirmations(scoped, sorted(pins))}            # APG-F67
    return [pins[k] for k in sorted(pins)], params


def gather_project(scoped, project, as_of, fin_policy_version, det_policy_version, mkt_policy_version, mkt_spec_version):
    return _gather(scoped, project, as_of, fin_policy_version, det_policy_version, mkt_policy_version, mkt_spec_version, {project})


def gather_tenant(scoped, as_of, fin_policy_version, det_policy_version, mkt_policy_version, mkt_spec_version, authorised_projects):
    return _gather(scoped, None, as_of, fin_policy_version, det_policy_version, mkt_policy_version, mkt_spec_version, set(authorised_projects))
