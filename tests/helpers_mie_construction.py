"""The construction pack on Builder Zero (outside the core's neutrality scan: field words are allowed here).  EVERY OWNER INPUT BELOW IS A TEST-ONLY VALUE chosen by the
implementer so that the pack can run in tests; none is guidance and none is a product-owner decision.  The values the tenant's M6 procurement policy already holds (the watched
materials and the buy-timing freshness limits) are taken from that policy through construction.owner_inputs_from_m6_policy, not chosen here.

golden_run(root) builds the Builder Zero world through the real M3 to M6 intake (apg.ingest.golden_m3._world and apg.mkt.demo_mkt.load_mkt_all), maps the stored market and
FX records to observation messages (mie.adapters.m6.records_to_messages with apg.fin.intake.usable), registers, approves and activates the completed pack for the tenant through
APG's own verified context (mie.adapters.apg_host.ApgContext), and assesses MAT-STEEL to BUY with the demand's required date."""
from . import _path                                         # noqa: F401
from apg.fin import intake as FI
from apg.ingest.golden_m3 import _world
from apg.mkt import demo_mkt as DM
from mie.adapters import apg_host, m6 as M6A
from mie.core import canon, engine as E, reference as R
from mie.packs import construction as C

EVALUATION_DATE = '2026-09-30'
NEED_BY = '2026-12-01'                                       # the Builder Zero MAT-STEEL demand's required_on_site date
OWNER = 'TEST-ONLY owner (not a product-owner decision)'
LIMITS = {'max_pack_bytes': 200000, 'max_rules': 50, 'max_string_length': 200, 'max_batch_items': 500, 'max_abs_exponent': 30, 'max_mantissa_digits': 30,
          'max_series_points': 5000, 'max_audit_page': 500, 'max_scenarios': 10}           # TEST-ONLY host limits
FX_UNITS = {'AUD/USD': ('USD-per-AUD', 'FX-REFERENCE')}


def test_only_inputs(policy):
    """The owner inputs: the M6 policy part, then TEST-ONLY values for everything M6 does not hold."""
    inputs = C.owner_inputs_from_m6_policy(policy, OWNER)
    inputs.update(
        units=[{'unit_id': 'index_points_x100', 'decimal_scale': 0, 'value_domain': 'POSITIVE'},
               {'unit_id': 'AUD', 'decimal_scale': 2, 'value_domain': 'NON_NEGATIVE'},
               {'unit_id': 'USD', 'decimal_scale': 2, 'value_domain': 'NON_NEGATIVE'},
               {'unit_id': 'USD-per-AUD', 'decimal_scale': 4, 'value_domain': 'POSITIVE'}],
        markets=['AU-national', 'FX-REFERENCE'],
        sources=[{'source_id': 'SYNTHETIC-INDEX', 'licence_ref': 'TEST-ONLY-LIC-INDEX', 'value_bases': ['INDEX']},
                 {'source_id': 'APG-FX-RATES', 'licence_ref': 'TEST-ONLY-LIC-FX', 'value_bases': ['INDEX']}],
        licences=[{'licence_id': 'TEST-ONLY-LIC-INDEX', 'status': 'LICENSED', 'valid_from': '2026-01-01', 'valid_to': '2026-12-31', 'terms_ref': 'TEST-ONLY terms'},
                  {'licence_id': 'TEST-ONLY-LIC-FX', 'status': 'LICENSED', 'valid_from': '2026-01-01', 'valid_to': '2026-12-31', 'terms_ref': 'TEST-ONLY terms'}],
        conversions=[{'pair': 'AUD/USD', 'rate_unit': 'USD-per-AUD', 'market': 'FX-REFERENCE', 'from_unit': 'AUD', 'to_unit': 'USD'}],
        movement={'window_days': 90, 'min_points': 2, 'movement_basis': 'RELATIVE', 'threshold': {'num': 1, 'den': 20}},
        conversion_movement={'window_days': 30, 'min_points': 2, 'movement_basis': 'RELATIVE', 'threshold': {'num': 1, 'den': 50}},
        parameters=[{'param_id': 'APG-P-ORDER-LEAD-DAYS', 'value': 90, 'owner_ref': OWNER}],
        required_evidence=[{'evidence_id': 'APG-REQ-INDEX', 'observation_class': 'HISTORICAL_MOVEMENT', 'value_basis': 'INDEX', 'market': 'AU-national',
                            'unit': 'index_points_x100'}],
        decision_table=[
            {'rule_id': 'APG-R-WITHIN-LEAD', 'intention': 'BUY', 'outcome': 'ACT_NOW', 'rationale_code': 'NEED-BY-WITHIN-ORDER-LEAD', 'basis_class': 'OWNER_ASSUMPTION',
             'owner_ref': OWNER, 'assumption': 'TEST-ONLY: ordering is due once the required date is within the order lead time',
             'predicates': [{'p': 'CONSTRAINT_COMPARE', 'constraint': 'days_to_need_by', 'comparison': 'LE', 'param': 'APG-P-ORDER-LEAD-DAYS', 'negate': False}]},
            {'rule_id': 'APG-R-BEYOND-LEAD', 'intention': 'BUY', 'outcome': 'WAIT', 'rationale_code': 'NEED-BY-BEYOND-ORDER-LEAD', 'basis_class': 'OWNER_ASSUMPTION',
             'owner_ref': OWNER, 'assumption': 'TEST-ONLY: ordering can wait while the required date is beyond the order lead time',
             'predicates': [{'p': 'CONSTRAINT_COMPARE', 'constraint': 'days_to_need_by', 'comparison': 'GT', 'param': 'APG-P-ORDER-LEAD-DAYS', 'negate': False}]},
            {'rule_id': 'APG-R-NO-DATE', 'intention': 'BUY', 'outcome': 'NOT_ASSESSED', 'rationale_code': 'NO-REQUIRED-DATE', 'basis_class': 'OBSERVED_EVIDENCE_ONLY',
             'predicates': [{'p': 'CONSTRAINT_ABSENT', 'constraint': 'days_to_need_by', 'negate': False}]}])
    return inputs


