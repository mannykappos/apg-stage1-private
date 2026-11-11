"""Actual cost from supplier invoices, net of credits.  Blueprint: Section 03 section 7, Section 05 sections 6 and 7, PG-PC-AC-02, 05, 06, 15, 20; PS-11, PS-12, PS-13, PS-21, PS-22.

Pure function of the pinned snapshot (snap.Facts).  What it does with each stored invoice:
  * a duplicate delivery counts once (the survivor), the repeat is listed as ignored;
  * a credit note is applied only when both it and its invoice are authoritative, and is listed with the invoice it reduced; a credit that is not yet trustworthy holds the
    INVOICE out of the figure (never counted at gross);
  * an invoice dated after the cut-off is outside the period (listed, not an error); a credit dated after the cut-off is not yet applied;
  * a held invoice (pending, quarantined, disputed, unknown value, unresolved link) is listed with its reason and keeps the figure provisional;
  * a record whose project cannot be told is listed on every project's figure as unattributed;
  * a human correction recorded through the M3 review queue is used, and the figure says so.
Cash payments are NEVER read here: cost is not cash (Section 03 section 6.4, no mixed bases)."""
from . import policy as P
from .figure import FigureBuilder

DISPUTE_PREFIX = ('CONFLICT_', 'SECONDARY_DISAGREES', 'SECONDARY_IN_CONFLICT', 'DUPLICATE_CANDIDATE', 'AMBIGUOUS_REVISION')
UNKNOWN_PREFIX = ('MATERIAL_VALUE_UNKNOWN', 'AUTHORITATIVE_VALUE_UNKNOWN', 'CRITICAL_VALUE_MISSING', 'AUTHORITATIVE_SOURCE_ABSENT')
AUTH_OUTCOMES = ('accepted', 'accepted_with_warnings')
NO_CODE = '(no cost code)'
LIMIT_COST = 'cost is supplier invoices excluding GST; labour, plant, accruals, contingency and overhead are not in this figure (CR-02 A5)'


def hold_class(state):
    """Why a record is held, as one exclusion class."""
    codes = [f['code'] for f in state['findings']]
    if any(c.startswith(DISPUTE_PREFIX) for c in codes):
        return 'disputed', codes
    if any(c.startswith(UNKNOWN_PREFIX) for c in codes):
        return 'unknown_value', codes
    return ('quarantined' if state['effective_outcome'] == 'quarantined' else 'held'), codes


def _disposition(state, date, cutoff):
    if state is None:
        return 'held', ['NO_RECONCILIATION_STATE']
    if state['lifecycle'] == 'duplicate_of':
        return 'duplicate_delivery', ['DUPLICATE_OF:' + str(state['duplicate_of'])]
    out = state['effective_outcome']
    if out == 'rejected':
        return 'rejected_by_review', [f['code'] for f in state['findings']]
    if out not in AUTH_OUTCOMES:
        return hold_class(state)
    if state['amount_cents'] is None:
        return 'unknown_value', ['AMOUNT_UNKNOWN']
    if not date:
        return 'unknown_value', ['DATE_UNKNOWN']
    if date > cutoff:
        return 'after_cutoff', ['DATED_AFTER_CUTOFF:' + date]
    return 'counted', []


def invoice_lines(F, project, cutoff):
    """-> (lines, unattributed).  One line per invoice that belongs to the project; `unattributed` = (ref, codes) for records that might."""
    certain, possible = F.of_project('ap_invoice', project)
    cr_certain, cr_possible = F.of_project('credit_note', project)
    lines = {}
    for key in certain:
        base, st = F.get('ap_invoice', key), F.recon('ap_invoice', key)
        fields = base['fields']
        disp, codes = _disposition(st, fields.get('invoice_date'), cutoff)
        lines[key] = {'key': key, 'ref': 'ap_invoice/' + key, 'revision': F.rev('ap_invoice', key), 'cost_code': fields.get('cost_code_ref') or NO_CODE, 'po': fields.get('purchase_order_ref'),
                      'date': fields.get('invoice_date'), 'gross': st['amount_cents'] if st else None, 'disp': disp, 'codes': codes, 'credits': [], 'net': None,
                      'candidate': fields.get('amount_ex_gst_cents'), 'review': (st or {}).get('review'), 'store_revision': (st or {}).get('revision'), 'source_revision': base.get('source_revision')}
    credit_state = {}
    for key in cr_certain:
        st = F.recon('credit_note', key)
        credit_state[key] = st
    applied = set()
    for key, ln in lines.items():
        st = F.recon('ap_invoice', key)
        if ln['disp'] != 'counted':
            continue
        credits = (st.get('lineage') or {}).get('credits', [])
        total = 0
        bad = []
        for c in credits:
            cst = F.recon('credit_note', c)
            cdate = (F.get('credit_note', c) or {}).get('fields', {}).get('credit_date')
            if cst is None or cst['effective_outcome'] not in AUTH_OUTCOMES or cst['amount_cents'] is None or not cdate:
                bad.append(c)
            elif cdate > cutoff:
                ln['credits'].append({'key': c, 'amount': cst['amount_cents'], 'applied': False, 'why': 'after_cutoff'})
            else:
                ln['credits'].append({'key': c, 'amount': cst['amount_cents'], 'applied': True, 'why': ''})
                total += cst['amount_cents']
                applied.add(c)
        if bad:
            ln['disp'], ln['codes'] = 'unresolved_link', ['LINKED_CREDIT_UNRESOLVED:' + ','.join(sorted(bad))]
            ln['credits'] = []
        else:
            ln['net'] = ln['gross'] - total
    orphans = []
    for key in sorted(cr_certain):
        if key in applied:
            continue
        st = credit_state[key]
        inv = (F.get('credit_note', key)['fields'] or {}).get('against_invoice_ref')
        target = lines.get(inv)
        cdate = (F.get('credit_note', key)['fields'] or {}).get('credit_date')
        if target is not None and any(c['key'] == key and c['why'] == 'after_cutoff' for c in target['credits']):
            orphans.append(('credit_note/' + key, 'after_cutoff', ['CREDIT_DATED_AFTER_CUTOFF:' + str(cdate)]))
        elif st is not None and st['effective_outcome'] not in AUTH_OUTCOMES:
            cls, codes = hold_class(st)
            orphans.append(('credit_note/' + key, cls, codes))
        elif target is not None and target['disp'] == 'after_cutoff':
            orphans.append(('credit_note/' + key, 'after_cutoff', ['TARGET_INVOICE_AFTER_CUTOFF:' + inv]))
        else:
            orphans.append(('credit_note/' + key, 'not_counted', ['TARGET_INVOICE_NOT_COUNTED:' + str(inv) + (':' + target['disp'] if target else '')]))
    unattributed = [('ap_invoice/' + k, ['PROJECT_UNKNOWN_OR_AMBIGUOUS']) for k in possible] + [('credit_note/' + k, ['PROJECT_UNKNOWN_OR_AMBIGUOUS']) for k in cr_possible]
    return lines, orphans, unattributed


