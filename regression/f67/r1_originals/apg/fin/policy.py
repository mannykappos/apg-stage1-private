"""Calculation policy: every method the locked text leaves open is a CONFIGURATION POINT here, with NO default.  Blueprint: Section 03 section 6.3 ("accounting treatment ... must
be specified before implementation"), Section 05 sections 3 to 6, CR-02 preparation brief items A2 to A13.

A policy is a versioned record.  A version is immutable (a change is a new version).  Each field is None until somebody configures it; a calculation that needs an
unconfigured field returns 'cannot_assess' and names the open decision, it never picks a method itself.  A policy is APPROVED only when a human with the role
'policy_owner', who is not the proposer, has approved it; figures computed under an unapproved policy are at most provisional.

This module does not choose any method, rate, tolerance or threshold.  The values used in the demonstration policy (fin/demo_fin.py) are SYNTHETIC and ILLUSTRATIVE."""
from .. import canon

POLICY_KIND = 'fin_policy'
POLICY_ROLE = 'policy_owner'

# policy field -> the open decision it stands for (CR-02 preparation brief, items A2 to A13; the brief is not approved text)
OPEN_DECISIONS = {
    'recognition_method': 'CR-02 A5 (revenue and progress recognition)',
    'ctc_method': 'CR-02 A3 (cost-to-complete methods)',
    'ffc_basis': 'CR-02 A4 (forecast final cost decomposition)',
    'tax_basis': 'CR-02 A6 (GST and tax treatment)',
    'cost_scope': 'CR-02 A5 (accruals, contingency, overhead, labour and plant)',
    'variation_status_map': 'CR-02 A12 (commercial-state transitions)',
    'po_status_map': 'CR-02 A12 and B2 (purchase order states)',
    'credit_reopens_commitment': 'CR-02 A12 (commercial-state transitions)',
    'carrying': 'CR-02 A7 (carrying-cost eligibility, rate and day-count)',
    'cash_adjustment': 'CR-02 A2 (cash-position-adjusted margin formula)',
    'freshness_days': 'CR-02 A10 (freshness thresholds)',
}
# not None-able: absence means 'exact equality'.  Recorded as interpretation I-17, not as a tolerance.
RECON_TOLERANCE_DECISION = 'CR-02 A13 (reconciliation tolerance)'

RECOGNITION_METHODS = ('cost_to_cost',)
CTC_METHODS = ('declared', 'budget_less_actual', 'declared_else_budget_less_actual')
FFC_BASES = ('actual_to_forecast_date_plus_ctc',)
TAX_BASES = ('ex_gst', 'inc_gst')
COST_CLASSES = ('supplier_invoices',)
VARIATION_CLASSES = ('approved', 'unapproved', 'disputed', 'rejected')
PO_CLASSES = ('committed', 'draft', 'cancelled', 'closed')
FRESHNESS_CLASSES = ('budget', 'forecast', 'facility')
CARRY_ELIGIBILITY = ('as_of_to_release_due_date',)
CARRY_RATE_SOURCES = ('facility', 'declared_proxy')
DAY_COUNTS = (360, 365)
CASH_BASES = ('recognised', 'forecast_final')
CASH_COMPONENTS = ('retention_carrying', 'security_carrying', 'overdue_receivables')