def completed_pack(version='0.2.0-TEST-ONLY'):
    return C.complete(C.base_pack(), test_only_inputs(DM.demo_mkt_policy()), version)


class ApgWorld:
    """Builder Zero (tenant zero_one) through the real M3 to M6 intake, and an engine whose tenant context is APG's verified context."""
    def __init__(self, root):
        self.clock, self.prov, self.store, self.audit, who = _world()
        self.s1 = who('t1', 'zero_one', 'ann')
        self.s2 = who('t2', 'zero_two', 'bob')
        DM.load_mkt_all(root, self.s1, self.clock, 'zero_one')
        DM.load_mkt_all(root, self.s2, self.clock, 'zero_two')
        self.ctx1, self.ctx2 = self.prov.resolve('t1'), self.prov.resolve('t2')
        self.obs, self.reg, self.res, self.aud, self.appr, self.hooks = R.RefObservations(), R.RefRegistry(), R.RefResults(), R.RefAudit(), R.RefApprovals(), R.RefHooks()
        self.e = E.Engine(apg_host.ApgContext(self.prov), self.obs, self.reg, self.res, self.aud, self.aud, self.appr, self.hooks, R.RefLimits(dict(LIMITS)))

    def install(self, doc, ctx=None, tenant='zero_one'):
        ctx = ctx or self.ctx1
        pin = self.e.register_pack(ctx, canon.dumps(doc))['pin']
        self.appr.register('TEST-ONLY-APPROVAL-%s' % tenant, 'TEST-ONLY approver', pin, tenant)
        self.e.activate_pack(ctx, pin, 'TEST-ONLY-APPROVAL-%s' % tenant)
        return pin

    def messages(self, doc, scoped=None):
        return M6A.records_to_messages(scoped or self.s1, doc, C.M6_KIND_MAP, FX_UNITS, FI.usable)


def golden_run(root):
    """-> a canonical summary of the Builder Zero run (the golden answer recorded in regression/mie1/golden_mie1.json)."""
    w = ApgWorld(root)
    doc = completed_pack()
    pin = w.install(doc)
    msgs, skipped = w.messages(doc)
    sub = w.e.submit_observations(w.ctx1, pin, msgs)
    steel = w.e.assess_timing(w.ctx1, pin, 'MAT-STEEL', 'BUY', {'need_by': NEED_BY}, [], EVALUATION_DATE)
    board = w.e.assess_timing(w.ctx1, pin, 'MAT-PBOARD', 'BUY', {'need_by': '2026-10-15'}, [], EVALUATION_DATE)
    undated = w.e.assess_timing(w.ctx1, pin, 'MAT-STEEL', 'BUY', {}, [], EVALUATION_DATE)
    replay = w.e.replay_result(w.ctx1, steel['result_id'])
    sig = w.e.get_signals(w.ctx1, pin, 'MAT-STEEL', EVALUATION_DATE)

    def short(r):
        return {'result_id': r['result_id'], 'outcome': r['outcome'], 'outcome_reason': r['outcome_reason'], 'rule': (r['rule_fired'] or {}).get('rule_id'),
                'influence': r['signal_influence']['class'], 'qualification': r['qualification']['status'], 'qualification_reasons': r['qualification']['reasons'],
                'days_to_need_by': r['days_to_need_by'], 'gaps': [g.get('reason') for g in r['gaps']],
                'signals': sorted([s['signal_id'], s['status'], s.get('direction'), s.get('reason')] for s in r['signals'])}
    return {'pack_pin': pin, 'messages': len(msgs), 'skipped': sorted(set(s['why'] for s in skipped)), 'skipped_count': len(skipped), 'receipt_counts': sub['counts'],
            'MAT-STEEL': short(steel), 'MAT-PBOARD': short(board), 'MAT-STEEL_no_date': short(undated),
            'replay': {'identical': replay['identical'], 'same_digest': replay['stored_digest'] == replay['replayed_digest']},
            'signals_MAT-STEEL': sorted([s['signal_id'], s['status'], s.get('direction'), s.get('reason')] for s in sig['signals'])}
