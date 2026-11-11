"""A corpus of deliberately faulty or borderline procurement inputs (M6 test input; Blueprint Section 08; RFC-01 test list: missing data, conflicting quotes, duplicate records, currency errors,
changed prices, delivery changes, misleading recommendations).  Deterministic.  Synthetic.  Each case builds a small hand-made world through the real M3-M6 intake paths, runs the real
comparison / scenario / detection code and states what the result MUST say.  A case never says "no error": it names the ranking status, the offers that must be excluded and why, the
rules that must be raised or silent, and the runs that must say they did not run.

It runs against the Builder's reference pipeline (the helpers in tests/helpers_mkt.py).  Unlike the M5 corpus it is NOT yet written against a storage-neutral world interface: running it
against the Engine's own storage is Engine-integration work (handoff register).

Expectation keys (all optional):
  rank   {'status','definitive','order':[offer refs, best first],'excluded':{ref: class},'may': bool,'why_has': text,'decision','qty','label':{ref: label}}
  rules  {'raised':[rule ids],'silent':[rule ids],'run':{rule: status}}   (a project run for PRJ-001 at the as-of day)
  fn     callable(m) -> None, raising AssertionError on a failure   (for checks the keys cannot say)"""
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from .test_mkt_compare import cq, cread, rank
from .test_mkt_rules import conc, steel as rsteel, with_quotes, S_
from apg.mkt import compare as CP, demand as DEM, demo_mkt as DM, opportunity as OPP, scenarios as SC

AS_OF_ = '2026-09-30'
CONC_DEM = demand('DEM-1', 'PRJ-001', 'MAT-CONC40', '100', 'm3', '2026-12-01')
STEEL_DEM = demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '40', 'tonne', '2026-12-01')
A, B, C_ = 'supplier_quote/Q-A', 'supplier_quote/Q-B', 'supplier_quote/Q-C'


def two(a=None, b=None, readings=('Q-A', 'Q-B'), dem=True, **kw):
    qa, ra = conc('Q-A', **(a or {}))
    qb, rb = conc('Q-B', **dict({'sup': 'SUP-002', 'rate': '33000'}, **(b or {})))
    m = with_quotes((qa, ra if 'Q-A' in readings else []), (qb, rb if 'Q-B' in readings else []), dem=[CONC_DEM] if dem else None, **kw)
    return m


def one(**kw):
    q, r = conc('Q-A', **kw)
    return with_quotes((q, r), dem=[CONC_DEM])


def intl(rate='6900', fx='0.6612', fxd='2026-09-20', ref='0.6540', ref_date='2026-09-30', cur='USD', basis='FOB', freight='800', lead='56', issue='2026-09-10', valid='2026-12-31', dom=True, resolve=False):
    """A steel demand, a domestic delivered steel quote (Q-B) and an international FOB steel quote (Q-A)."""
    qa = quote('Q-A', 'SUP-004', 'MAT-STEEL', 's', issue, valid, rate, cur, fx, fxd, freight, basis, lead)
    qb = rsteel('Q-B', rate='265000', sup='SUP-001')
    m = mkt_world()
    m.quote_rows(qa, *( [qb[0]] if dom else []))
    m.readings(*std_readings('Q-A', 'tonne', 'alice'), *(qb[1] if dom else []))
    if ref:
        m.fx(*(ref if isinstance(ref, list) else [fxrow(ref_date, ref)]))
    m.demands(STEEL_DEM)
    if resolve:
        m.assumptions(['Q-A', 'insurance', '150', '', cur, 'allowance', 'none', 'alice', '2026-09-20'], ['Q-A', 'duty', '', '500', '', 'rate', 'ref', 'alice', '2026-09-20'],
                      ['Q-A', 'clearance', '30000', '', 'AUD', 'allowance', 'none', 'alice', '2026-09-20'], ['Q-A', 'handling', '12000', '', 'AUD', 'allowance', 'none', 'alice', '2026-09-20'])
        m.checks(*[['Q-A', c, 'resolved', 'EV-1', 'alice', '2026-09-21'] for c in ('customs_classification', 'duty_rate_confirmed', 'import_permit')])
    return m


def steel_world(*quotes, qty='40', required='2026-12-01', **kw):
    m = mkt_world(**kw)
    m.quote_rows(*quotes)
    m.readings(*[r for q in quotes for r in std_readings(q[0])])
    m.demands(demand('DEM-1', 'PRJ-001', 'MAT-STEEL', qty, 'tonne', required))
    return m


def sq(qid='Q-1', rate='265000', valid='2026-12-31', lead='21', sup='SUP-001', basis='delivered', freight='0', issue='2026-09-10'):
    return quote(qid, sup, 'MAT-STEEL', 's', issue, valid, rate, 'AUD', '', '', freight, basis, lead)


