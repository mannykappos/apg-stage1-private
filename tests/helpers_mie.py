"""Shared fixtures for the MIE-1 core tests.  They use the synthetic pack only (no field vocabulary), so these files are inside the core's neutrality scan (NE-01).
Every value here is a TEST-ONLY fixture value; none is guidance."""
import copy
from . import _path                                         # noqa: F401
from mie.core import canon, engine as E, reference as R
from mie.core.vocab import MieError
from mie.packs import synthetic as SP

LIMITS = {'max_pack_bytes': 200000, 'max_rules': 50, 'max_string_length': 200, 'max_batch_items': 500, 'max_abs_exponent': 30, 'max_mantissa_digits': 30,
          'max_series_points': 5000, 'max_audit_page': 500, 'max_scenarios': 10}           # TEST-ONLY host limits
EVAL = '2026-09-30'


def code(fn):
    try:
        fn()
    except MieError as e:
        return e.code
    return None


class World:
    """One engine with reference ports, two tenants (T-A, T-B) and an expired session; the synthetic pack registered and activated for T-A unless told otherwise."""
    def __init__(self, pack=None, activate=True, limits=LIMITS):
        self.now = [100]
        self.ctxp = R.RefContext(lambda: self.now[0])
        self.ctxp.register('tA', 'T-A', 10 ** 9)
        self.ctxp.register('tB', 'T-B', 10 ** 9)
        self.ctxp.register('tOld', 'T-A', 50)
        self.obs, self.reg, self.res, self.aud, self.appr, self.hooks = R.RefObservations(), R.RefRegistry(), R.RefResults(), R.RefAudit(), R.RefApprovals(), R.RefHooks()
        self.lim = R.RefLimits(dict(limits) if limits is not None else None)
        self.e = E.Engine(self.ctxp, self.obs, self.reg, self.res, self.aud, self.aud, self.appr, self.hooks, self.lim)
        self.pin = None
        if pack is not False:
            self.doc = pack or SP.pack()
            self.pin = self.e.register_pack('tA', canon.dumps(self.doc))['pin']
            if activate:
                self.activate('tA', self.pin)

    def activate(self, token, pin, ref=None):
        tenant = self.ctxp.sessions[token][0]
        ref = ref or 'APR-%s-%s' % (tenant, pin['pack_hash'][:8])
        self.appr.register(ref, 'TEST-ONLY approver', pin, tenant)
        return self.e.activate_pack(token, pin, ref)

    def submit(self, items, token='tA', pin=None):
        return self.e.submit_observations(token, pin or self.pin, items)

    def signals(self, subject='SYN-ITEM-A', when=EVAL, token='tA'):
        return self.e.get_signals(token, self.pin, subject, when)

    def assess(self, intention='BUY', need_by=None, scenarios=None, when=EVAL, subject='SYN-ITEM-A', token='tA', limits=None, pin=None):
        return self.e.assess_timing(token, pin or self.pin, subject, intention, {'need_by': need_by} if need_by else {}, scenarios or [], when, limits)

    def events(self, tenant='T-A'):
        return [e['event'] for e in self.aud.chains.get(tenant, [])]


def ob(as_of, mantissa=None, exponent=-2, **kw):
    """A level observation of SYN-ITEM-A from SYN-SRC-1, HISTORICAL_MOVEMENT / INDEX, in SYN-MARKET-1 and SYN-UNIT (TEST-ONLY)."""
    o = {'subject_id': 'SYN-ITEM-A', 'source_id': 'SYN-SRC-1', 'licence_ref': 'SYN-LIC-1', 'market': 'SYN-MARKET-1', 'unit': 'SYN-UNIT',
         'observation_class': 'HISTORICAL_MOVEMENT', 'value_basis': 'INDEX', 'as_of': as_of, 'retrieved_at': kw.pop('retrieved_at', as_of)}
    if mantissa is not None:
        o['value'] = {'mantissa': mantissa, 'exponent': exponent}
    o.update(kw)
    return o


def ev(as_of, label, **kw):
    o = ob(as_of, **kw)
    o['event_label'] = label
    return o


def rate(as_of, mantissa, **kw):
    return ob(as_of, mantissa, -4, subject_id='SYN-RATE-1', unit='SYN-RATE-UNIT', observation_class='CURRENT_REFERENCE', **kw)


def series(points, **kw):
    """[(as_of, mantissa)] -> observations."""
    return [ob(d, m, **kw) for d, m in points]


def pack_with(**changes):
    """A deep copy of the synthetic pack with top-level sections replaced."""
    doc = copy.deepcopy(SP.pack())
    doc.update(copy.deepcopy(changes))
    return doc


def signal_cfg(doc, signal_id):
    return [s for s in doc['signals'] if s['signal_id'] == signal_id][0]


def rule(rid, outcome, preds, basis='OBSERVED_EVIDENCE_ONLY', intention='BUY', owner=None, assumption=None):
    r = {'rule_id': rid, 'intention': intention, 'outcome': outcome, 'rationale_code': 'TEST-ONLY-' + rid, 'basis_class': basis, 'predicates': preds}
    if basis == 'OWNER_ASSUMPTION' or owner or assumption:
        r['owner_ref'] = owner if owner is not None else 'TEST-ONLY owner'
        r['assumption'] = assumption if assumption is not None else 'TEST-ONLY assumption for ' + rid
    return r


def p_sig(typ='LEVEL_MOVEMENT', direction=None, cls=None, negate=False):
    return {'p': 'SIGNAL_PRESENT', 'type': typ, 'evidence_class': cls, 'direction': direction, 'negate': negate}


def p_na(typ='LEVEL_MOVEMENT', reason=None, negate=False):
    return {'p': 'SIGNAL_NOT_ASSESSED', 'type': typ, 'reason': reason, 'negate': negate}


def p_need(cmp, param, negate=False):
    return {'p': 'CONSTRAINT_COMPARE', 'constraint': 'days_to_need_by', 'comparison': cmp, 'param': param, 'negate': negate}


def p_gap(reason, negate=False):
    return {'p': 'GAP_PRESENT', 'reason': reason, 'negate': negate}


P_QUAL = {'p': 'QUALIFIED', 'negate': False}
P_ALWAYS = {'p': 'QUALIFIED', 'negate': True}            # true when the evidence is not qualified
P_ABSENT = {'p': 'CONSTRAINT_ABSENT', 'constraint': 'days_to_need_by', 'negate': False}


def scenario(sid='SYN-SC-1', label='SYN-LABEL', **kw):
    s = {'scenario_id': sid, 'label': label, 'owner_ref': 'TEST-ONLY owner', 'basis_statement': 'TEST-ONLY assumed level for a test',
         'assumed_level': {'mantissa': 12000, 'exponent': -2}, 'unit': 'SYN-UNIT'}
    s.update(kw)
    return s


UP = [('2026-07-15', 10000), ('2026-08-15', 10500), ('2026-09-15', 11000)]
DOWN = [('2026-07-15', 11000), ('2026-08-15', 10500), ('2026-09-15', 10000)]
FLAT = [('2026-07-15', 10000), ('2026-08-15', 10100), ('2026-09-15', 10200)]
