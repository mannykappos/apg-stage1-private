"""Choosing and pinning the stored records a detection run will read.  Blueprint: Section 05 section 13 (immutable input snapshots), Section 06 section 16 (reproducible evidence).

Same discipline as fin/gather.py: the run reads the store ONCE and pins the exact revision and hash of every record it may use.  A project run pins what the financial core
pins (invoices, orders, budgets, variations, forecasts, retention, reconciliation states, the financial policy) plus the project's notices, delay events, hire, timesheets, output
and defects, plus the detection policy.  A tenant run pins supplier compliance evidence, suppliers, quotes and orders (tenant-wide facts that belong to no project) plus the
detection policy.  Like the financial gatherer it lists every record of a kind and filters in memory: fine for Builder Zero, wrong at the size of a real builder (EDR-24)."""
from ..repro import pin_latest
from ..fin import gather as FG
from ..fin.snap import project_of
from . import policy as DP
from .. import policy_approval as PA

PROJECT_DET_KINDS = ('notice', 'delay_event', 'plant_hire', 'timesheet', 'work_output', 'defect')
TENANT_DET_KINDS = ('compliance', 'supplier', 'supplier_quote', 'purchase_order')
RECON_KINDS = ('supplier_quote', 'purchase_order')


def gather_project(scoped, project, as_of, fin_policy_version, det_policy_version, extra=None):
    refs, params = FG.gather(scoped, project, as_of, fin_policy_version, None)
    pins = {(r.kind, r.key): r for r in refs}

    def pin(kind, key):
        if (kind, key) not in pins:
            pins[(kind, key)] = pin_latest(scoped, kind, key)
    pin(DP.POLICY_KIND, det_policy_version)
    for kind in PROJECT_DET_KINDS:
        for rec in scoped.query(kind):
            p = project_of(kind, rec.payload)               # the six kinds carry their own project: no lookup of another record is needed
            if p is None or p == project:
                pin(kind, rec.key)
    params = {'scope': 'project', 'project': project, 'as_of': as_of, 'policy': fin_policy_version, 'det_policy': det_policy_version,
              'pins': {f'{k}/{key}': r.revision for (k, key), r in sorted(pins.items())},
              'approvals_confirmed': PA.confirmations(scoped, sorted(pins))}            # APG-F67
    params.update(extra or {})
    return [pins[k] for k in sorted(pins)], params


def gather_tenant(scoped, as_of, det_policy_version, extra=None):
    pins = {}

    def pin(kind, key):
        if (kind, key) not in pins:
            pins[(kind, key)] = pin_latest(scoped, kind, key)
    pin(DP.POLICY_KIND, det_policy_version)
    for kind in TENANT_DET_KINDS:
        for rec in scoped.query(kind):
            pin(kind, rec.key)
            if kind in RECON_KINDS and scoped.get('recon_state', f'{kind}/{rec.key}') is not None:
                pin('recon_state', f'{kind}/{rec.key}')
    params = {'scope': 'tenant', 'project': None, 'as_of': as_of, 'policy': None, 'det_policy': det_policy_version, 'pins': {f'{k}/{key}': r.revision for (k, key), r in sorted(pins.items())},
              'approvals_confirmed': PA.confirmations(scoped, sorted(pins))}            # APG-F67
    params.update(extra or {})
    return [pins[k] for k in sorted(pins)], params