class PolicyError(ValueError):
    pass


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate_policy(p):
    """-> list of problems (empty = well-formed).  Well-formed does not mean approved or complete."""
    bad = []
    if not isinstance(p, dict):
        return ['policy must be a dict']
    allowed = {'version', 'proposer', 'approvals', 'recognition_method', 'ctc_method', 'ffc_basis', 'tax_basis', 'gst_rate_bps', 'cost_scope', 'variation_status_map', 'po_status_map',
               'credit_reopens_commitment', 'reconciliation_tolerance_cents', 'freshness_days', 'carrying', 'cash_adjustment', 'note'}
    for k in p:
        if k not in allowed:
            bad.append('unknown field ' + str(k))
    if not isinstance(p.get('version'), str) or not p.get('version'):
        bad.append('version')
    if not isinstance(p.get('proposer'), str) or not p.get('proposer'):
        bad.append('proposer')
    ap = p.get('approvals', [])
    if not isinstance(ap, list) or not all(isinstance(a, dict) and set(a) == {'approver', 'role', 'kind', 'date'} and all(isinstance(v, str) and v for v in a.values()) for a in ap):
        bad.append('approvals')
    if p.get('recognition_method') not in (None,) + RECOGNITION_METHODS:
        bad.append('recognition_method')
    m = p.get('ctc_method')
    if m is not None:
        if not isinstance(m, dict) or set(m) - {'default', 'by_cost_code'} or m.get('default') not in CTC_METHODS or not isinstance(m.get('by_cost_code', {}), dict) \
                or any(v not in CTC_METHODS for v in m.get('by_cost_code', {}).values()):
            bad.append('ctc_method')
    if p.get('ffc_basis') not in (None,) + FFC_BASES:
        bad.append('ffc_basis')
    if p.get('tax_basis') not in (None,) + TAX_BASES:
        bad.append('tax_basis')
    g = p.get('gst_rate_bps')
    if g is not None and (not _int(g) or g < 0):
        bad.append('gst_rate_bps')
    if p.get('tax_basis') == 'inc_gst' and g is None:
        pass                                                      # allowed: the calculation then says it cannot convert
    cs = p.get('cost_scope')
    if cs is not None and (not isinstance(cs, list) or not cs or any(c not in COST_CLASSES for c in cs) or len(set(cs)) != len(cs)):
        bad.append('cost_scope')
    for fld, classes in (('variation_status_map', VARIATION_CLASSES), ('po_status_map', PO_CLASSES)):
        mp = p.get(fld)
        if mp is not None and (not isinstance(mp, dict) or not mp or any(not isinstance(k, str) or not k or v not in classes for k, v in mp.items())):
            bad.append(fld)
    cr = p.get('credit_reopens_commitment')
    if cr is not None and not isinstance(cr, bool):
        bad.append('credit_reopens_commitment')
    t = p.get('reconciliation_tolerance_cents')
    if t is not None and (not _int(t) or t < 0):
        bad.append('reconciliation_tolerance_cents')
    fr = p.get('freshness_days', {})
    if not isinstance(fr, dict) or any(k not in FRESHNESS_CLASSES or not _int(v) or v < 0 for k, v in fr.items()):
        bad.append('freshness_days')
    c = p.get('carrying')
    if c is not None:
        if not isinstance(c, dict) or set(c) - {'eligibility', 'rate_source', 'proxy_rate_bps', 'day_count_basis', 'overlap', 'funded_share_bps'} or c.get('eligibility') not in CARRY_ELIGIBILITY \
                or not _int(c.get('funded_share_bps')) or not 0 <= c['funded_share_bps'] <= 10000 \
                or c.get('rate_source') not in CARRY_RATE_SOURCES or c.get('day_count_basis') not in DAY_COUNTS or c.get('overlap') not in (None, 'cost_scope_excludes_financing_costs') \
                or (c.get('rate_source') == 'declared_proxy' and not (_int(c.get('proxy_rate_bps')) and c['proxy_rate_bps'] >= 0)) \
                or (c.get('rate_source') == 'facility' and c.get('proxy_rate_bps') is not None):
            bad.append('carrying')
    ca = p.get('cash_adjustment')
    if ca is not None and (not isinstance(ca, dict) or set(ca) != {'base', 'components'} or ca['base'] not in CASH_BASES or not isinstance(ca['components'], list) or not ca['components']
                           or any(x not in CASH_COMPONENTS for x in ca['components']) or len(set(ca['components'])) != len(ca['components'])):
        bad.append('cash_adjustment')
    return bad


def new_policy(version, proposer, **fields):
    p = {'version': version, 'proposer': proposer, 'approvals': []}
    p.update(fields)
    bad = validate_policy(p)
    if bad:
        raise PolicyError('; '.join(bad))
    return canon.deep_copy(p)


def is_approved(p):
    """Approved = a human 'policy_owner', not the proposer, approved this exact version."""
    return any(a['kind'] == 'human' and a['role'] == POLICY_ROLE and a['approver'] != p['proposer'] for a in p.get('approvals', []))


def view(p):
    """The policy as calculations see it: a copy plus the derived flag `_approved`."""
    q = canon.deep_copy(p)
    q['_approved'] = is_approved(p)
    return q


def missing(p, needed):
    """-> list of (field, decision text) for each needed field that is not configured."""
    out = []
    for f in needed:
        v = p.get(f)
        if v is None or (f == 'freshness_days' and not v):
            out.append((f, OPEN_DECISIONS[f]))
    return out


def store_policy(scoped, p):
    """A policy version's CONTENT is immutable.  The only change allowed under an existing version is appending approvals (each approval is a new stored revision, so a figure
    that pinned the earlier revision keeps showing the policy as unapproved).  Any other change must be a new version string."""
    bad = validate_policy(p)
    if bad:
        raise PolicyError('; '.join(bad))
    cur = scoped.get(POLICY_KIND, p['version'])
    if cur is not None:
        old = cur.payload
        if {k: v for k, v in old.items() if k != 'approvals'} != {k: v for k, v in p.items() if k != 'approvals'} or p['approvals'][:len(old['approvals'])] != old['approvals']:
            raise PolicyError(f'policy version {p["version"]} already exists with different content; a change is a new version')
    return scoped.put(POLICY_KIND, p['version'], p, expected_revision=0 if cur is None else cur.revision)


def approve(p, approver, role, kind, date):
    """-> a new policy dict carrying one more approval (the caller stores it under the same version: only approvals may be appended)."""
    q = canon.deep_copy(p)
    q['approvals'] = list(q.get('approvals', [])) + [{'approver': approver, 'role': role, 'kind': kind, 'date': date}]
    return q