def scn(m, as_of=AS_OF_):
    ctx = m.ctx(as_of=as_of)
    (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand']
    return SC.build(ctx, req, DEM.coverage(ctx, req)), ctx, req


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


CASES = []


def case(cid, desc, build, **expect):
    CASES.append(dict(id=cid, desc=desc, build=build, expect=expect))


# ---------------------------------------------------------------- A: comparability, ranking and missing data
case('A01', 'control: two comparable, current, complete offers give a definitive ranking, cheapest first', lambda: two(),
     rank=dict(status='definitive', definitive=True, order=[B, A], may=True))
case('A02', 'one offer is never a ranking', lambda: one(), rank=dict(status='insufficient_offers', definitive=False, may=False, why_has='fewer than two'))
case('A03', 'no quote at all is no offers', lambda: with_quotes(dem=[CONC_DEM]), rank=dict(status='no_offers', definitive=False, may=False))
case('A04', 'a quote with no readings at all is not a verified like-for-like offer, so nothing is definitive', lambda: two(readings=('Q-A',)),
     rank=dict(definitive=False, may=False))
case('A05', 'readings verified by the person who extracted them do not count as verified', lambda: _self_verified(), rank=dict(definitive=False, may=False))
case('A06', 'a cheaper offer at a lower verified strength is excluded and explained, and wins nothing', lambda: two(b={'strength': '32', 'rate': '27000'}),
     rank=dict(excluded={B: 'not_comparable'}, order=[A], definitive=False, may=False))
case('A07', 'the same, with a third comparable offer: the ranking stays definitive and the excluded offer stays visible', lambda: _three_one_wrong(),
     rank=dict(status='definitive', definitive=True, order=[C_, A], excluded={B: 'not_comparable'}, may=True))
case('A08', 'a cheaper offer for a different material is excluded', lambda: two(b={'mat': 'MAT-CONC32', 'strength': '32', 'rate': '27000'}),
     rank=dict(excluded={B: 'not_comparable'}, definitive=False))
case('A09', 'a verified unit that differs from the demanded unit excludes the offer', lambda: _unit_wrong(), rank=dict(definitive=False, may=False))
case('A10', 'an ex-works offer with no stated freight is not a complete landed cost, so no definitive ranking', lambda: _exw(freight=''),
     rank=dict(definitive=False, may=False))
case('A11', 'an ex-works offer whose headline rate is lower but whose landed cost is higher does not rank first', lambda: _exw(freight='2500', rate='33000'),
     rank=dict(order=[A, B], definitive=True, may=True))
case('A12', 'a cheaper delivered offer ranks first on landed cost and the ex-works offer is second', lambda: _exw(freight='500', rate='33000'),
     rank=dict(order=[B, A], definitive=True))
case('A13', 'a missing procurement-policy parameter stops the ranking and says which one', lambda: _drop('freshness.quote_ranking'),
     fn=lambda m: _missing(lambda: rank(m), 'freshness'))
case('A14', 'a missing benchmark-freshness parameter makes the staleness rule say it could not run, rather than pass', lambda: _drop('freshness.benchmark'),
     rules=dict(run={'MP01': 'not_configured'}))
case('A15', 'no demand: the uncovered-demand rule is silent and no ranking is made for a demand that does not exist', lambda: with_quotes(conc('Q-A'), conc('Q-B', sup='SUP-002')),
     rules=dict(silent=['MP03']), fn=lambda m: need(not [r for r in CP.requirements(m.ctx()) if r['kind'] == 'demand'], 'a demand appeared'))
case('A16', 'a quote with a blank unit rate is held at intake and is not an offer', lambda: two(a={'rate': ''}),
     rank=dict(definitive=False, may=False))
case('A17', 'a quote with a negative unit rate is held and is not an offer', lambda: two(a={'rate': '-100'}), rank=dict(definitive=False, may=False))
case('A18', 'a quote with a zero unit rate is not an offer', lambda: two(a={'rate': '0'}), rank=dict(definitive=False, may=False))

# ---------------------------------------------------------------- B: conflicting and duplicate records
case('B01', 'two different verified readings of one attribute block the offer', lambda: _conflicting_readings(), rank=dict(definitive=False, may=False))
case('B02', 'a quote re-delivered under the same id with a different rate is held: neither version is used, nothing is overwritten silently, and it is reported', lambda: _revised(),
     rank=dict(definitive=False, may=False), rules=dict(raised=['MPD1:supplier_quote|held_records']))
case('B03', 'an exact repeat of a quote row is one offer, not two', lambda: _repeat_quote(), rank=dict(status='insufficient_offers', definitive=False))
case('B04', 'two quotes from the same supplier are not two independent offers for a definitive ranking', lambda: _same_supplier(), fn=lambda m: _same_supplier_check(m))
case('B05', 'identical orders on the same day are reported as a possible duplicate', lambda: _dup_orders(), rules=dict(raised=['MP05']))
case('B06', 'a demand delivered twice with different quantities is a conflict: reported, and not used', lambda: _conflicting_demand(),
     rules=dict(raised=['MPD1']))
case('B07', 'two different FX rates for one date leave the conversion unresolved, so the foreign offer is not definitive', lambda: _fx_conflict(),
     fn=lambda m: _landed_incomplete(m))
case('B09', 'orders that differ in any one detail are not a possible duplicate', lambda: _differ(), rules=dict(silent=['MP05']))
case('B08', 'a zero tier price is held, reported as held and never used', lambda: _zero_tier(), rules=dict(raised=['MPD1']))

case('B10', 'clean inputs keep the held-input rule silent', lambda: two(), rules=dict(silent=['MPD1']))

# ---------------------------------------------------------------- C: currency, tax and unit errors
case('C01', 'a foreign quote with no stated and no reference rate cannot be converted: landed incomplete, not definitive', lambda: intl(fx='', fxd='', ref=None, resolve=True),
     fn=lambda m: _landed_incomplete(m))
case('C02', 'a stated rate with no reference rate is reported as having nothing to check against, never guessed', lambda: intl(ref=None, fxd='2026-09-20'),
     rules=dict(raised=['MP06']))
case('C03', 'a recent stated rate that diverges beyond the tolerance from the reference is flagged', lambda: intl(fx='0.7000', fxd='2026-09-28'), rules=dict(raised=['MP06']))
case('C04', 'a recent stated rate inside the tolerance is silent', lambda: intl(fx='0.6540', fxd='2026-09-28'), rules=dict(silent=['MP06']))
case('C05', 'an inverted rate (AUD per USD instead of USD per AUD) is flagged as diverging', lambda: intl(fx='1.5291', fxd='2026-09-28'), rules=dict(raised=['MP06']))
case('C06', 'a zero stated exchange rate is reported and does not alter the conversion, which uses the reference rate', lambda: intl(fx='0', fxd='2026-09-20', resolve=True),
     rules=dict(raised=['MP06']), fn=lambda m: _conversion_unchanged(m))
case('C07', 'a negative stated exchange rate is reported and does not alter the conversion, which uses the reference rate', lambda: intl(fx='-0.66', fxd='2026-09-20', resolve=True),
     rules=dict(raised=['MP06']), fn=lambda m: _conversion_unchanged(m))
case('C08', 'a currency code the programme does not know is not converted', lambda: intl(cur='XXX', resolve=True), fn=lambda m: _landed_incomplete(m, hold=True))
case('C09', 'a reference rate older than the limit leaves the foreign offer qualified, the ranking indicative and the age stated', lambda: intl(ref_date='2026-08-01', resolve=True),
     rank=dict(status='indicative', definitive=False, may=False, why_has='FRESHNESS'), fn=lambda m: _fx_stale(m))
case('C10', 'an international offer with unresolved critical checks is never definitive', lambda: intl(), rank=dict(definitive=False, may=False), rules=dict(raised=['MP07']))
case('C11', 'resolving every critical check, with a person, a date and evidence, clears the check rule', lambda: intl(resolve=True), rules=dict(silent=['MP07']))
case('C12', 'a rate stated in the foreign currency is kept as stated: the converted figure never overwrites it', lambda: intl(resolve=True),
     fn=lambda m: _stated_kept(m))
case('C13', 'a foreign quote past its validity is not flagged as a live risk', lambda: intl(valid='2026-09-01'), rules=dict(silent=['MP06', 'MP07']))
case('C14', 'an old stated rate is flagged even when it is close to the reference', lambda: intl(fx='0.6540', fxd='2026-05-02'), rules=dict(raised=['MP06']))

# ---------------------------------------------------------------- D: changed prices and freshness
case('D01', 'a quote exactly at the age limit is current; one day older is stale and cannot make a definitive ranking', lambda: two(a={'issue': '2026-08-16'}),
     rank=dict(definitive=True, may=True))
case('D02', 'one day past the age limit the quote is stale: still an offer, not definitive-eligible', lambda: two(a={'issue': '2026-08-15'}),
     rank=dict(definitive=False, may=False))
case('D03', 'a quote past its validity date is historical only and is not offered', lambda: two(a={'valid': '2026-09-29', 'issue': '2026-09-01'}), rank=dict(definitive=False, may=False))
case('D04', 'a quote issued after the as-of day is not yet knowable and is not offered', lambda: two(a={'issue': '2026-10-05'}, b={}), rank=dict(definitive=False, may=False))
case('D05', 'a stale price index is flagged with its age', lambda: _index('2026-07-01'), rules=dict(raised=['MP01:MAT-STEEL|index']))
case('D06', 'a price index exactly at the limit is fresh', lambda: _index('2026-08-16'), rules=dict(silent=['MP01:MAT-STEEL|index']))
case('D07', 'no index observation at all is unavailable, never fresh', lambda: _index(None), rules=dict(raised=['MP01:MAT-STEEL|index']))
case('D08', 'a comparable current quote cheaper than the last paid rate is an estimate for the quantity not yet ordered', lambda: _opp(), rules=dict(raised=['MP09']))
case('D09', 'a quote dearer than the last paid rate is silent', lambda: _opp(quote_rate='1900'), rules=dict(silent=['MP09']))
case('D10', 'a cheaper partially comparable quote is not the baseline for the comparability warning (Defect B regression)', lambda: _partial_baseline(), fn=lambda m: _partial_baseline_check(m))
case('D11', 'a cheaper non-comparable quote is flagged as a comparability warning, never as a saving', lambda: two(b={'strength': '32', 'rate': '27000'}),
     rules=dict(raised=['MP02']))
case('D12', 'a dearer non-comparable quote is silent', lambda: two(b={'strength': '32', 'rate': '41000'}), rules=dict(silent=['MP02']))

# ---------------------------------------------------------------- E: delivery, lead time and quantity changes
case('E01', 'a lead time that cannot meet the required date is shown on the scenario and not hidden', lambda: steel_world(sq(lead='90'), required='2026-11-15'),
     fn=lambda m: _late(m))
case('E02', 'a lead time that just meets the required date is shown as meeting it', lambda: steel_world(sq(lead='45'), required='2026-11-14'),
     fn=lambda m: _just_in_time(m))
case('E03', 'a required date earlier than today leaves no decision window and says so', lambda: steel_world(sq(), required='2026-09-20'), fn=lambda m: _past_required(m))
case('E04', 'demand with offers lapsing inside the decision window is flagged with the earliest comparable date', lambda: _lapsing(), rules=dict(raised=['MP03']))
case('E05', 'demand whose decision date is beyond the window is silent', lambda: _lapsing(v1='2026-12-31', v2='2026-12-31'), rules=dict(silent=['MP03']))
case('E06', 'orders above the demand by more than the tolerance are an estimated surplus', lambda: _orders(qty_ordered='120'), rules=dict(raised=['MP04']))
case('E07', 'orders within the surplus tolerance are silent', lambda: _orders(qty_ordered='104'), rules=dict(silent=['MP04']))
case('E08', 'orders in a different unit from the demand cannot be assessed and say so', lambda: _orders(unit='m3'), fn=lambda m: _unit_cannot(m))
case('E09', 'orders for another project do not cover this demand', lambda: _orders(project='PRJ-002'), fn=lambda m: need(DEM.coverage(m.ctx(), _req(m))['status'] in ('uncovered',), 'another project covered this demand: %r' % (DEM.coverage(m.ctx(), _req(m)),)))
case('E10', 'short-accepted dockets over a sufficient sample are an observation about the supplier, not a ranking', lambda: _dockets(), rules=dict(raised=['MP08']))
case('E11', 'a small docket sample is not assessed rather than reported as good or bad', lambda: _dockets(n=2), rules=dict(silent=['MP08']))
case('E12', 'a zero-quantity demand produces no purchase scenario and no division by zero', lambda: steel_world(sq(), qty='0'), fn=lambda m: _zero_qty(m))
case('E13', 'a very large quantity and rate stay exact integers', lambda: steel_world(sq(rate='900000000'), qty='999999'), fn=lambda m: _big(m))

# ---------------------------------------------------------------- F: misleading recommendations
case('F01', 'scenarios never choose between themselves or between offers', lambda: steel_world(sq(), sq('Q-2', rate='260000', sup='SUP-002')), fn=lambda m: _no_choice(m))
case('F02', 'a wait scenario whose quote lapses before the order date is flagged as an evidence gap, not priced as available', lambda: steel_world(sq(valid='2026-10-31')),
     fn=lambda m: _wait_lapses(m))
case('F03', 'a saving is never claimed realised: claim_saving always refuses', lambda: _opp(), fn=lambda m: _claim(m))
case('F04', 'every ranking requires a human approval, whatever its status', lambda: two(), fn=lambda m: need(rank(m)[0]['human_approval_required'] is True, 'approval flag'))
case('F05', 'a portfolio comparison is silent when the authorised projects do not cover every project that bought the material', lambda: _pf(),
     fn=lambda m: _portfolio_silent(m))
case('F06', 'a portfolio comparison needs every buying project authorised and then is a weak estimate', lambda: _pf(),
     fn=lambda m: _portfolio_reports(m))
case('F11', 'two authorised projects paying different average rates give a weak, labelled portfolio estimate', lambda: _pf(), rules=dict(raised=['MP10'], authorised=('PRJ-001', 'PRJ-002')))
case('F07', 'a wait path that is not in the policy is never invented', lambda: steel_world(sq()), fn=lambda m: _paths_only_policy(m))
case('F08', 'an unapproved procurement policy does not run the rules', lambda: _unapproved(), fn=lambda m: _unapproved_check(m))
case('F09', 'a tenant run that is authorised for no project reports nothing about any project', lambda: two(), fn=lambda m: _no_projects(m))
case('F10', 'the same inputs give the same run key and the same signals', lambda: two(), fn=lambda m: _repro(m))


# ---------------------------------------------------------------- builders and checks used above (kept below the case table so the table reads first)
def _req(m):
    (req,) = [r for r in CP.requirements(m.ctx()) if r['kind'] == 'demand']
    return req


def _self_verified():
    qa, ra = conc('Q-A')
    qb, _ = conc('Q-B', sup='SUP-002', rate='33000')
    rb = [reading('Q-B', 'strength_mpa', '40', verified_by='extractor'), reading('Q-B', 'unit', 'm3', verified_by='extractor')]
    return with_quotes((qa, ra), (qb, rb), dem=[CONC_DEM])


def _three_one_wrong():
    return with_quotes(conc('Q-A'), conc('Q-B', strength='32', rate='27000', sup='SUP-002'), conc('Q-C', sup='SUP-003', rate='33000'), dem=[CONC_DEM])


def _unit_wrong():
    qa, ra = conc('Q-A')
    qb, _ = conc('Q-B', sup='SUP-002', rate='33000')
    rb = [reading('Q-B', 'strength_mpa', '40', verified_by='alice'), reading('Q-B', 'unit', 'tonne', verified_by='alice')]
    return with_quotes((qa, ra), (qb, rb), dem=[CONC_DEM])


def _exw(freight, rate='33000'):
    qa, ra = conc('Q-A')
    qb = quote('Q-B', 'SUP-002', 'MAT-CONC40', 's', '2026-09-10', '2026-12-31', rate, 'AUD', '', '', freight, 'ex-works', '7')
    return with_quotes((qa, ra), (qb, cread('Q-B')), dem=[CONC_DEM])


def _drop(path):
    m = two()
    m.drop(path)
    return m


def _missing(fn, text):
    from apg.mkt import common as MC
    try:
        fn()
    except MC.MissingParam as e:
        need(text in str(e), 'the missing parameter was not named: %s' % (e,))
        return
    raise AssertionError('a missing parameter did not stop the calculation')


def _conflicting_readings():
    m = two(readings=('Q-A',))
    m.readings(reading('Q-B', 'strength_mpa', '40', verified_by='alice'), reading('Q-B', 'strength_mpa', '32', verified_by='alice'), reading('Q-B', 'unit', 'm3', verified_by='alice'))
    return m


def _revised():
    m = two()
    m.quote_rows(quote('Q-B', 'SUP-002', 'MAT-CONC40', 's', '2026-09-10', '2026-12-31', '35000', 'AUD', '', '', '0', 'delivered', '7'))
    return m


def _repeat_quote():
    m = one()
    q, _ = conc('Q-A')
    m.quote_rows(q)
    return m


def _same_supplier():
    return with_quotes(conc('Q-A', sup='SUP-001'), conc('Q-B', sup='SUP-001', rate='33000'), dem=[CONC_DEM])


def _same_supplier_check(m):
    r, _, _ = rank(m)
    sup = {o['offer']['supplier'] for o in r['offers']}
    need(sup == {'SUP-001'}, 'expected a single supplier behind both offers: %r' % (sup,))
    need(r['status'] != 'definitive' or any('one supplier' in n for n in r.get('notes', [])), 'a ranking from one supplier alone was called definitive without saying so')
    r2, _, _ = rank(two())
    need('notes' not in r2, 'a two-supplier ranking carries the one-supplier note')


def _dup_orders():
    m = mkt_world()
    m.orders(pom('PO-1', qty='10', rate='100000', date='2026-08-25'), pom('PO-2', qty='10', rate='100000', date='2026-08-25'))
    return m


def _conflicting_demand():
    m = mkt_world()
    m.demands(demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '5', 'tonne', '2026-12-01'), demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '7', 'tonne', '2026-12-01'))
    return m


