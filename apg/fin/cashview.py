"""Retention and security position, carrying cost, and the cash-position-adjusted margin.  Blueprint: Section 12 sections 4, 7, 8, 9; Section 05 section 5.3 and 12; Section 03
sections 4.1, 5.3; PG-PC-AC-01, 10, 11; CR-02 A2, A7, A9.

  position        face values only.  Retention withheld and security-instrument face value are SEPARATE figures and neither is a cost, a loss or cash.  A forecast release
                  date or an expiry date passing raises a REVIEW flag; it never moves money and never asserts entitlement.
  carrying cost   funded share of the balance x annual rate x eligible days / day-count basis (Section 12 section 7), rounded once.  The funded share is a policy value
                  (CR-02 A7): the face value is never assumed to have been financed in full.  The eligible days run from the as-of date to the expected release date (a
                  FORWARD cost); days already past are not costed because no balance history is ingested.  The rate is the facility's stated rate, or a policy-declared
                  PROXY, which makes the figure provisional and says so.  Overlap with other financing costs must be attested by the policy, otherwise the figure is
                  provisional with the overlap check listed as unknown.
  cash-adjusted   a distinct management view: a base margin (recognised or forecast, by policy) less the listed cash-position costs.  The component list is the policy's
                  (CR-02 A2).  It is never an accounting margin and says so.  A listed component that cannot be assessed makes the whole figure unassessable (a component that
                  has been defined as part of the formula is not optional)."""
from . import cash_states as CS, policy as P
from .figure import FigureBuilder
from .fmath import carrying_cents, days_between, round_div
from .intake import usable
from .margins import build_recognised
from .forecast import build_forecast

LIMIT_VIEW = 'management view connecting margin with cash-position costs; NOT a statutory or accounting margin (Section 05 section 5.3)'


def _ledger(F, project):
    p = F.get('retention', project)
    return p


def build_retention(F, project, as_of):
    pol = F.policy
    b = FigureBuilder('retention_position', 'cash_position', 'fin.cash_position', 1, {'project': project}, as_of, pol)
    if pol is None:
        return b.cannot('POLICY_NOT_PINNED')
    led = F.get('retention', project)
    ref = 'retention/' + project
    if led is None:
        b.unknown(ref, 'no_data')
        return b.finish()
    if not usable(led):
        b.exclude(ref, 'disputed' if led.get('conflict') else 'unknown_value', ['CONFLICT_SAME_KEY'] if led.get('conflict') else led['intrinsic']['pending'])
        if led.get('conflict'):
            b.dispute(ref, 'several different versions of the retention ledger record')
        return b.finish()
    fl = led['fields']
    bank = {'bank_txn/' + k: v['fields'] for k, v in F.kind('bank_txn').items() if usable(v)}
    events = CS.events_of(F, project)
    pools, problems = CS.fold(fl, events, bank)
    if problems:
        b.dispute('retention_event/' + project, 'event sequence breaks a rule at seq %d: %s' % (problems[0]['seq'], problems[0]['code']))
        b.reason('RETENTION_EVENTS_INCONSISTENT')
    b.contribute(ref, F.rev('retention', project), fl['retention_held_cents'], 'retention_ledger')
    for e in events:
        k = '%s|%04d' % (project, e['seq'])
        b.contribute('retention_event/' + k, F.rev('retention_event', k), e['amount_cents'], 'event:%s>%s' % (e['from_state'], e['to_state']))
    due, rel = fl.get('release_due_date'), fl.get('released_date')
    flags = []
    if due is None:
        b.unknown(ref + ' release_due_date', 'no_data')
    elif due <= as_of and pools['withheld'] > 0:
        flags.append('RELEASE_REVIEW_DUE')                          # the due date has passed with money still withheld: a review prompt, NOT an entitlement
        b.reason('RELEASE_REVIEW_DUE: due %s, not released; entitlement is not asserted' % due)
    if fl.get('hold_reason_text'):
        flags.append('HELD_WITH_REASON')
    if rel and any(p for p in ('released',) if pools[p]):
        flags.append('RELEASED_PER_LEDGER_CASH_RECEIPT_NOT_EVIDENCED' if not pools['received'] else 'RELEASED_AND_RECEIVED')
    cls = {k: v for k, v in pools.items()}
    b.classify('pools_cents', cls)
    b.classify('release_due_date', due)
    b.classify('flags', flags)
    newest = fl.get('release_due_date')
    b.limit('retention is face value only: it is not available cash, not a loss and not a financing cost; pools show money only where an evidenced event or the ledger put it')
    return b.finish(cents=pools['withheld'])


