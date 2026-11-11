#!/usr/bin/env python3
"""CR-02 Stage 1 (rev 2) -- deterministic cases, differential oracle, properties and change-control cases for the
materiality REFERENCE MODEL v0.1.  SYNTHETIC values only; the numbers below are illustrative test values,
NOT proposed defaults.   Usage:  python3 -I cr02_materiality_tests.py [--quiet] [--failfast]
Env:  CR02_MODEL_PATH  path of the model file to test (used by the mutation runner; default = sibling file)."""
import datetime
import importlib.util, os, random, sys, json, copy
sys.dont_write_bytecode = True   # keep the working copy free of caches
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
MP = os.environ.get('CR02_MODEL_PATH', os.path.join(HERE, 'cr02_materiality_model.py'))
spec = importlib.util.spec_from_file_location('cr02_model_under_test', MP)
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

QUIET = '--quiet' in sys.argv
FAILFAST = '--failfast' in sys.argv


class _Fails(list):
    def append(self, x):
        super().append(x)
        if FAILFAST:
            print('FAILED (failfast):', str(x)[:300]); sys.exit(1)


fails = _Fails(); ran = {'cases': 0, 'change': 0, 'props': 0, 'diff': 0}

def P(**over):
    p = {'version': 'P-1', 'rules': {
            'exposure': {'abs_cents': 500000, 'rel_bps': 100, 'rel_base': 'contract_value'},
            'extracted_value': {'abs_cents': 100000},
            'forecast_or_estimate': {'abs_cents': 1000000, 'delay_days': 5},
            'recommendation_or_conclusion': {},
            'calc_all': {'all_records': True},
            'bad_rule': {'abs_cents': 0}},
         'always_material': ['tax', 'retention', 'statutory_notice'], 'aggregate': True,
         'aggregation': {'keys': ['project'], 'window_days': 30}}
    p.update(over); return p

def R(subject='exposure', amount=0, **kw):
    r = {'subject': subject, 'amount_cents': amount, 'bases': {'contract_value': 100000000}}
    r.update(kw); return r

def run_case(cid, rec, pol, group, exp_mat, exp_reasons):
    ran['cases'] += 1
    got = M.assess(rec, pol, group)
    ok = got['material'] == exp_mat and got['reasons'] == sorted(exp_reasons)
    if not ok: fails.append(('CASE', cid, exp_mat, exp_reasons, got['material'], got['reasons']))
    if not QUIET: print(('OK   ' if ok else 'FAIL ') + cid)

NB = ['NM-BELOW']
# ---- boundaries: absolute (exposure: abs 500000; rel 100 bps of contract_value) -----------------------------------
run_case('AB-01 just below abs',        R(amount=499999), P(), None, False, NB)
run_case('AB-02 at abs',                R(amount=500000), P(), None, True, ['M-ABS'])
run_case('AB-03 just above abs',        R(amount=500001), P(), None, True, ['M-ABS'])
run_case('AB-04 zero',                  R(amount=0), P(), None, False, NB)
run_case('AB-05 negative at abs',       R(amount=-500000), P(), None, True, ['M-ABS'])
run_case('AB-06 negative below abs',    R(amount=-499999), P(), None, False, NB)
# relative: base 40,000,000 -> 100 bps = 400,000
b40 = {'contract_value': 40000000}
run_case('RB-01 just below rel',        R(amount=399999, bases=b40), P(), None, False, NB)
run_case('RB-02 at rel (abs not hit)',  R(amount=400000, bases=b40), P(), None, True, ['M-REL'])
run_case('RB-03 above rel',             R(amount=400001, bases=b40), P(), None, True, ['M-REL'])
run_case('RB-04 both abs and rel',      R(amount=600000, bases=b40), P(), None, True, ['M-ABS', 'M-REL'])
run_case('RB-05 base large, rel quiet', R(amount=499999, bases={'contract_value': 10**12}), P(), None, False, NB)
# base problems
run_case('BA-01 base missing',          R(amount=100, bases={}), P(), None, True, ['M-BASE-INVALID'])
run_case('BA-02 bases absent entirely', {'subject': 'exposure', 'amount_cents': 100}, P(), None, True, ['M-BASE-INVALID'])
run_case('BA-03 base zero',             R(amount=100, bases={'contract_value': 0}), P(), None, True, ['M-BASE-INVALID'])
run_case('BA-04 base negative',         R(amount=100, bases={'contract_value': -5}), P(), None, True, ['M-BASE-INVALID'])
run_case('BA-05 base float',            R(amount=100, bases={'contract_value': 1000.0}), P(), None, True, ['M-BASE-INVALID'])
run_case('BA-06 base bool',             R(amount=100, bases={'contract_value': True}), P(), None, True, ['M-BASE-INVALID'])
run_case('BA-07 base wrong key',        R(amount=100, bases={'forecast_margin': 10**9}), P(), None, True, ['M-BASE-INVALID'])
run_case('BA-08 abs hit and base bad',  R(amount=500000, bases={}), P(), None, True, ['M-ABS', 'M-BASE-INVALID'])
run_case('BA-09 bases not a dict',      R(amount=100, bases=[1]), P(), None, True, ['M-BASE-INVALID'])
# amount problems
run_case('AM-01 missing (None)',        R(amount=None), P(), None, True, ['M-AMOUNT-MISSING'])
run_case('AM-02 key absent',            {'subject': 'exposure', 'bases': {'contract_value': 10**9}}, P(), None, True, ['M-AMOUNT-MISSING'])
run_case('AM-03 string',                R(amount='500000'), P(), None, True, ['M-AMOUNT-INVALID'])
run_case('AM-04 float',                 R(amount=500000.0), P(), None, True, ['M-AMOUNT-INVALID'])
run_case('AM-05 bool',                  R(amount=True), P(), None, True, ['M-AMOUNT-INVALID'])
run_case('AM-06 NaN',                   R(amount=float('nan')), P(), None, True, ['M-INPUT-INVALID'])
run_case('AM-07 huge int below abs? no, above', R(amount=10**15, bases={'contract_value': 10**18}), P(), None, True, ['M-ABS'])
# categories
run_case('CA-01 tax tiny amount',       R(amount=1, categories=['tax']), P(), None, True, ['M-ALWAYS'])
run_case('CA-02 retention + abs',       R(amount=500000, categories=['retention']), P(), None, True, ['M-ABS', 'M-ALWAYS'])
run_case('CA-03 other category',        R(amount=1, categories=['materials']), P(), None, False, NB)
run_case('CA-04 case-sensitive',        R(amount=1, categories=['Tax']), P(), None, False, NB)
run_case('CA-05 categories not list',   R(amount=1, categories='tax'), P(), None, True, ['M-INPUT-INVALID'])
run_case('CA-06 categories has non-str',R(amount=1, categories=['tax', 5]), P(), None, True, ['M-INPUT-INVALID'])
run_case('CA-07 empty categories',      R(amount=1, categories=[]), P(), None, False, NB)
run_case('CA-08 always + unset rule',   {'subject': 'recommendation_or_conclusion', 'categories': ['tax']}, P(), None, True, ['M-ALWAYS', 'M-THRESHOLD-UNSET'])
# subject / rule problems
run_case('SU-01 unset rule',            {'subject': 'recommendation_or_conclusion', 'amount_cents': 0}, P(), None, True, ['M-THRESHOLD-UNSET'])
run_case('SU-02 invalid rule (abs 0)',  {'subject': 'bad_rule', 'amount_cents': 0}, P(), None, True, ['M-THRESHOLD-INVALID'])
run_case('SU-03 unknown subject',       {'subject': 'nope', 'amount_cents': 0}, P(), None, True, ['M-UNKNOWN-SUBJECT'])
run_case('SU-04 subject missing',       {'amount_cents': 0}, P(), None, True, ['M-UNKNOWN-SUBJECT'])
run_case('SU-05 subject not str',       {'subject': 7, 'amount_cents': 0}, P(), None, True, ['M-UNKNOWN-SUBJECT'])
for i, bad in enumerate([{'abs_cents': -1}, {'abs_cents': 1.5}, {'abs_cents': True}, {'abs_cents': '5'}, {'rel_bps': 5},
                         {'rel_base': 'contract_value'}, {'rel_bps': 5, 'rel_base': 'nonsense'}, {'rel_bps': 0, 'rel_base': 'contract_value'},
                         {'delay_days': 0}, {'delay_days': 2.0}, {'abs_cents': 5, 'extra': 1}, 'abs', None, 5,
                         {'all_records': False}, {'all_records': 1}, {'all_records': 'yes'}, {'all_records': True, 'abs_cents': 5},
                         {'all_records': True, 'delay_days': 3}, {'all_records': None}]):
    run_case(f'RU-{i+1:02d} invalid rule {bad!r}', {'subject': 'exposure', 'amount_cents': 0}, P(rules={'exposure': bad}), None, True, ['M-THRESHOLD-INVALID'])
