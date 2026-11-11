"""Portfolio view of findings.  Blueprint: Section 06 sections 7 (never combine the financial categories into one number), 9 (do not sum overlapping exposures), 13 (portfolio intelligence
respects tenant boundaries), PG-AI-AC-10, 16, 17.

`aggregate` takes the findings of ONE tenant (the caller reads them through a tenant-scoped store, so another tenant's findings can never be in the list; a finding naming a different
tenant would have been refused at write time).  It returns, for each financial interpretation SEPARATELY, a lower bound (the largest amount in each overlap component, added across
components) and an upper bound (the plain sum), and says whether the two differ.  It never returns one number for several interpretations, never counts an unquantified finding as zero
(they are listed), never includes dismissed or superseded findings, and never describes an estimate or an exposure as realised."""
from . import findings as FD, relations as R

LABEL_ORDER = ('figure', 'record', 'estimate')


def _money(c):
    return '%s%d.%02d' % ('-' if c < 0 else '', abs(c) // 100, abs(c) % 100)


def _range_display(lower, upper, n_quant, n_unquant):
    """M6 correction of the M5 review issue 1: when nothing is quantified the headline says so; it never prints a range of zero for exposure that is merely unquantified."""
    if n_quant == 0:
        return 'no quantified amount available (%d finding(s) have no defensible amount; this is not zero exposure)' % n_unquant
    rng = _money(lower) if lower == upper else '%s to %s' % (_money(lower), _money(upper))
    return rng + ('; %d further finding(s) are unquantified and not included' % n_unquant if n_unquant else '')


def aggregate(findings, project=None):
    live = [f for f in findings if f['status'] not in R.EXCLUDED_STATUSES]
    if project is not None:
        live = [f for f in live if f['scope'].get('project') == project]
    comp = R.components(live)
    out, unq = {}, []
    for interp in FD.FINANCIAL:
        members = [f for f in live if f['signal']['interpretation'] == interp]
        quant = [f for f in members if f['signal']['quantification']['status'] == 'quantified']
        unq.extend({'finding_id': f['finding_id'], 'interpretation': interp, 'why': f['signal']['quantification']['reason']} for f in members if f['signal']['quantification']['status'] != 'quantified')
        if not members:
            continue
        per = {}
        for f in quant:
            per.setdefault(comp[f['finding_id']], []).append(f['signal']['quantification']['gross_cents'])
        lower = sum(max(v) for v in per.values())
        upper = sum(sum(v) for v in per.values())
        labels = sorted({f['signal']['quantification']['label'] for f in quant}, key=LABEL_ORDER.index)
        out[interp] = {'findings': len(members), 'quantified': len(quant), 'unquantified': len(members) - len(quant), 'components': len(per), 'lower_bound_cents': lower, 'upper_bound_cents': upper, 'overlap_adjusted': lower != upper,
                       'quantified_amount_available': bool(quant),
                       'range_display': _range_display(lower, upper, len(quant), len(members) - len(quant)),
                       'amount_labels': labels, 'note': 'a range, not a total: amounts inside one overlap component may include each other' if lower != upper else
                       'no overlapping amounts found among the quantified findings; still a sum of separate estimates and records, not a verified figure'}
    return {'by_interpretation': out, 'unquantified': sorted(unq, key=lambda u: u['finding_id']),
            'excluded': sorted(f['finding_id'] for f in findings if f['status'] in R.EXCLUDED_STATUSES),
            'not_reported': ['interpretations are never added together', 'no amount here is a verified realised saving (Section 05 verification is not built)',
                             'data-integrity, compliance and operational findings carry no financial amount here']}


def portfolio_view(scoped, project=None):
    return aggregate(FD.all_findings(scoped), project)
