"""International sourcing safeguards.  Blueprint: Section 08 section 12 (flag import restrictions and product requirements, standards and certification, customs classification and duty assumptions,
supplier and payment identity, shipping and insurance terms, warranty and returns, quality inspection, traceability, trade restrictions and delivery uncertainty; the system must NOT declare a product
legally compliant or a supplier cleared for import; unresolved critical checks block a definitive recommendation), PG-MP-AC-11, 12.

The checks a policy lists are RECORDS a person enters (kind import_check, one row per quote and check).  A check is resolved only when it says resolved AND names a person and an evidence reference
AND is dated; not-applicable needs a person too.  Anything else - no record, a held record, a status the system does not know, a 'resolved' with no evidence - is UNRESOLVED.  This module never
sets a check to resolved and never concludes compliance: it reports what a person has and has not recorded."""
from . import common as C
from .policy import CHECK_STATUSES


def checks(F, mp, q):
    names, critical = mp['international']['checks'], set(mp['international']['critical_checks'])
    recs, held = {}, []
    for key in C.keys_of(F, 'import_check'):
        v = C.simple_view(F, 'import_check', key, ('quote_ref', 'check_name', 'status_text'))
        if v is None or not C.names_quote(F, 'import_check', key, q['key']):
            continue
        if not v['ok']:
            held.append({'ref': v['ref'], 'why': v['why']})
            continue
        recs[v['f']['check_name']] = v
    rows, unresolved, unres_crit = [], [], []
    for n in names:
        v = recs.get(n)
        if v is None:
            status, why, ref, rev, by = 'unresolved', 'no record of this check', None, None, None
        else:
            f = v['f']
            st = (f['status_text'] or '').strip().lower()
            by, ev, on = f.get('checked_by'), f.get('evidence_ref'), f.get('checked_on')
            if st not in CHECK_STATUSES:
                status, why = 'unresolved', 'status %r is not one of %s' % (f['status_text'], '/'.join(CHECK_STATUSES))
            elif st == 'unresolved':
                status, why = 'unresolved', 'recorded as unresolved'
            elif not by or not on or (st == 'resolved' and not ev):
                status, why = 'unresolved', 'recorded as %s without %s' % (st, 'a person, a date and an evidence reference' if st == 'resolved' else 'a person and a date')
            else:
                status, why = st, ''
            ref, rev = v['ref'], v['rev']
        rows.append({'check': n, 'critical': n in critical, 'status': status, 'why': why, 'ref': ref, 'revision': rev, 'checked_by': by})
        if status == 'unresolved':
            unresolved.append(n)
            if n in critical:
                unres_crit.append(n)
    extra = sorted(c for c in critical if c not in names)
    return {'checks': rows, 'unresolved': unresolved, 'unresolved_critical': sorted(set(unres_crit) | set(extra)), 'held': held, 'unlisted_critical': extra,
            'note': 'APG records what a person has entered; it does not decide that a product is compliant or a supplier cleared for import'}