run_case('RU-15 rules value {} is unset', {'subject': 'exposure', 'amount_cents': 0}, P(rules={'exposure': {}}), None, True, ['M-THRESHOLD-UNSET'])
# policy problems
for i, bad in enumerate([None, {}, [], 'p', P(version=''), P(version=5), P(version='  '), P(rules=[]), P(rules=None),
                         P(always_material='tax'), P(always_material=[1]), P(always_material=['']), P(aggregate='yes'), P(aggregate=1),
                         P(aggregation={'keys': ['supplier'], 'window_days': 30}), P(aggregation={'keys': ['project'], 'window_days': 0}),
                         P(aggregation={'keys': [], 'window_days': 30}), P(aggregation={'keys': ['project', 'project'], 'window_days': 30}),
                         P(aggregation={'keys': ['project'], 'window_days': True}), P(aggregation={'keys': ['project'], 'window_days': 1.5}),
                         P(aggregation={'keys': 'project', 'window_days': 30}), P(aggregation={'keys': ['project']}),
                         P(aggregation={'keys': ['project'], 'window_days': 30, 'x': 1}), P(aggregation=None), P(aggregation=[])]):
    run_case(f'PO-{i+1:02d} invalid policy', R(amount=0), bad, None, True, ['M-POLICY-INVALID'])
run_case('PO-R1 record not a dict',     'x', P(), None, True, ['M-INPUT-INVALID'])
run_case('PO-R2 record None',           None, P(), None, True, ['M-INPUT-INVALID'])
# delay measure (forecast_or_estimate: abs 1,000,000; delay 5 days)
FE = lambda a, d, **k: {'subject': 'forecast_or_estimate', 'amount_cents': a, 'delay_days': d, **k}
run_case('DY-01 below both',            FE(999999, 4), P(), None, False, NB)
run_case('DY-02 days at threshold',     FE(0, 5), P(), None, True, ['M-DAYS'])
run_case('DY-03 negative days',         FE(0, -5), P(), None, True, ['M-DAYS'])
run_case('DY-04 amount at, days below', FE(1000000, 4), P(), None, True, ['M-ABS'])
run_case('DY-05 days missing',          FE(0, None), P(), None, True, ['M-DAYS-MISSING'])
run_case('DY-06 days float',            FE(0, 4.5), P(), None, True, ['M-DAYS-INVALID'])
run_case('DY-07 days bool',             FE(0, True), P(), None, True, ['M-DAYS-INVALID'])
run_case('DY-08 amount missing days ok',FE(None, 0), P(), None, True, ['M-AMOUNT-MISSING'])
run_case('DY-09 both hit',              FE(1000000, 9), P(), None, True, ['M-ABS', 'M-DAYS'])
# aggregation (exposure: abs 500000)
G = lambda a, **k: {'subject': 'exposure', 'amount_cents': a, **k}
run_case('AG-01 split just over',       R(amount=300000), P(), [G(300000)], True, ['M-AGG'])
run_case('AG-02 split just under',      R(amount=200000), P(), [G(299999)], False, NB)
run_case('AG-03 split exactly at',      R(amount=250000), P(), [G(250000)], True, ['M-AGG'])
run_case('AG-04 aggregate off',         R(amount=300000), P(aggregate=False), [G(300000)], False, NB)
run_case('AG-05 empty group',           R(amount=300000), P(), [], False, NB)
run_case('AG-06 member other subject',  R(amount=1), P(), [{'subject': 'extracted_value', 'amount_cents': 999999}], True, ['M-AGG-UNKNOWN'])
run_case('AG-07 member missing amount', R(amount=1), P(), [G(None)], True, ['M-AGG-UNKNOWN'])
run_case('AG-08 member float amount',   R(amount=1), P(), [G(2.5)], True, ['M-AGG-UNKNOWN'])
run_case('AG-09 member not a dict',     R(amount=1), P(), ['x'], True, ['M-AGG-UNKNOWN'])
run_case('AG-10 credits do not net',    R(amount=300000), P(), [G(-300000)], True, ['M-AGG'])
run_case('AG-11 single and aggregate',  R(amount=500000), P(), [G(1)], True, ['M-ABS', 'M-AGG'])
run_case('AG-12 relative aggregate',    R(amount=200000, bases=b40), P(), [G(200000)], True, ['M-AGG'])
run_case('AG-13 relative agg below',    R(amount=200000, bases=b40), P(), [G(199999)], False, NB)
run_case('AG-14 delay-only rule ignores group', FE(0, 1), P(rules={'forecast_or_estimate': {'delay_days': 5}}), [FE(0, 1)], False, NB)
run_case('AG-15 three-way split',       R(amount=170000), P(), [G(170000), G(170000)], True, ['M-AGG'])
run_case('AG-16 abs and rel both on aggregate', R(amount=600000, bases=b40), P(), [G(600000)], True, ['M-ABS', 'M-AGG', 'M-REL'])
_pn = P(); del _pn['aggregate']
run_case('AG-17 aggregate defaults to ON when key absent', R(amount=300000), _pn, [G(300000)], True, ['M-AGG'])