def _differ():
    m = mkt_world()
    m.orders(pom('PO-1', qty='10', rate='100000', date='2026-08-25'), pom('PO-2', qty='10', rate='100001', date='2026-08-25'))
    return m


def _zero_tier():
    m = with_quotes(rsteel('Q-1'))
    m.tiers(['Q-1', '100', '0'])
    return m


def _fx_conflict():
    return intl(ref=[fxrow('2026-09-30', '0.6540'), fxrow('2026-09-30', '0.6600')], resolve=True)


def _landed_of(m, key='Q-A'):
    from apg.mkt import landed as LD
    a = m.analysis()
    return LD.unit_landed(a.F, a.mp, a.ctx.quotes[key], AS_OF_, None)


def _landed_incomplete(m, hold=False):
    if hold and 'Q-A' not in m.ctx().quotes:                         # the quote itself was held at intake: it is not an offer at all
        return
    u = _landed_of(m)
    need(u['complete'] is False and u['missing'], 'the landed cost was called complete although the conversion could not be made: %r' % ({k: u[k] for k in ('complete', 'missing', 'unit_cents')},))
    r, _, _ = rank(m)
    need(not r['definitive'] and not CP.may_recommend(r)[0], 'an unconvertible offer allowed a definitive ranking')


def _fx_stale(m):
    r, _, _ = rank(m)
    (qa,) = [o for o in r['offers'] if o['offer']['key'] == 'Q-A']
    f = [x for x in qa['freshness'] if x['class'] == 'fx']
    need(f and f[0]['state'] == 'stale' and f[0]['age_days'] == 60, 'the stale reference rate was not stated with its age: %r' % (f,))
    need(any('60 days old' in x for x in qa['limitations']), 'the limitation does not state the age')


