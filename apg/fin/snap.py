"""The snapshot a calculation reads, and the rule that decides which stored records belong to which project.  Blueprint: Section 05 section 13 (immutable input snapshots),
Section 04 sections 7 and 9 (held records stay visible).

`Facts` wraps the pinned inputs and parameters of one calculation and offers read-only access.  A calculation never reads anything else: no store, no clock, no global.

`project_of` is the ONE place that decides which project a stored record belongs to.  The gatherer (calc_records.gather) and the calculations both use it, so a record
can never be pinned for one reason and counted for another.  A record whose project cannot be told (a conflict marker whose contenders name different projects, a record
with no project) is `None` = UNATTRIBUTED: it is shown on EVERY project's figures as something that might belong there, never silently dropped.  (The M3 `invoice_cost_view`
with a project filter silently skipped conflict markers; that is finding F-14, and this module is the M4 answer to it.)"""
from .. import canon
from .. import policy_approval as PA
from . import policy as P

PROJECT_FIELD = 'project_ref'
BASE_KINDS = ('ap_invoice', 'credit_note', 'purchase_order', 'po_amendment', 'budget_line')
FIN_KINDS = ('project', 'contract', 'variation', 'ctc_line', 'retention', 'security', 'retention_event')
TENANT_KINDS = ('facility', 'bank_txn')                  # not owned by one project


def split_ref(ref):
    kind, _, key = ref.partition('/')
    return kind, key


def _fields_of(payload):
    """-> list of field dicts to look at: the record's own, or every contender's for a conflict marker."""
    if payload.get('conflict'):
        return [c['fields'] for c in payload['conflict']['contenders']]
    if 'fields' not in payload:
        return [payload]                                   # a flat record written by the platform itself (a retention event), not by ingestion
    return [payload['fields']]


def project_of(kind, payload, lookup=None):
    """-> project id, or None when it cannot be told.  `lookup(kind, key)` returns a stored payload (needed for credit notes and PO amendments, which carry no project)."""
    if kind == 'credit_note':
        links = {f.get('against_invoice_ref') for f in _fields_of(payload)}
        target_kind = 'ap_invoice'
    elif kind == 'po_amendment':
        links = {f.get('purchase_order_ref') for f in _fields_of(payload)}
        target_kind = 'purchase_order'
    else:
        projs = {f.get(PROJECT_FIELD) for f in _fields_of(payload)}
        return next(iter(projs)) if len(projs) == 1 and None not in projs else None
    if len(links) != 1 or None in links or lookup is None:
        return None
    target = lookup(target_kind, next(iter(links)))
    return None if target is None else project_of(target_kind, target, lookup)


class Facts:
    """Read-only view of a calculation's pinned inputs (`inputs`: 'kind/key' -> payload) and parameters."""
    def __init__(self, inputs, params):
        self._by = {}
        for ref, payload in inputs.items():
            kind, key = split_ref(ref)
            self._by.setdefault(kind, {})[key] = payload
        self.params = canon.deep_copy(params)
        self.as_of = params.get('as_of')
        self.project = params.get('project')
        self.pins = params.get('pins', {})
        pol = self._by.get(P.POLICY_KIND, {}).get(params.get('policy'))
        self.policy = P.view(pol, PA.pinned(params, P.POLICY_KIND, params.get('policy'))) if pol is not None else None      # APG-F67: only approvals the run confirmed

    def kind(self, kind):
        return self._by.get(kind, {})

    def get(self, kind, key):
        return self._by.get(kind, {}).get(key)

    def recon(self, kind, key):
        return self._by.get('recon_state', {}).get(f'{kind}/{key}')

    def rev(self, kind, key):
        return self.pins.get(f'{kind}/{key}')

    def lookup(self, kind, key):
        return self.get(kind, key)

    def of_project(self, kind, project=None):
        """-> (certain, possible): keys of `kind` that belong to the project, and keys that MIGHT (project unknown or contenders disagree).  Both sorted."""
        project = project or self.project
        certain, possible = [], []
        for key in sorted(self.kind(kind)):
            p = project_of(kind, self.kind(kind)[key], self.lookup)
            if p == project:
                certain.append(key)
            elif p is None:
                possible.append(key)
        return certain, possible