# ---- all_records: an INTENTIONAL unconditional rule is not the same as a missing threshold (rev 2) -----------------------
CA = lambda a, **k: {'subject': 'calc_all', 'amount_cents': a, **k}
run_case('AL-01 all_records, zero amount',     CA(0), P(), None, True, ['M-ALL-RECORDS'])
run_case('AL-02 all_records, amount missing',  CA(None), P(), None, True, ['M-ALL-RECORDS'])
run_case('AL-03 all_records, junk amount',     CA('x'), P(), None, True, ['M-ALL-RECORDS'])
run_case('AL-04 all_records, no amount key',   {'subject': 'calc_all'}, P(), None, True, ['M-ALL-RECORDS'])
run_case('AL-05 all_records + tax category',   CA(0, categories=['tax']), P(), None, True, ['M-ALL-RECORDS', 'M-ALWAYS'])
run_case('AL-06 all_records ignores group',    CA(1), P(), [CA(1)], True, ['M-ALL-RECORDS'])
run_case('AL-07 unset stays a DIFFERENT reason', {'subject': 'recommendation_or_conclusion', 'amount_cents': 0}, P(), None, True, ['M-THRESHOLD-UNSET'])
run_case('AL-08 categories still validated first', CA(0, categories='tax'), P(), None, True, ['M-INPUT-INVALID'])

# ---- grouping: assess_with_context (rev 2) --------------------------------------------------------------------------------
def run_ctx(cid, rec, cands, pol, exp_mat, exp_reasons):
    ran['cases'] += 1
    got = M.assess_with_context(rec, cands, pol)
    ok = got['material'] == exp_mat and got['reasons'] == sorted(exp_reasons)
    if not ok: fails.append(('CTX', cid, exp_mat, exp_reasons, got['material'], got['reasons']))
    if not QUIET: print(('OK   ' if ok else 'FAIL ') + cid)

def X(i, amt, date, project='P1', supplier='S1', subject='exposure', **k):
    r = {'id': i, 'subject': subject, 'amount_cents': amt, 'group': {'project': project, 'supplier': supplier}, 'date': date,
         'bases': {'contract_value': 100000000}}
    r.update(k); return r
PS = P(aggregation={'keys': ['project', 'supplier'], 'window_days': 30})     # narrower key
base = X('a', 300000, '2026-03-10')
run_ctx('CX-01 same project, in window',            base, [X('b', 300000, '2026-03-20')], P(), True, ['M-AGG'])
run_ctx('CX-02 exactly window_days apart',          base, [X('b', 300000, '2026-02-08')], P(), True, ['M-AGG'])
run_ctx('CX-03 one day outside the window',         base, [X('b', 300000, '2026-02-07')], P(), False, NB)
run_ctx('CX-04 later date, exactly in window',      base, [X('b', 300000, '2026-04-09')], P(), True, ['M-AGG'])
run_ctx('CX-05 later date, one day outside',        base, [X('b', 300000, '2026-04-10')], P(), False, NB)
run_ctx('CX-06 other project',                      base, [X('b', 300000, '2026-03-10', project='P2')], P(), False, NB)
run_ctx('CX-07 other subject type',                 base, [X('b', 900000, '2026-03-10', subject='extracted_value')], P(), False, NB)
run_ctx('CX-08 key=project catches cross-supplier split', base, [X('b', 300000, '2026-03-10', supplier='S2')], P(), True, ['M-AGG'])
run_ctx('CX-09 key=project+supplier MISSES cross-supplier split (documented evasion)', base, [X('b', 300000, '2026-03-10', supplier='S2')], PS, False, NB)
run_ctx('CX-10 key=project+supplier catches same supplier', base, [X('b', 300000, '2026-03-10')], PS, True, ['M-AGG'])
run_ctx('CX-11 record has no group',                {**base, 'group': None}, [], P(), True, ['M-AGG-UNKNOWN'])
run_ctx('CX-12 record group lacks a key',           {**base, 'group': {'project': 'P1'}}, [], PS, True, ['M-AGG-UNKNOWN'])
run_ctx('CX-13 record group value empty',           {**base, 'group': {'project': ''}}, [], P(), True, ['M-AGG-UNKNOWN'])
run_ctx('CX-14 record has no date',                 {k: v for k, v in base.items() if k != 'date'}, [], P(), True, ['M-AGG-UNKNOWN'])
for i, bad in enumerate(['2026-3-10', '20260310', '2026/03/10', '2026-02-30', '2026-13-01', 20260310, None, '2026-03-10T00:00', ' 2026-03-10', '2026-03-10\n', '\u0662\u0660\u0662\u0666-\u0660\u0663-\u0661\u0660', '0000-01-01', '2026-03-10 ']):
    run_ctx(f'CX-15{chr(97+i)} record date {bad!r} is unusable', {**base, 'date': bad}, [], P(), True, ['M-AGG-UNKNOWN'])
    run_ctx(f'CX-16{chr(97+i)} candidate date {bad!r} is unusable', base, [X('b', 1, bad)], P(), True, ['M-AGG-UNKNOWN'])