def _conversion_unchanged(m):
    base = _landed_of(intl(resolve=True))
    now = _landed_of(m)
    need(now['unit_cents'] == base['unit_cents'] and now['complete'] and now['conversion']['rate_micro'] == base['conversion']['rate_micro'], 'a bad stated rate changed the conversion: %r vs %r' % (now['conversion'], base['conversion']))


def _stated_kept(m):
    u = _landed_of(m)
    cv = u['conversion']
    need(cv['from_currency'] == 'USD' and cv['from_minor'] == 6900 and cv['rate_source_ref'], 'the stated amount was lost: %r' % (cv,))
    q = m.ctx().quotes['Q-A']
    need(q['rate'] == 6900 if 'rate' in q else True, 'the stated rate was overwritten')


def _index(date):
    m = mkt_world()
    if date:
        m.observations(obs('OBS-1', 'MAT-STEEL', date))
    return m


def _opp(quote_rate='1740', last='1850', ordered='1300'):
    m = mkt_world()
    m.quote_rows(quote('Q-6', 'SUP-001', 'MAT-PBOARD', 's', '2026-09-08', '2026-11-15', quote_rate, 'AUD', '', '', '0', 'delivered', '7'))
    m.readings(reading('Q-6', 'thickness_mm', '13'), reading('Q-6', 'unit', 'sheet'))
    m.demands(demand('DEM-1', 'PRJ-001', 'MAT-PBOARD', '2000', 'sheet', '2026-12-01'))
    m.orders(pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty=ordered, rate=last, date='2026-08-25'))
    return m