def build_security(F, project, as_of):
    pol = F.policy
    b = FigureBuilder('security_face_value', 'cash_position', 'fin.cash_position', 1, {'project': project}, as_of, pol)
    if pol is None:
        return b.cannot('POLICY_NOT_PINNED')
    certain, possible = F.of_project('security', project)
    total, items, flags = 0, [], []
    for key in certain:
        p, ref = F.get('security', key), 'security/' + key
        if not usable(p):
            b.exclude(ref, 'disputed' if p.get('conflict') else 'unknown_value', ['CONFLICT_SAME_KEY'] if p.get('conflict') else p['intrinsic']['pending'])
            continue
        fl = p['fields']
        exp = fl.get('expiry_date')
        review = bool(exp and exp <= as_of)
        if exp is None:
            b.unknown(ref + ' expiry_date', 'no_data')
        if review:
            flags.append('EXPIRY_REVIEW:' + key)
        total += fl['face_value_cents']
        b.contribute(ref, F.rev('security', key), fl['face_value_cents'], 'instrument_face_value')
        items.append({'instrument': key, 'kind': fl.get('kind_text'), 'face_value_cents': fl['face_value_cents'], 'expiry_date': exp, 'review': review})
    for k in possible:
        b.exclude('security/' + k, 'unattributed', ['PROJECT_UNKNOWN_OR_AMBIGUOUS'])
    b.classify('instruments', items)
    b.classify('flags', flags)
    b.limit('a security instrument is not cash, not retention and not a cost; face value is not collateral or margin and is not a financing cost (Section 12 section 9)')
    if not certain:
        b.unknown('security instruments for ' + project, 'no_data')
        return b.finish()
    if not items:
        return b.finish()                                   # every instrument is held: the total is unknown, not zero
    return b.finish(cents=total)


def facility_rate(F, as_of):
    """-> (rate_bps, ref, statement_date, problem).  Exactly one usable facility statement is needed; several is ambiguous (nothing chooses for you)."""
    usable_f = [(k, v) for k, v in sorted(F.kind('facility').items()) if usable(v)]
    held = [k for k, v in sorted(F.kind('facility').items()) if not usable(v)]
    if held:
        return None, None, None, 'FACILITY_RECORD_HELD:' + ','.join(held)
    if not usable_f:
        return None, None, None, 'NO_FACILITY_STATEMENT'
    if len(usable_f) > 1:
        return None, None, None, 'SEVERAL_FACILITIES:' + ','.join(k for k, _ in usable_f)
    k, v = usable_f[0]
    if v['fields']['statement_date'] > as_of:
        return None, None, None, 'FACILITY_STATEMENT_AFTER_AS_OF'
    return v['fields']['rate_bps'], 'facility/' + k, v['fields']['statement_date'], None