run_ctx('CX-17 candidate group missing',            base, [{**X('b', 1, '2026-03-10'), 'group': None}], P(), True, ['M-AGG-UNKNOWN'])
run_ctx('CX-18 candidate not a dict',               base, ['x'], P(), True, ['M-AGG-UNKNOWN'])
run_ctx('CX-19 other-subject candidate may be junk', base, [{'subject': 'extracted_value', 'date': 'bad', 'group': None}], P(), False, NB)
run_ctx('CX-20 the record itself is skipped',       base, [X('a', 300000, '2026-03-10')], P(), False, NB)
run_ctx('CX-21 different record with same amount is NOT skipped', base, [X('z', 300000, '2026-03-10')], P(), True, ['M-AGG'])
run_ctx('CX-22 aggregate off: no grouping needed',  {**base, 'group': None, 'date': None}, [], P(aggregate=False), False, NB)
_ns = P(); del _ns['aggregation']
run_ctx('CX-23 aggregation on but no spec',         base, [], _ns, True, ['M-AGG-SPEC-MISSING'])
run_ctx('CX-24 delay-only rule needs no grouping',  {'subject': 'forecast_or_estimate', 'amount_cents': 0, 'delay_days': 1}, [], P(rules={'forecast_or_estimate': {'delay_days': 5}}), False, NB)
run_ctx('CX-25 all_records needs no grouping',      {'subject': 'calc_all', 'amount_cents': 0}, [], P(), True, ['M-ALL-RECORDS'])
run_ctx('CX-26 relative aggregate in project',      X('a', 200000, '2026-03-10', bases={'contract_value': 40000000}), [X('b', 200000, '2026-03-12')], P(), True, ['M-AGG'])
run_ctx('CX-27 relative aggregate just below',      X('a', 200000, '2026-03-10', bases={'contract_value': 40000000}), [X('b', 199999, '2026-03-12')], P(), False, NB)
run_ctx('CX-28 single already material + group',   X('a', 500000, '2026-03-10'), [X('b', 1, '2026-03-12')], P(), True, ['M-ABS', 'M-AGG'])
run_ctx('CX-29 three-way split in window',         X('a', 170000, '2026-03-01'), [X('b', 170000, '2026-03-15'), X('c', 170000, '2026-03-29')], P(), True, ['M-AGG'])
# chain: c is 28 days after b and 56 days after a; assessing c sees only b (a is outside c's window) -> known limitation OQ-A1-7
run_ctx('CX-30 chain splitting: end of chain sees only its neighbour (known limitation)', X('c', 200000, '2026-04-26'),
        [X('a', 200000, '2026-03-01'), X('b', 200000, '2026-03-29')], P(), False, NB)
run_ctx('CX-31 chain: the middle record DOES see both', X('b', 200000, '2026-03-29'), [X('a', 200000, '2026-03-01'), X('c', 200000, '2026-04-26')], P(), True, ['M-AGG'])
run_ctx('CX-32 candidates not a list',              base, 'x', P(), True, ['M-INPUT-INVALID'])
run_ctx('CX-33 invalid policy',                     base, [], None, True, ['M-POLICY-INVALID'])
run_ctx('CX-34 NaN in a candidate',                 base, [X('b', float('nan'), '2026-03-10')], P(), True, ['M-INPUT-INVALID'])
run_ctx('CX-35 unknown subject',                    {**base, 'subject': 'nope'}, [], P(), True, ['M-UNKNOWN-SUBJECT'])
run_ctx('CX-36 record not a dict',                  'x', [], P(), True, ['M-INPUT-INVALID'])
run_ctx('CX-37 unhashable subject',                 {**base, 'subject': ['x']}, [], P(), True, ['M-UNKNOWN-SUBJECT'])
ran['cases'] += 1
c1 = M.assess_with_context(base, [X('b', 1, '2026-03-10')], P()); c2 = M.assess_with_context(base, [X('b', 2, '2026-03-10')], P())
if c1['digest'] == c2['digest'] or c1['digest'] is None: fails.append(('CTX', 'CX-38 digest covers every candidate'))
ran['cases'] += 1
c3 = M.assess_with_context(base, [X('b', 1, '2026-09-10')], P())   # outside the window: not a member, but still in the digest
if c3['digest'] == M.assess_with_context(base, [], P())['digest']: fails.append(('CTX', 'CX-39 digest covers non-member candidates'))
# decision record
d1 = M.assess(R(amount=10), P(), None); d2 = M.assess(R(amount=10), P(), None)
ran['cases'] += 1
okd = d1 == d2 and d1['rule_version'] == 'P-1' and isinstance(d1['digest'], str) and len(d1['digest']) == 64
if not okd: fails.append(('CASE', 'DG-01 repeatable', d1, d2))
d3 = M.assess(R(amount=10), P(version='P-2'), None)
ran['cases'] += 1
if d3['digest'] == d1['digest'] or d3['rule_version'] != 'P-2': fails.append(('CASE', 'DG-02 version changes digest'))
rk = {'bases': {'contract_value': 100000000}, 'amount_cents': 10, 'subject': 'exposure'}
ran['cases'] += 1
if M.assess(rk, P(), None)['digest'] != d1['digest']: fails.append(('CASE', 'DG-03 key order does not change digest'))
ran['cases'] += 1
if M.assess(R(amount=11), P(), None)['digest'] == d1['digest']: fails.append(('CASE', 'DG-04 record change changes digest'))
ran['cases'] += 1
if M.assess(R(amount=10), P(), [G(1)])['digest'] == d1['digest']: fails.append(('CASE', 'DG-05 group changes digest'))
ran['cases'] += 1
if M.assess(R(amount=float('nan')), P(), None)['digest'] is not None: fails.append(('CASE', 'DG-06 NaN gives no digest'))
ran['cases'] += 1
if M.assess(R(amount=10), None, None)['rule_version'] is not None: fails.append(('CASE', 'DG-07 no policy gives no version'))

# ---- change control -----------------------------------------------------------------------------------------------
def ch(cid, mut, exp_kind, approvals, exp, proposer='p1', pkind='human', version='P-2', swap=False):
    ran['change'] += 1
    old = P(); old['rules'].pop('bad_rule'); new = copy.deepcopy(old); mut(new); new['version'] = version   # change-control policies hold no deliberately invalid rule
    a, b = (new, old) if swap else (old, new)
    kind = M.classify_change(a, b)
    change = {'proposer': proposer, 'proposer_kind': pkind, 'approvals': approvals}
    res = M.change_allowed(a, b, change)
    ok = kind == exp_kind and res == exp
    if not ok: fails.append(('CHANGE', cid, exp_kind, exp, kind, res))
    if not QUIET: print(('OK   ' if ok else 'FAIL ') + cid)