def _partial_baseline():
    return with_quotes(conc('Q-A'), conc('Q-P', sup='SUP-002', rate='31000', verified=False), conc('Q-N', sup='SUP-003', strength='32', rate='32000'), dem=[CONC_DEM])


def _partial_baseline_check(m):
    got = [x for x in S_(m.mres(), 'MP02')]
    subs = sorted(x['taxonomy']['subtype'] for x in got)
    need('cheaper_quote_not_comparable' in subs, 'the not-comparable cheaper quote was hidden by the partially comparable one: %r' % (subs,))
    need(all(x['extra']['baseline_unit_cents'] == 34000 for x in got), 'the baseline was not the cheapest like-for-like offer')


def _lapsing(v1='2026-10-27', v2='2026-11-30'):
    return with_quotes(rsteel('Q-1', valid=v1), rsteel('Q-2', sup='SUP-002', rate='101000', valid=v2), dem=[demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '100', 'tonne', '2026-12-01')])


def _orders(qty_ordered='120', unit='tonne', project='PRJ-001'):
    return with_quotes(dem=[demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '100', 'tonne', '2026-12-01')], orders=[pom('PO-1', qty=qty_ordered, rate='100000', date='2026-08-25', unit=unit, project=project)])


def _unit_cannot(m):
    cov = DEM.coverage(m.ctx(), _req(m))
    need(cov['status'] == 'cannot_assess' and 'UNIT_MISMATCH' in cov['why'], 'a unit mismatch was not reported: %r' % (cov,))
    r = m.mres()
    need(not S_(r, 'MP04') and r['rule_runs']['MP04']['not_assessed'], 'the over-order rule did not say it could not assess')


