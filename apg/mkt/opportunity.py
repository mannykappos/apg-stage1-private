"""Procurement savings opportunities and the savings verification gate.  Blueprint: Section 08 sections 11 (each opportunity needs an approved baseline, a comparable specification and quantity, a
documented calculation, an estimated gross benefit, implementation and other incremental costs, schedule and quality implications, assumptions, uncertainty, approval and implementation status, and the
evidence required to verify the result), 11.1 (a negotiated quote or a lower price on paper is NOT a realised saving: it needs an approved comparable baseline, implementation evidence and authorised
verification of the actual outcome against the baseline including offsetting costs), 2 (benefits must be verified), PG-MP-AC-13, 15; Section 06 section 12.

An opportunity here is always an ESTIMATE.  `status` can only be `estimate`; there is no code path to `realised`.  `claim_saving` refuses, always, because Section 05 verification is not built in this
milestone.  The reference price is the last rate paid for the same project and material: it is NOT an approved baseline and the record says so.  An opportunity is raised only when the quote could be
ranked at all (comparable, or comparable with adjustment), is current, has a complete landed cost, and the reference differs from it ONLY in that the order rate's delivery basis is not recorded."""
from . import common as C, compare as CP, spec as SP
from ..fin import fmath

TOLERATED_REFERENCE_CODES = ('REFERENCE_BASIS_UNRECORDED',)


class SavingNotVerified(Exception):
    pass


def claim_saving(opportunity):
    """Always refuses: an estimate cannot be reported as realised without the Section 05 verification, which this milestone does not build (PG-MP-AC-15)."""
    raise SavingNotVerified('opportunity %s is an estimate; a realised saving needs an approved comparable baseline, implementation evidence and authorised verification (Section 05), none of which exists here'
                            % opportunity.get('id'))


def tax_adjust(mp, a_tax, b_tax, cents):
    """-> (cents in b's treatment, note) or (None, why).  a_tax: treatment of `cents`; b_tax: treatment wanted."""
    if a_tax == b_tax:
        return cents, ''
    g = mp['basis'].get('gst_bps')
    if g is None:
        return None, 'tax treatments differ (%s and %s) and no GST rate is configured' % (a_tax, b_tax)
    if a_tax == 'ex_gst':
        return C.mul_div(cents, 10000 + g, 10000), 'converted from ex_gst to inc_gst at %d basis points' % g
    return C.mul_div(cents, 10000, 10000 + g), 'converted from inc_gst to ex_gst at %d basis points' % g


def verification_requirements():
    return ['an approved comparable baseline (the last rate paid is not one)', 'implementation evidence: an order actually placed at the lower rate (a quote is not a commitment)',
            'authorised verification of the actual outcome against the baseline', 'offsetting costs: storage, waste, handling, freight, financing, switching and qualification',
            'no double counting with schedule or other procurement benefits (Section 08 section 10)']


def discover(ctx, req, cov):
    """-> list of opportunity records for a demand requirement (empty when none)."""
    ref = CP.last_paid(ctx, req)
    if ref is None:
        return []
    mp = ctx.mp
    out = []
    qty = cov.get('uncovered_micro') if cov.get('status') != 'cannot_assess' else None
    for q in CP.candidates(ctx, req):
        o = CP.eval_quote(ctx, q, req, 'quote_ranking', qty if qty else None)
        if o['gate']['class'] not in SP.DEFINITIVE_OK or o['qualification'] != 'current' or not o['landed']['complete'] or o['international'] and o['international']['unresolved_critical']:
            continue
        if any(c not in TOLERATED_REFERENCE_CODES for c in ref['gate']['codes']) or ref['gate']['class'] in ('not_comparable', 'unverified'):
            continue
        quote_unit, note = tax_adjust(mp, o['landed']['tax_treatment'], ref['landed']['tax_treatment'], o['landed']['unit_cents'])
        if quote_unit is None:
            continue
        gap = ref['landed']['unit_cents'] - quote_unit
        if gap <= 0:
            continue
        gap_bps = fmath.bps_of(gap, ref['landed']['unit_cents'])
        if gap_bps < mp['savings']['min_gap_bps']:
            continue
        gross = C.mul_div(gap, qty, C.MICRO) if qty else None
        out.append({'id': 'OPP-%s-%s' % (req['id'].split('/')[1], q['key']), 'requirement': req['id'], 'project': req['project'], 'material': req['material'], 'quote': q['ref'], 'quote_revision': q['rev'],
                    'supplier': q['supplier'], 'reference': ref['offer']['ref'], 'reference_revision': ref['offer']['revision'], 'reference_date': ref['offer']['order_date'],
                    'reference_supplier': ref['offer']['supplier'], 'reference_held_as_duplicate_candidate': ref.get('held_as_duplicate_candidate', False),
                    'unit_gap_cents': gap, 'gap_bps': gap_bps, 'quote_unit_cents': quote_unit, 'reference_unit_cents': ref['landed']['unit_cents'], 'tax_note': note,
                    'quantity_micro': qty or None, 'gross_estimate_cents': gross, 'label': 'indicative', 'status': 'estimate',
                    'baseline': {'basis': 'last rate paid for this project and material', 'approved': False, 'delivery_basis_recorded': False},
                    'comparable': {'quote_class': o['gate']['class'], 'reference_class': ref['gate']['class'], 'reference_codes': ref['gate']['codes']},
                    'incremental_costs': 'unknown: switching, qualification and any change in freight, storage or financing are not in the data',
                    'schedule_and_quality': {'quote_lead_time_days': q['lead'], 'required_date': req['required_date'], 'quality': 'warranty and quality documents are not recorded on the quote'},
                    'assumptions': ['the quote is accepted at the quoted rate', 'the last order rate is a fair reference although its delivery basis is not recorded'],
                    'uncertainty': ['a quote is an offer: validity, stock and lead time are the supplier\'s to confirm'], 'implementation_status': 'not_started', 'approval_status': 'not_approved',
                    'evidence_required_to_verify': verification_requirements(), 'human_approval_required': True,
                    'offer_evaluation': o, 'sources': sorted(set(o['landed']['sources'] + ref['landed']['sources'] + list(req['sources'])), key=lambda s: (s[0], s[1] if s[1] is not None else -1))})
    return out
