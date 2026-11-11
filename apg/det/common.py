"""Shared helpers for the detection rules (Blueprint Section 06 section 5 and section 10: a rule that cannot run says so): rule start-up (is the rule configured?), run records, plain-language money and percentage text, exact decimal reading.
No rule reads the store, the clock or any global: it receives a snap.Facts (the pinned inputs) and the detection policy."""
from . import policy as DP
from .. import policy_approval as PA
from ..fin import fmath

RULE_VERSIONS = {'R01': 1, 'R02': 1, 'R03': 1, 'R04': 1, 'R04B': 1, 'R05': 1, 'R06': 1, 'R07': 1, 'R08': 1, 'R09': 1, 'AGG': 1, 'DLY': 1, 'LAB': 1, 'DEF': 1, 'D01': 1, 'D02': 1}
RUN_STATES = ('evaluated', 'not_configured', 'disabled', 'cannot_assess')


def det_policy(F):
    ver = F.params.get('det_policy')
    p = F.get(DP.POLICY_KIND, ver) if ver else None
    return DP.view(p, PA.pinned(F.params, DP.POLICY_KIND, ver)) if p is not None else None      # APG-F67: only approvals the run confirmed


def new_run(rid):
    return {'rule': rid, 'version': RULE_VERSIONS[rid], 'status': 'evaluated', 'evaluated': 0, 'signals': 0, 'silent': 0, 'not_assessed': [], 'notes': [], 'missing_parameters': [], 'decision': ''}


def start(F, dp, rid):
    """-> (rule dict, params, run).  rule is None when the rule does not run; the run record then says why (never a silent skip)."""
    run = new_run(rid)
    if dp is None:
        run['status'] = 'cannot_assess'
        run['notes'].append('DET_POLICY_NOT_PINNED')
        return None, None, run
    ent = (dp.get('rules') or {}).get(rid)
    if rid in DP.RULES:
        if ent is not None and ent.get('enabled') is False:
            run['status'] = 'disabled'
            run['notes'].append('SWITCHED_OFF_IN_POLICY')
            return None, None, run
        params, miss = DP.rule_params(dp, rid)
        if params is None:
            run['status'] = 'not_configured'
            run['missing_parameters'] = miss
            run['decision'] = DP.RULES[rid][2]
            return None, None, run
        params.pop('enabled', None)
    else:
        params = {}
    return {'id': 'DET-' + rid, 'version': RULE_VERSIONS[rid], 'params': params}, params, run


def cannot(run, *codes):
    run['status'] = 'cannot_assess'
    run['notes'].extend(codes)
    return [], run


def money(c):
    if c is None:
        return 'unknown'
    sign = '-' if c < 0 else ''
    c = abs(c)
    return f'{sign}{c // 100:,}.{c % 100:02d}'


def pct(bps):
    if bps is None:
        return 'unknown'
    sign = '-' if bps < 0 else ''
    b = abs(bps)
    return f'{sign}{b // 100}.{b % 100:02d}%'


def micro(text):
    """Exact decimal text -> integer millionths (hours, quantities).  None for anything that is not a plain non-negative decimal."""
    if not isinstance(text, str) or not text or not text.isascii():
        return None
    whole, _, frac = text.partition('.')
    if not whole.isdigit() or (frac and not frac.isdigit()) or len(frac) > 6:
        return None
    return int(whole) * 1_000_000 + int((frac + '000000')[:6])


def days(a, b):
    return fmath.days_between(a, b)


def usable_payload(p):
    from ..fin.intake import usable
    return p is not None and usable(p)


def held_codes(p):
    if p.get('conflict'):
        return ['CONFLICT_SAME_KEY']
    return list(p['intrinsic']['pending']) or ['NOT_USABLE']


def supplier_of(F, kind, key):
    """The supplier id a stored record is reconciled to, else the text it carried."""
    st = F.recon(kind, key)
    rec = F.get(kind, key)
    if st is not None and st.get('supplier_id'):
        return st['supplier_id']
    return (rec or {}).get('fields', {}).get('supplier_ref')


def exceeds_bps(num, den, tol_bps):
    """True when num/den is STRICTLY above tol_bps basis points - decided by exact integer cross-multiplication, never by a rounded ratio (so 500.0002 bps does exceed 500).
    A non-positive denominator has no ratio and never exceeds."""
    return den > 0 and num * 10000 > tol_bps * den


def at_least_bps(num, den, thr_bps):
    return den > 0 and num * 10000 >= thr_bps * den
