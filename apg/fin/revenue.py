"""Contract revenue and its classes.  Blueprint: Section 03 section 6.1 ("these states must not be collapsed into one revenue field"), Section 05 PG-PC-AC-09 (unapproved or
disputed revenue is not silently treated as secured), section 6.4 (no mixed tax bases); CR-02 A6, A12, A13.

  secured revenue = original contract value + APPROVED variations that have a value
  separate classes: variations that are submitted-but-unapproved, disputed, rejected, and approved-but-unpriced.  They are reported next to the figure, never inside it.
Which variation status means 'approved' is the policy's variation_status_map (CR-02 A12) - there is no built-in meaning.  An unmapped or missing status keeps the variation
out and makes the figure provisional.  The contract file also carries a summary 'approved variations' number: if it disagrees with the variation register (beyond the
configured tolerance, or exactly when none is configured) BOTH are shown as disputed and the figure is provisional; the register is used for the value because it is line-level.
Tax: costs are ex GST.  Revenue is used as is only when the policy says contract values are ex GST; if it says inc GST the policy must also carry a GST rate and the
conversion is exact integer arithmetic; with no tax basis configured there is no figure (mixing bases is refused)."""
from . import policy as P
from .figure import FigureBuilder
from .fmath import round_div
from .intake import usable


def _tolerance(pol):
    t = pol.get('reconciliation_tolerance_cents')
    return 0 if t is None else t                    # no tolerance configured = exact equality is required (interpretation I-17)


def build_revenue(F, project, as_of):
    pol = F.policy
    b = FigureBuilder('secured_revenue', 'component', 'fin.revenue', 1, {'project': project}, as_of, pol)
    if pol is None:
        return b.cannot('POLICY_NOT_PINNED')
    for fld in ('tax_basis', 'variation_status_map'):
        if pol.get(fld) is None:
            return b.cannot(fld.upper() + '_NOT_CONFIGURED', P.OPEN_DECISIONS[fld])
    if pol['tax_basis'] == 'inc_gst' and pol.get('gst_rate_bps') is None:
        return b.cannot('GST_RATE_NOT_CONFIGURED', P.OPEN_DECISIONS['tax_basis'])
    con = F.get('contract', project)
    if con is None:
        b.unknown('contract/' + project, 'no_data')
        return b.finish()
    cref = 'contract/' + project
    if not usable(con):
        b.exclude(cref, 'disputed' if con.get('conflict') else 'held', [f for f in (con.get('intrinsic') or {}).get('pending', [])] or ['CONFLICT_SAME_KEY'])
        if con.get('conflict'):
            b.dispute(cref, 'several different versions of the contract record')
        return b.finish()
    cf = con['fields']
    original = cf['original_contract_cents']
    b.contribute(cref, F.rev('contract', project), original, 'original_contract')
    proj = F.get('project', project)
    if proj is not None and usable(proj) and proj['fields'].get('contract_value_cents') is not None and abs(proj['fields']['contract_value_cents'] - original) > _tolerance(pol):
        b.dispute('project/' + project, f"project master contract value {proj['fields']['contract_value_cents']} differs from the contract record {original}")
        b.dispute(cref, 'differs from the project master contract value')
    approved, classes = 0, {'approved': 0, 'unapproved': 0, 'disputed': 0, 'rejected': 0}
    refs = {'approved': [], 'unapproved': [], 'disputed': [], 'rejected': [], 'approved_unpriced': [], 'unmapped': []}
    certain, possible = F.of_project('variation', project)
    for key in certain:
        v, ref = F.get('variation', key), 'variation/' + key
        if not usable(v):
            b.exclude(ref, 'disputed' if v.get('conflict') else 'held', ['CONFLICT_SAME_KEY'] if v.get('conflict') else v['intrinsic']['pending'])
            if v.get('conflict'):
                b.dispute(ref, 'several different versions of the variation')
            continue
        fl = v['fields']
        if fl.get('raised_date') and fl['raised_date'] > as_of:
            b.exclude(ref, 'after_cutoff', ['RAISED_AFTER_AS_OF'])
            continue
        status = fl.get('source_status')
        cls = pol['variation_status_map'].get(status)
        if cls is None:
            b.exclude(ref, 'unknown_value', ['VARIATION_STATUS_UNMAPPED:' + str(status)], fl.get('value_cents'))
            b.unknown(ref + ' status ' + str(status), 'unmapped', P.OPEN_DECISIONS['variation_status_map'])
            refs['unmapped'].append(key)
            continue
        val = fl.get('value_cents')
        if cls == 'approved':
            if val is None:
                refs['approved_unpriced'].append(key)
                b.unknown(ref + ' value', 'no_data')          # an approved variation with no value: revenue is not fully known
            else:
                approved += val
                classes['approved'] += val
                refs['approved'].append(key)
                b.contribute(ref, F.rev('variation', key), val, 'approved_variation')
        else:
            refs[cls].append(key)
            if val is not None:
                classes[cls] += val
            if cls == 'disputed':
                b.dispute(ref, 'variation is disputed')
    for k in possible:
        b.exclude('variation/' + k, 'unattributed', ['PROJECT_UNKNOWN_OR_AMBIGUOUS'])
    summary = cf.get('approved_variations_cents')
    if summary is not None and abs(summary - approved) > _tolerance(pol):
        b.dispute(cref, f'contract summary of approved variations ({summary}) differs from the variation register ({approved})')
        b.dispute('variation/*', f'variation register approved total ({approved}) differs from the contract summary ({summary})')
        b.reason('CONTRACT_SUMMARY_DISAGREES_WITH_REGISTER')
    elif summary is None:
        b.unknown(cref + ' approved_variations_cents', 'no_data')
    secured = original + approved
    if pol['tax_basis'] == 'inc_gst':
        secured = round_div(secured * 10000, 10000 + pol['gst_rate_bps'])
        b.reason('CONVERTED_FROM_INC_GST_AT_POLICY_RATE')
    b.classify('original_contract_cents', original)
    b.classify('approved_variations_cents', approved)
    b.classify('variation_classes_cents', classes)
    b.classify('variation_refs', {k: sorted(v) for k, v in refs.items()})
    b.classify('contract_summary_approved_variations_cents', summary)
    b.classify('tax_basis', pol['tax_basis'])
    b.limit('unapproved, disputed and rejected variations, claims and revenue at risk are NOT in secured revenue; they are listed in classified.variation_classes_cents')
    return b.finish(cents=secured)