OWN = {'approver': 'own', 'role': 'materiality_owner', 'kind': 'human'}
OTH = {'approver': 'fin', 'role': 'finance', 'kind': 'human'}
AIA = {'approver': 'bot', 'role': 'materiality_owner', 'kind': 'ai'}
lowerE = lambda p: p['rules']['exposure'].update(abs_cents=400000)
raiseE = lambda p: p['rules']['exposure'].update(abs_cents=600000)
ch('CH-01 no change',           lambda p: None, 'none', [OWN], (False, 'C-NOCHANGE'))
ch('CH-02 tighten, owner',      lowerE, 'tighten', [OWN], (True, 'C-OK'))
ch('CH-03 tighten, none',       lowerE, 'tighten', [], (False, 'C-APPROVAL'))
ch('CH-04 tighten, non-owner',  lowerE, 'tighten', [OTH], (False, 'C-APPROVAL'))
ch('CH-05 tighten, self-approve', lowerE, 'tighten', [{'approver': 'p1', 'role': 'materiality_owner', 'kind': 'human'}], (False, 'C-APPROVAL'))
ch('CH-06 tighten, AI approver', lowerE, 'tighten', [AIA], (False, 'C-APPROVAL'))
ch('CH-07 tighten, AI proposer + owner', lowerE, 'tighten', [OWN], (True, 'C-OK'), proposer='bot', pkind='ai')
ch('CH-08 loosen, owner only',  raiseE, 'loosen', [OWN], (False, 'C-APPROVAL'))
ch('CH-09 loosen, owner+other', raiseE, 'loosen', [OWN, OTH], (True, 'C-OK'))
ch('CH-10 loosen, owner twice', raiseE, 'loosen', [OWN, dict(OWN)], (False, 'C-APPROVAL'))
ch('CH-11 loosen, owner+proposer', raiseE, 'loosen', [OWN, {'approver': 'p1', 'role': 'finance', 'kind': 'human'}], (False, 'C-APPROVAL'))
ch('CH-12 loosen, two non-owners', raiseE, 'loosen', [OTH, {'approver': 'x', 'role': 'qs', 'kind': 'human'}], (False, 'C-APPROVAL'))
ch('CH-13 loosen, AI second',   raiseE, 'loosen', [OWN, {'approver': 'bot', 'role': 'finance', 'kind': 'ai'}], (False, 'C-APPROVAL'))
ch('CH-14 same version',        raiseE, 'loosen', [OWN, OTH], (False, 'C-VERSION'), version='P-1')
ch('CH-15 unset -> set is loosen', lambda p: p['rules'].__setitem__('recommendation_or_conclusion', {'abs_cents': 5}), 'loosen', [OWN], (False, 'C-APPROVAL'))
ch('CH-16 unset -> set, 2 approvals', lambda p: p['rules'].__setitem__('recommendation_or_conclusion', {'abs_cents': 5}), 'loosen', [OWN, OTH], (True, 'C-OK'))
ch('CH-17 set -> unset is tighten', lambda p: p['rules'].__setitem__('exposure', {}), 'tighten', [OWN], (True, 'C-OK'))
ch('CH-18 add always category', lambda p: p['always_material'].append('gst'), 'tighten', [OWN], (True, 'C-OK'))
ch('CH-19 remove always category', lambda p: p['always_material'].remove('tax'), 'loosen', [OWN], (False, 'C-APPROVAL'))
ch('CH-20 add a second test',   lambda p: p['rules']['extracted_value'].update(delay_days=3), 'tighten', [OWN], (True, 'C-OK'))
ch('CH-21 remove a test',       lambda p: p['rules']['forecast_or_estimate'].pop('delay_days'), 'loosen', [OWN], (False, 'C-APPROVAL'))
ch('CH-22 mixed',               lambda p: (lowerE(p), p['always_material'].remove('tax')), 'mixed', [OWN], (False, 'C-APPROVAL'))
ch('CH-23 mixed, two approvals',lambda p: (lowerE(p), p['always_material'].remove('tax')), 'mixed', [OWN, OTH], (True, 'C-OK'))
ch('CH-24 base change',         lambda p: p['rules']['exposure'].update(rel_base='forecast_final_cost'), 'mixed', [OWN], (False, 'C-APPROVAL'))
ch('CH-24b base change, 2 approvals', lambda p: p['rules']['exposure'].update(rel_base='forecast_final_cost'), 'mixed', [OWN, OTH], (True, 'C-OK'))
ch('CH-25 aggregate off',       lambda p: p.update(aggregate=False), 'loosen', [OWN], (False, 'C-APPROVAL'))
ch('CH-26 aggregate on (was off)', lambda p: None, 'none', [OWN], (False, 'C-NOCHANGE'))
ch('CH-27 new subject, set rule', lambda p: p['rules'].__setitem__('audit_action', {'abs_cents': 9}), 'loosen', [OWN], (False, 'C-APPROVAL'))
ch('CH-28 subject removed',     lambda p: p['rules'].pop('extracted_value'), 'tighten', [OWN], (True, 'C-OK'))
ch('CH-29 lower rel threshold', lambda p: p['rules']['exposure'].update(rel_bps=50), 'tighten', [OWN], (True, 'C-OK'))
ch('CH-30 raise days',          lambda p: p['rules']['forecast_or_estimate'].update(delay_days=9), 'loosen', [OWN, OTH], (True, 'C-OK'))
ch('CH-31 reverse of loosen is tighten', raiseE, 'tighten', [OWN], (True, 'C-OK'), swap=True)
ch('CH-32 proposer missing',    lowerE, 'tighten', [OWN], (False, 'C-PROPOSER'), proposer='')
ch('CH-33 proposer kind bad',   lowerE, 'tighten', [OWN], (False, 'C-PROPOSER'), pkind='robot')
def _pc(**o):
    p = P(**o); p['rules'] = {k: v for k, v in p['rules'].items() if k != 'bad_rule'}; return p