def build_carrying(F, project, as_of, what='retention'):
    pol = F.policy
    b = FigureBuilder(what + '_carrying_cost', 'cash_position', 'fin.cash_position', 1, {'project': project}, as_of, pol)
    if pol is None:
        return b.cannot('POLICY_NOT_PINNED')
    if pol.get('carrying') is None:
        return b.cannot('CARRYING_NOT_CONFIGURED', P.OPEN_DECISIONS['carrying'])
    car = pol['carrying']
    if what == 'security':
        return b.cannot('NO_CASH_MARGIN_EVIDENCE: instrument face value is not collateral; no cash margin or fee data is ingested')
    pos = build_retention(F, project, as_of)
    b.child('retention_position', pos)
    if pos['value']['cents'] is None:
        return b.cannot('RETENTION_POSITION_CANNOT_BE_ASSESSED')
    due = pos['classified'].get('release_due_date')
    if due is None:
        return b.cannot('NO_EXPECTED_RELEASE_DATE')
    balance = pos['value']['cents']
    if balance > 0 and due <= as_of:
        return b.cannot('EXPECTED_RELEASE_DATE_PASSED_AND_NOT_RELEASED: the date passing does not show when the money will be released, so a forward cost cannot be estimated')
    days = max(days_between(as_of, due), 0)
    funded = round_div(balance * car['funded_share_bps'], 10000)
    if car['rate_source'] == 'facility':
        rate, rref, sdate, problem = facility_rate(F, as_of)
        if problem:
            return b.cannot(problem)
        fresh = (pol.get('freshness_days') or {}).get('facility')
        if fresh is None:
            b.unknown('facility statement freshness', 'method_not_configured', P.OPEN_DECISIONS['freshness_days'])
        elif days_between(sdate, as_of) > fresh:
            b.unknown('facility statement is %d days old, beyond the %d configured' % (days_between(sdate, as_of), fresh), 'stale')
        b.contribute(rref, F.rev('facility', rref.split('/', 1)[1]), rate, 'facility_rate_bps')
    else:
        rate, rref = car['proxy_rate_bps'], 'policy:proxy_rate'
        b.reason('RATE_IS_A_POLICY_PROXY_NOT_AN_EVIDENCED_FACILITY_RATE')
        b.unknown('evidenced facility rate', 'not_obtained')
    if car.get('overlap') is None:
        b.unknown('overlap with other financing costs', 'method_not_configured', P.OPEN_DECISIONS['carrying'])
    cost = carrying_cents(funded, rate, days, car['day_count_basis'])
    b.classify('inputs', {'balance_cents': balance, 'funded_share_bps': car['funded_share_bps'], 'funded_balance_cents': funded, 'rate_bps': rate, 'rate_source': rref, 'eligible_days': days,
                          'from': as_of, 'to': due, 'day_count_basis': car['day_count_basis'], 'eligibility': car['eligibility']})
    b.limit('forward cost from the as-of date to the expected release date; cost already incurred before the as-of date is not estimated (no balance history is ingested)')
    b.limit('retention face value is shown in retention_position and is NOT this figure')
    return b.finish(cents=cost)


def build_overdue_receivables(F, project, as_of):
    b = FigureBuilder('overdue_receivables_cost', 'cash_position', 'fin.cash_position', 1, {'project': project}, as_of, F.policy)
    return b.cannot('NO_RECEIVABLES_DATA: client invoices, certificates and receipts are not ingested (data gap O-1 / M4 limitation)')


COMPONENTS = {'retention_carrying': lambda F, p, a: build_carrying(F, p, a, 'retention'), 'security_carrying': lambda F, p, a: build_carrying(F, p, a, 'security'),
              'overdue_receivables': build_overdue_receivables}


def build_cash_adjusted(F, project, as_of):
    pol = F.policy
    b = FigureBuilder('cash_position_adjusted_margin', 'cash_adjusted', 'fin.cash_adjusted', 1, {'project': project}, as_of, pol)
    if pol is None:
        return b.cannot('POLICY_NOT_PINNED')
    if pol.get('cash_adjustment') is None:
        return b.cannot('CASH_ADJUSTMENT_NOT_CONFIGURED', P.OPEN_DECISIONS['cash_adjustment'])
    ca = pol['cash_adjustment']
    base = (build_recognised if ca['base'] == 'recognised' else build_forecast)(F, project, as_of)
    b.child('base_margin_' + ca['base'], base)
    total, ok = 0, base['value']['cents'] is not None
    for name in ca['components']:
        c = COMPONENTS[name](F, project, as_of)
        b.child(name, c)
        if c['value']['cents'] is None:
            ok = False
        else:
            total += c['value']['cents']
    b.classify('base', ca['base'])
    b.classify('components', list(ca['components']))
    b.limit(LIMIT_VIEW)
    if not ok:
        return b.cannot('A_DEFINED_COMPONENT_CANNOT_BE_ASSESSED')
    b.classify('cash_costs_cents', total)
    return b.finish(cents=base['value']['cents'] - total)