def _dockets(n=3):
    m = mkt_world()
    m.orders(*[pom('PO-%d' % i, 'SUP-001', 'PRJ-001', 'MAT-STEEL', '10', '100000', '2026-08-0%d' % i) for i in range(1, n + 1)])
    m.dockets(*[docket('DK-%d' % i, 'PO-%d' % i, date='2026-08-%02d' % (i * 3 + 1), delivered='10', accepted='9') for i in range(1, n + 1)])
    return m


def _late(m):
    s, _, _ = scn(m)
    (b,) = [x for x in s['scenarios'] if x['scenario'] == 'buy_now']
    need(b['schedule']['meets_required_date'] is False and b['schedule']['days_before_required'] == -44, 'a late delivery was not shown as late: %r' % (b['schedule'],))
    (w,) = [x for x in s['scenarios'] if x['scenario'] == 'wait']
    need(w['status'] == 'not_available' and 'before the as-of day' in w['why'], 'waiting was offered although the latest order date has passed: %r' % (w,))


def _just_in_time(m):
    s, _, _ = scn(m)
    (b,) = [x for x in s['scenarios'] if x['scenario'] == 'buy_now']
    need(b['schedule']['meets_required_date'] is True and b['schedule']['days_before_required'] == 0, 'a delivery on the required day was not shown as meeting it: %r' % (b['schedule'],))