ch('CH-37 not-configured -> all_records is EQUIVALENT', lambda p: p['rules'].__setitem__('recommendation_or_conclusion', {'all_records': True}), 'equivalent', [OWN], (True, 'C-OK'))
ch('CH-38 equivalent still needs an owner', lambda p: p['rules'].__setitem__('recommendation_or_conclusion', {'all_records': True}), 'equivalent', [OTH], (False, 'C-APPROVAL'))
ch('CH-39 all_records -> not configured is EQUIVALENT', lambda p: p['rules'].__setitem__('calc_all', {}), 'equivalent', [OWN], (True, 'C-OK'))
ch('CH-40 all_records -> threshold is a LOOSENING', lambda p: p['rules'].__setitem__('calc_all', {'abs_cents': 7}), 'loosen', [OWN], (False, 'C-APPROVAL'))
ch('CH-41 all_records -> threshold, 2 approvals', lambda p: p['rules'].__setitem__('calc_all', {'abs_cents': 7}), 'loosen', [OWN, OTH], (True, 'C-OK'))
ch('CH-42 threshold -> all_records is a TIGHTENING', lambda p: p['rules'].__setitem__('exposure', {'all_records': True}), 'tighten', [OWN], (True, 'C-OK'))
ch('CH-43 new subject with all_records is equivalent', lambda p: p['rules'].__setitem__('audit_action', {'all_records': True}), 'equivalent', [OWN], (True, 'C-OK'))
ch('CH-44 aggregation keys: add one = loosen', lambda p: p['aggregation'].update(keys=['project', 'supplier']), 'loosen', [OWN], (False, 'C-APPROVAL'))
ch('CH-45 aggregation keys: add one, 2 approvals', lambda p: p['aggregation'].update(keys=['project', 'supplier']), 'loosen', [OWN, OTH], (True, 'C-OK'))
ch('CH-46 aggregation window: larger = tighten', lambda p: p['aggregation'].update(window_days=60), 'tighten', [OWN], (True, 'C-OK'))
ch('CH-47 aggregation window: smaller = loosen', lambda p: p['aggregation'].update(window_days=10), 'loosen', [OWN], (False, 'C-APPROVAL'))
ch('CH-48 keys: add two = loosen', lambda p: p['aggregation'].update(keys=['supplier', 'project', 'package']) , 'loosen', [OWN], (False, 'C-APPROVAL'))
ch('CH-49 keys: bigger window + more keys = mixed', lambda p: p['aggregation'].update(keys=['project', 'supplier'], window_days=90), 'mixed', [OWN], (False, 'C-APPROVAL'))
ch('CH-50 spec removed while aggregation on = tighten (fails safe)', lambda p: p.pop('aggregation'), 'tighten', [OWN], (True, 'C-OK'))
ch('CH-51 aggregation switched off = loosen', lambda p: (p.update(aggregate=False)), 'loosen', [OWN], (False, 'C-APPROVAL'))
ran['change'] += 1
_o = P(aggregate=False); _o['rules'].pop('bad_rule'); _n = copy.deepcopy(_o); _n['version'] = 'P-2'; _n['aggregation']['window_days'] = 5
if M.classify_change(_o, _n) != 'none': fails.append(('CHANGE', 'CH-52 spec change ignored while aggregation is off', M.classify_change(_o, _n)))

ran['change'] += 1
if M.change_allowed(P(), P(rules=[]), {'proposer': 'a', 'proposer_kind': 'human', 'approvals': [OWN]}) != (False, 'C-INVALID'): fails.append(('CHANGE', 'CH-34 invalid new policy'))
ran['change'] += 1
if M.change_allowed(P(rules={'exposure': {'abs_cents': 0}}), P(version='P-2'), {'proposer': 'a', 'proposer_kind': 'human', 'approvals': [OWN]}) != (False, 'C-INVALID'): fails.append(('CHANGE', 'CH-35 invalid old rule'))
ran['change'] += 1
if M.change_allowed(_pc(), _pc(version='P-2', aggregate=False), {'proposer': 'a', 'proposer_kind': 'human', 'approvals': 'x'}) != (False, 'C-APPROVAL'): fails.append(('CHANGE', 'CH-36 approvals not a list'))

# ---- independent oracle (different formulation: exact fractions, positive proof of immateriality) -----------------
def oracle_material(rec, pol, grp=None):
    try:
        if not isinstance(rec, dict): return True
        json.dumps([rec, pol, grp], allow_nan=False)
        if not (isinstance(pol, dict) and isinstance(pol.get('version'), str) and pol['version'].strip()
                and isinstance(pol.get('rules'), dict)): return True
        am = pol.get('always_material', [])
        if not (isinstance(am, list) and all(isinstance(c, str) and c for c in am)): return True
        if not isinstance(pol.get('aggregate', True), bool): return True
        if 'aggregation' in pol:
            sp = pol['aggregation']
            if not (isinstance(sp, dict) and set(sp) == {'keys', 'window_days'}): return True
            ks = sp['keys']
            if not (isinstance(ks, list) and ks and all(isinstance(k, str) and k for k in ks) and len(set(ks)) == len(ks) and 'project' in ks): return True
            if not (type(sp['window_days']) is int and sp['window_days'] >= 1): return True
        if rec.get('subject') not in pol['rules'] or not isinstance(rec.get('subject'), str): return True
        cats = rec.get('categories', [])
        if not (isinstance(cats, list) and all(isinstance(c, str) for c in cats)): return True
        if set(cats) & set(am): return True
        rule = pol['rules'][rec['subject']]
        if rule == {'all_records': True}: return True          # intentional unconditional rule
        if not isinstance(rule, dict) or set(rule) - {'abs_cents', 'rel_bps', 'rel_base', 'delay_days'}: return True
        if not rule: return True
        isint = lambda x: type(x) is int
        if 'abs_cents' in rule and not (isint(rule['abs_cents']) and rule['abs_cents'] >= 1): return True
        if ('rel_bps' in rule) != ('rel_base' in rule): return True
        if 'rel_bps' in rule and not (isint(rule['rel_bps']) and rule['rel_bps'] >= 1 and rule['rel_base'] in M.BASES): return True
        if 'delay_days' in rule and not (isint(rule['delay_days']) and rule['delay_days'] >= 1): return True
        uses_amt = 'abs_cents' in rule or 'rel_bps' in rule
        def amount_immaterial(total):
            if 'abs_cents' in rule and total >= rule['abs_cents']: return False
            if 'rel_bps' in rule:
                base = (rec.get('bases') or {}).get(rule['rel_base']) if isinstance(rec.get('bases'), dict) else None
                if not (isint(base) and base >= 1): return False
                if Fraction(total, base) >= Fraction(rule['rel_bps'], 10000): return False
            return True
        if uses_amt:
            a = rec.get('amount_cents')
            if not isint(a) or not amount_immaterial(abs(a)): return True
        if 'delay_days' in rule:
            d = rec.get('delay_days')
            if not isint(d) or abs(d) >= rule['delay_days']: return True
        if grp and pol.get('aggregate', True) and uses_amt:
            mem = [rec] + list(grp)
            if not all(isinstance(x, dict) and isint(x.get('amount_cents')) and x.get('subject') == rec['subject'] for x in mem): return True
            if not amount_immaterial(sum(abs(x['amount_cents']) for x in mem)): return True
        return False
    except Exception:
        return True

def _odate(s):
    if not (isinstance(s, str) and len(s) == 10 and s.isascii() and s[4] == '-' and s[7] == '-' and (s[:4] + s[5:7] + s[8:]).isdigit()): return None
    try: return datetime.date(int(s[:4]), int(s[5:7]), int(s[8:]))
    except ValueError: return None