def build_actual(F, project, cutoff, name='actual_cost', cost_code=None, view='component'):
    """-> figure (dict).  `cost_code` restricts the figure to one cost code (the unallocated bucket is NO_CODE)."""
    pol = F.policy
    b = FigureBuilder(name, view, 'fin.actual_cost', 1, {'project': project, 'cost_code': cost_code}, cutoff, pol)
    if pol is None:
        return b.cannot('POLICY_NOT_PINNED')
    if pol.get('cost_scope') is None:
        return b.cannot('COST_SCOPE_NOT_CONFIGURED', P.OPEN_DECISIONS['cost_scope'])
    b.limit(LIMIT_COST)
    lines, orphans, unattributed = invoice_lines(F, project, cutoff)
    total, by_code, gross_total, credit_total, after = 0, {}, 0, 0, []
    for key in sorted(lines):
        ln = lines[key]
        if cost_code is not None and ln['cost_code'] != cost_code:
            continue
        ref = ln['ref']
        if ln['disp'] == 'counted':
            b.contribute(ref, ln['revision'], ln['gross'], 'invoice', ln['cost_code'])
            total += ln['net']
            gross_total += ln['gross']
            by_code[ln['cost_code']] = by_code.get(ln['cost_code'], 0) + ln['net']
            for c in ln['credits']:
                if c['applied']:
                    b.credit('credit_note/' + c['key'], ref, -c['amount'])
                    b.contribute('credit_note/' + c['key'], F.rev('credit_note', c['key']), -c['amount'], 'credit', ln['cost_code'])
                    credit_total += c['amount']
            if ln['store_revision'] and ln['store_revision'] > 1:
                b.revision(ref, ln['store_revision'], ln['source_revision'])
            if ln['review']:
                b.reason(('HUMAN_CORRECTION_APPLIED:' if ln['review'].get('action') == 'correct' else 'PROMOTED_BY_REVIEW:') + ref)
        else:
            amt = ln['candidate'] if ln['disp'] != 'duplicate_delivery' else None      # the size of what is left out, for the reviewer; it is NOT in the value
            b.exclude(ref, ln['disp'], ln['codes'], amt)
            if ln['disp'] == 'duplicate_delivery':
                b.duplicate(ref, 'ap_invoice/' + str(ln['codes'][0].split(':', 1)[1]))
            if ln['disp'] == 'after_cutoff':
                after.append({'ref': ref, 'amount_cents': ln['gross'], 'date': ln['date'], 'cost_code': ln['cost_code']})
            if ln['disp'] in ('disputed', 'quarantined'):
                b.dispute(ref, ','.join(ln['codes']))
    for ref, cls, codes in orphans:
        if cost_code is None:
            b.exclude(ref, cls, codes)
    for ref, codes in unattributed:
        b.exclude(ref, 'unattributed', codes)
    b.classify('by_cost_code', dict(sorted(by_code.items())))
    b.classify('gross_cents', gross_total)
    b.classify('credits_applied_cents', credit_total)
    b.classify('after_cutoff', sorted(after, key=lambda x: x['ref']))
    b.classify('counted_invoices', sum(1 for l in lines.values() if l['disp'] == 'counted' and (cost_code is None or l['cost_code'] == cost_code)))
    return b.finish(cents=total)