def _past_required(m):
    s, _, _ = scn(m)
    (b,) = [x for x in s['scenarios'] if x['scenario'] == 'buy_now']
    need(b['schedule']['meets_required_date'] is False and b['schedule']['days_before_required'] < 0, 'a required date in the past was not shown as missed')
    (w,) = [x for x in s['scenarios'] if x['scenario'] == 'wait']
    need(w['status'] == 'not_available', 'waiting was offered for a date already past')


def _zero_qty(m):
    need(not [r for r in CP.requirements(m.ctx()) if r['kind'] == 'demand'], 'a zero-quantity demand became a purchase requirement')
    r = m.mres()
    need(r['counts']['rules'] >= 1 and not S_(r, 'MP03') and not S_(r, 'MP04'), 'a zero-quantity demand produced a purchase signal')


def _big(m):
    s, _, _ = scn(m)
    (b,) = [x for x in s['scenarios'] if x['scenario'] == 'buy_now']
    need(b['landed_total_cents'] == 999999 * 900_000_000 and type(b['total_cost_cents']) is int and type(b['landed_total_cents']) is int, 'large amounts are not exact integers: %r' % (b['landed_total_cents'],))


def _no_choice(m):
    import json
    s, _, _ = scn(m)
    need(not ({'recommended', 'selected', 'chosen', 'winner', 'best'} & set(s)), 'the scenario set names a choice: %r' % (sorted(s),))
    for x in s['scenarios']:
        need(not ({'recommended', 'selected', 'chosen', 'winner', 'best'} & set(x)) and x['human_approval_required'] is True and x['changes_authoritative_forecast'] is False, 'scenario %s names a choice or changes the forecast' % x['scenario'])
    need(s['human_approval_required'] is True and s['changes_authoritative_forecast'] is False, 'the scenario set lost its approval flag')
    text = json.dumps(s).lower()
    for w in ('we recommend', 'recommended scenario', 'best option', 'you should buy'):
        need(w not in text, 'wording: ' + w)


def _wait_lapses(m):
    s, _, _ = scn(m)
    waits = [x for x in s['scenarios'] if x['scenario'].startswith('wait:')]
    need(len(waits) == 3, 'expected the three configured price paths')
    for w in waits:
        need(w['status'] == 'scenario_only' and any('lapses on 2026-10-31' in g and 'modelled value, not an offer' in g for g in w['evidence_gaps']), 'a wait scenario priced a lapsed quote as available: %r' % (w['evidence_gaps'],))


def _claim(m):
    opps = m.analysis().opportunities()
    need(len(opps) == 1, 'expected one opportunity')
    o = opps[0]
    need((o['status'], o['implementation_status'], o['approval_status'], o['human_approval_required']) == ('estimate', 'not_started', 'not_approved', True), 'an opportunity is not an unapproved estimate: %r' % (o['status'],))
    try:
        OPP.claim_saving(o)
    except OPP.SavingNotVerified:
        return
    raise AssertionError('a saving was claimed')


def _pf():
    m = mkt_world()
    m.orders(pom('PO-1', 'SUP-001', 'PRJ-001', 'MAT-PBOARD', '10', '100', '2026-08-01', unit='sheet'), pom('PO-2', 'SUP-002', 'PRJ-002', 'MAT-PBOARD', '20', '120', '2026-08-02', unit='sheet'))
    return m


def _portfolio_silent(m):
    import json
    r = m.mtres(authorised=('PRJ-001',))
    need(not sigs(r, 'MP10') and 'PORTFOLIO_BOUNDARY_APPLIED' in r['rule_runs']['MP10']['notes'], 'the portfolio rule reported although not every buying project was authorised')
    text = json.dumps(r['signals'])
    need('PRJ-002' not in text and 'PO-2' not in text, 'a signal named a project the caller is not authorised for')


def _portfolio_reports(m):
    (x,) = sigs(m.mtres(authorised=('PRJ-001', 'PRJ-002')), 'MP10')
    need((x['quantification']['label'], x['confidence']['evidence_strength']) == ('estimate', 'weak'), 'the portfolio gap is not a weak estimate')