def oracle_ctx(rec, cands, pol):
    """Independent re-statement of assess_with_context() (materiality only)."""
    try:
        if not isinstance(cands, list): return True
        json.dumps([rec, pol, cands], allow_nan=False)
        if oracle_material(rec, pol, None): return True
        rule = pol['rules'][rec['subject']]
        if not (('abs_cents' in rule or 'rel_bps' in rule) and pol.get('aggregate', True)):
            return False
        sp = pol.get('aggregation')
        if sp is None: return True
        keys, win = sp['keys'], sp['window_days']
        ok = lambda g: isinstance(g, dict) and all(isinstance(g.get(k), str) and g.get(k) != '' for k in keys)
        rd = _odate(rec.get('date'))
        if rd is None or not ok(rec.get('group')): return True
        members = []
        for c in cands:
            if not isinstance(c, dict): return True
            if c.get('subject') != rec['subject']: continue
            if c.get('id') is not None and c.get('id') == rec.get('id'): continue
            cd = _odate(c.get('date'))
            if cd is None or not ok(c.get('group')): return True
            if all(c['group'][k] == rec['group'][k] for k in keys) and abs((cd - rd).days) <= win: members.append(c)
        return oracle_material(rec, pol, members or None)
    except Exception:
        return True

def rand_policy(rnd):
    rules = {}
    for s in ('exposure', 'extracted_value', 'forecast_or_estimate', 'recommendation_or_conclusion'):
        t = rnd.random()
        if t < .15: rules[s] = {}
        else:
            r = {}
            if rnd.random() < .8: r['abs_cents'] = rnd.choice([1, 2, 50, 1000, 500000, 10**7])
            if rnd.random() < .5: r['rel_bps'] = rnd.choice([1, 10, 100, 5000]); r['rel_base'] = rnd.choice(M.BASES)
            if rnd.random() < .4: r['delay_days'] = rnd.choice([1, 3, 10, 60])
            rules[s] = r
    pol = {'version': 'V%d' % rnd.randrange(5), 'rules': rules,
           'always_material': rnd.sample(['tax', 'retention', 'statutory_notice', 'dispute'], rnd.randrange(0, 3)),
           'aggregate': rnd.random() < .8}
    if rnd.random() < .3: pol['rules']['calc_all'] = {'all_records': True}
    if rnd.random() < .08: pol['rules']['exposure'] = {'all_records': True}
    if rnd.random() < .85:
        pol['aggregation'] = {'keys': rnd.choice([['project'], ['project', 'supplier'], ['supplier', 'project']]), 'window_days': rnd.choice([1, 7, 30, 90])}
    if rnd.random() < .03: pol['aggregation'] = rnd.choice([{'keys': ['supplier'], 'window_days': 5}, {'keys': ['project']}, {'keys': ['project'], 'window_days': 0}, 'x'])
    if rnd.random() < .04: pol['rules']['exposure'] = rnd.choice([{'abs_cents': 0}, {'rel_bps': 5}, 'x', {'abs_cents': 1.5}])
    if rnd.random() < .02: pol = rnd.choice([None, {}, {'version': ''}])
    return pol

def rand_amount(rnd):
    return rnd.choice([0, 1, 2, 49, 50, 51, 999, 1000, 1001, 499999, 500000, 500001, 10**7 - 1, 10**7, 10**7 + 1, 10**9, -1, -50, -500000, -10**7])

def rand_record(rnd, subject=None):
    r = {'subject': subject or rnd.choice(['exposure', 'extracted_value', 'forecast_or_estimate', 'recommendation_or_conclusion', 'calc_all', 'zzz'])}
    t = rnd.random()
    r['amount_cents'] = rand_amount(rnd) if t > .1 else rnd.choice([None, 1.5, '5', True])
    if rnd.random() < .6: r['delay_days'] = rnd.choice([0, 1, 2, 3, 9, 10, 11, 60, -3, None, 2.5])
    if rnd.random() < .8: r['bases'] = {b: rnd.choice([1, 100, 10**4, 10**6, 10**9, 0, -1, None]) for b in M.BASES if rnd.random() < .8}
    if rnd.random() < .3: r['categories'] = rnd.sample(['tax', 'retention', 'other', 'Tax'], rnd.randrange(0, 3))
    return r

def prop(name, ok, detail=None):
    ran['props'] += 1
    if not ok: fails.append(('PROP', name, detail))

SEEDS = [11, 23, 37, 59, 71]; N = 1500
for seed in SEEDS:
    rnd = random.Random(seed)
    for _ in range(N):
        pol = rand_policy(rnd); rec = rand_record(rnd)
        grp = None
        if rnd.random() < .4: grp = [rand_record(rnd, rec['subject']) for _ in range(rnd.randrange(0, 4))]
        got = M.assess(rec, pol, grp)
        ran['diff'] += 1
        if got['material'] != oracle_material(rec, pol, grp):
            fails.append(('DIFF', seed, rec, pol, grp, got)); 
        # DIFF-CTX: assess_with_context against the independent oracle
        rec2 = dict(rec); rec2['id'] = 'r0'
        rec2['group'] = rnd.choice([{'project': 'P1', 'supplier': 'S1'}, {'project': 'P1'}, None, {'project': ''}])
        rec2['date'] = rnd.choice(['2026-03-10', '2026-03-10', '2026-03-11', 'bad', None, '2026-02-30'])
        cands = []
        for j in range(rnd.randrange(0, 4)):
            c = rand_record(rnd, rec['subject'] if rnd.random() < .8 else None); c['id'] = 'c%d' % j
            c['group'] = rnd.choice([{'project': 'P1', 'supplier': 'S1'}, {'project': 'P1', 'supplier': 'S2'}, {'project': 'P2', 'supplier': 'S1'}, None])
            c['date'] = rnd.choice(['2026-03-10', '2026-03-01', '2026-02-01', '2026-04-20', 'bad'])
            cands.append(c)
        if rnd.random() < .02: cands = rnd.choice([None, 'x', [None]])
        ran['diff'] += 1
        gotc = M.assess_with_context(rec2, cands, pol)
        if gotc['material'] != oracle_ctx(rec2, cands, pol): fails.append(('DIFF-CTX', seed, rec2, pol, cands, gotc))
        prop('P-CTX-DET', M.assess_with_context(rec2, cands, pol) == gotc, None)
        prop('P-CTX-ORDER', M.assess_with_context(rec2, list(reversed(cands)) if isinstance(cands, list) else cands, pol)['material'] == gotc['material'], None)
        # P-CTX-GROW: adding a same-subject, in-window, same-project record never makes the result less material
        if isinstance(cands, list) and isinstance(pol, dict):
            extra = {'id': 'zz', 'subject': rec2['subject'], 'amount_cents': rnd.choice([0, 1, 1000, 10**7]), 'group': rec2['group'], 'date': rec2['date']}
            prop('P-CTX-GROW', (not M.assess_with_context(rec2, cands, pol)['material']) or M.assess_with_context(rec2, cands + [extra], pol)['material'], None)
        # P-ALLREC: an explicit all_records subject is always material, with the intentional reason
        if isinstance(pol, dict) and isinstance(pol.get('rules'), dict) and pol['rules'].get('calc_all') == {'all_records': True} and M.policy_valid(pol):
            ar = {'subject': 'calc_all', 'amount_cents': rnd.choice([0, 1, None, 'x'])}
            ra = M.assess(ar, pol, None)
            prop('P-ALLREC', ra['material'] and 'M-ALL-RECORDS' in ra['reasons'] and 'M-THRESHOLD-UNSET' not in ra['reasons'], ar)
        # P-DET: repeat and reorder keys
        prop('P-DET', M.assess(rec, pol, grp) == got, (rec, pol))
        # P-FAILCLOSED
        prop('P-FAILCLOSED', M.assess(rec, None, grp)['material'] and M.assess(rec, {'version': 'v', 'rules': {}}, grp)['material'], rec)
        # P-SIGN: negating amount and delay does not change the result (digest excluded)
        if isinstance(rec.get('amount_cents'), int) and not isinstance(rec.get('amount_cents'), bool):
            neg = dict(rec); neg['amount_cents'] = -rec['amount_cents']
            a, b = M.assess(rec, pol, None), M.assess(neg, pol, None)
            prop('P-SIGN', (a['material'], a['reasons']) == (b['material'], b['reasons']), (rec, pol))
        # P-MONO-AMT: larger absolute amount never turns material into not-material
        if isinstance(rec.get('amount_cents'), int) and not isinstance(rec.get('amount_cents'), bool):
            bigger = dict(rec); bigger['amount_cents'] = abs(rec['amount_cents']) + rnd.randrange(0, 10**6)
            prop('P-MONO-AMT', (not M.assess(rec, pol, None)['material']) or M.assess(bigger, pol, None)['material'], (rec, pol))
        # P-ALWAYS
        if pol and isinstance(pol, dict) and pol.get('always_material') and isinstance(pol.get('rules'), dict):
            r2 = copy.deepcopy(rec); r2['categories'] = [pol['always_material'][0]]
            prop('P-ALWAYS', M.assess(r2, pol, grp)['material'], (r2, pol))
        # P-MONO-THR: halving every abs threshold (stricter) never removes materiality
        if isinstance(pol, dict) and isinstance(pol.get('rules'), dict):
            tp = copy.deepcopy(pol)
            for s, ru in tp['rules'].items():
                if isinstance(ru, dict) and type(ru.get('abs_cents')) is int and ru['abs_cents'] > 1: ru['abs_cents'] = ru['abs_cents'] // 2
                if isinstance(ru, dict) and type(ru.get('rel_bps')) is int and ru['rel_bps'] > 1: ru['rel_bps'] = ru['rel_bps'] // 2
            prop('P-MONO-THR', (not M.assess(rec, pol, grp)['material']) or M.assess(rec, tp, grp)['material'], (rec, pol))
    # P-SPLIT: splitting a material amount into n parts in one group keeps every part material (aggregate on)
    for _ in range(300):
        thr = rnd.choice([100, 5000, 500000])
        pol = {'version': 'S', 'rules': {'exposure': {'abs_cents': thr}}, 'always_material': [], 'aggregate': True}
        total = thr + rnd.randrange(0, 3 * thr)
        n = rnd.randrange(2, 7)
        cuts = sorted(rnd.randrange(0, total + 1) for _ in range(n - 1))
        parts = [b - a for a, b in zip([0] + cuts, cuts + [total])]
        recs = [{'subject': 'exposure', 'amount_cents': x} for x in parts]
        ok = all(M.assess(recs[i], pol, recs[:i] + recs[i + 1:])['material'] for i in range(n))
        prop('P-SPLIT', ok, (thr, parts))
    # P-ANTISYM and P-LOOSEN-HARDER
    for _ in range(300):
        a, b = rand_policy(rnd), rand_policy(rnd)
        if not (M.policy_valid(a) and M.policy_valid(b)): continue
        k1, k2 = M.classify_change(a, b), M.classify_change(b, a)
        exp = {'tighten': 'loosen', 'loosen': 'tighten', 'mixed': 'mixed', 'none': 'none', 'invalid': 'invalid', 'equivalent': 'equivalent'}
        prop('P-ANTISYM', exp[k1] == k2, (a, b, k1, k2))
        if k1 in ('loosen', 'mixed'):
            b2 = copy.deepcopy(b); b2['version'] = 'Z-' + str(seed)
            a2 = copy.deepcopy(a); a2['version'] = 'Y-' + str(seed)
            one = {'proposer': 'p', 'proposer_kind': 'human', 'approvals': [OWN]}
            prop('P-LOOSEN-HARDER', M.change_allowed(a2, b2, one) == (False, 'C-APPROVAL'), (a, b))
            two = {'proposer': 'p', 'proposer_kind': 'human', 'approvals': [OWN, OTH]}
            prop('P-LOOSEN-TWO', M.change_allowed(a2, b2, two) == (True, 'C-OK'), (a, b))
        if k1 == 'equivalent':
            b2 = copy.deepcopy(b); b2['version'] = 'Z-' + str(seed); a2 = copy.deepcopy(a); a2['version'] = 'Y-' + str(seed)
            prop('P-EQUIV-ONE', M.change_allowed(a2, b2, {'proposer': 'p', 'proposer_kind': 'human', 'approvals': [OWN]}) == (True, 'C-OK'), (a, b))
        if k1 == 'tighten':
            b2 = copy.deepcopy(b); b2['version'] = 'Z-' + str(seed); a2 = copy.deepcopy(a); a2['version'] = 'Y-' + str(seed)
            prop('P-TIGHTEN-ONE', M.change_allowed(a2, b2, {'proposer': 'p', 'proposer_kind': 'human', 'approvals': [OWN]}) == (True, 'C-OK'), (a, b))

total = ran['cases'] + ran['change'] + ran['props'] + ran['diff']
print(f"cases {ran['cases']}  change-control {ran['change']}  differential {ran['diff']}  property checks {ran['props']}  seeds {SEEDS} x {N}")
if fails:
    print(f'FAILED: {len(fails)}')
    for f in fails[:12]: print('  ', str(f)[:300])
    sys.exit(1)
print('ALL PASS')