def _paths_only_policy(m):
    s, _, _ = scn(m)
    names = sorted(x['scenario'] for x in s['scenarios'] if x['scenario'].startswith('wait:'))
    need(names == ['wait:down_5pct', 'wait:flat', 'wait:up_5pct'], 'wait scenarios are not exactly the configured paths: %r' % (names,))
    m2 = steel_world(sq())
    m2.set_mkt(scenarios=dict(DM.demo_mkt_fields()['scenarios'], price_paths=[{'name': 'flat', 'change_bps': 0, 'horizon_days': 30}]))
    s2, _, _ = scn(m2)
    need(sorted(x['scenario'] for x in s2['scenarios'] if x['scenario'].startswith('wait:')) == ['wait:flat'], 'a path outside the policy was invented')


def _unapproved():
    return mkt_world(approved=False)


def _unapproved_check(m):
    r = m.mres()
    need((r['mkt_policy']['approved'], r['mkt_spec']['approved']) == (False, False), 'an unapproved policy or register was not labelled unapproved')
    r2 = steel_world(sq()).mres()
    need((r2['mkt_policy']['approved'], r2['mkt_spec']['approved']) == (True, True), 'the approved control was not labelled approved')


def _no_projects(m):
    r = m.mtres(authorised=())
    need(all(x['subject'].endswith('|index') for x in r['signals']), 'a tenant run with no authorised project reported on a project: %r' % ([x['subject'] for x in r['signals']],))


def _repro(m):
    a, b = m.mdetect(), m.mdetect()
    need(a['run_key'] == b['run_key'] and a['result']['signals'] == b['result']['signals'], 'the same inputs gave a different run')
    m.quote_rows(conc('Q-Z', sup='SUP-003', rate='32000')[0])
    c = m.mdetect()
    need(c['run_key'] != a['run_key'], 'a new input did not change the run key')


# ---------------------------------------------------------------- the checker
def _signals(m, authorised=None):
    """rule runs and signals from a project run and a tenant run (union): a rule is 'raised' if either raised it"""
    out_sig, out_run = [], {}
    for fn in (m.mres, (lambda: m.mtres(authorised=authorised)) if authorised else m.mtres):
        r = fn()
        out_sig += r['signals']
        for k, v in r['rule_runs'].items():
            if k not in out_run or out_run[k]['status'] == 'evaluated':
                out_run[k] = v
    return out_sig, out_run


def check_case(case):
    """-> (ok, message).  Builds the world fresh for every case."""
    try:
        m = case['build']()
        ex = case['expect']
        msgs = []
        if 'rank' in ex:
            e = ex['rank']
            r, _, _ = rank(m, e.get('decision', 'quote_ranking'), e.get('qty'))
            for k in ('status', 'definitive'):
                if k in e and r[k] != e[k]:
                    msgs.append(f'{k} is {r[k]!r}, required {e[k]!r}')
            if 'order' in e and [x['offer'] for x in r['ranking']] != e['order']:
                msgs.append('ranking order is %r, required %r' % ([x['offer'] for x in r['ranking']], e['order']))
            for ref, cls in e.get('excluded', {}).items():
                got = {x['offer']: x['class'] for x in r['excluded']}
                if got.get(ref) != cls:
                    msgs.append(f'{ref} should be excluded as {cls}, found {got}')
            if 'may' in e:
                ok, why = CP.may_recommend(r)
                if ok != e['may']:
                    msgs.append(f'may_recommend is {ok}, required {e["may"]} ({why})')
            if 'why_has' in e and e['why_has'] not in ' '.join(CP.may_recommend(r)[1] + r.get('outstanding', [])):
                msgs.append('the reasons do not say %r' % e['why_has'])
        if 'rules' in ex:
            e = ex['rules']
            sig, runs = _signals(m, e.get('authorised'))

            def hit(spec):
                rid, _, suffix = spec.partition(':')
                return [s for s in sig if s['rule']['id'] == 'DET-' + rid and (not suffix or s['subject'].endswith(suffix))]
            for spec in e.get('raised', ()):
                if not hit(spec):
                    msgs.append(f'{spec} should be raised; raised: {sorted({s["rule"]["id"][4:] + ":" + s["subject"] for s in sig})}')
            for spec in e.get('silent', ()):
                if hit(spec):
                    msgs.append(f'{spec} should be silent but raised {[s["subject"] for s in hit(spec)]}')
            for rid, st in e.get('run', {}).items():
                if runs.get(rid, {}).get('status') != st:
                    msgs.append(f'{rid} run status is {runs.get(rid, {}).get("status")!r}, required {st!r}')
        if 'fn' in ex:
            ex['fn'](m)
        return (not msgs, '; '.join(msgs))
    except AssertionError as e:
        return False, str(e)
    except Exception as e:                                                     # an unexpected exception is a failure of the case, never a pass
        return False, f'{type(e).__name__}: {e}'


def cases():
    return CASES
