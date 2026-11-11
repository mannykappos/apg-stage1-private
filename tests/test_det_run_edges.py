"""Edge cases of the detection run found by the mutation pass: which records a project run and a tenant run pin, how a malformed rule result is refused, and what a reviewer's
check of a stored run reports.  Every value is synthetic."""
import copy
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import det_world, inv, notice, quote
from apg import repro
from apg.det import detect as D


def breach_world():
    m = det_world()
    m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
    m.reconcile()
    return m


class TestWhatARunPins(unittest.TestCase):
    def test_a_project_run_pins_its_own_notices_and_not_another_projects(self):
        m = det_world()
        m.projects(['PRJ-002', 'P2', '1', '2026-01-01', '2027-01-01'])
        m.notices(notice('N-1', project='PRJ-001'), notice('N-2', project='PRJ-002'))
        m.reconcile()
        pins = m.detect('PRJ-001')['params']['pins']
        self.assertIn('notice/N-1', pins)
        self.assertNotIn('notice/N-2', pins)
        self.assertIn('notice/N-2', m.detect('PRJ-002')['params']['pins'])

    def test_a_tenant_run_with_an_unreconciled_quote_runs_and_pins_no_reconciliation_state_for_it(self):
        m = det_world()
        m.quotes(quote('Q-1'))
        pins = m.tdetect()['params']['pins']                                              # not reconciled: there is no state to pin
        self.assertIn('supplier_quote/Q-1', pins)
        self.assertFalse([k for k in pins if k.startswith('recon_state/supplier_quote/')])
        m.reconcile()
        self.assertIn('recon_state/supplier_quote/Q-1', m.tdetect()['params']['pins'])

    def test_a_tenant_run_pins_no_reconciliation_state_for_a_kind_that_has_none(self):
        m = det_world()
        m.compliance(['SUP-001', 'licence', '2027-12-31'])
        m.reconcile()
        pins = m.tdetect()['params']['pins']
        self.assertIn('supplier/SUP-001', pins)
        self.assertFalse([k for k in pins if k.startswith('recon_state/supplier/') or k.startswith('recon_state/compliance/')])


class TestMalformedRuleResults(unittest.TestCase):
    PARAMS = {'as_of': '2026-09-30', 'project': 'PRJ-001', 'det_policy': None}

    def good_run(self, rid):
        return {'rule': rid, 'version': 1, 'status': 'evaluated', 'evaluated': 0, 'signals': 0, 'silent': 0, 'not_assessed': [], 'notes': [], 'missing_parameters': [], 'decision': ''}

    def one_signal(self):
        m = breach_world()
        return m.res()['signals'][0]

    def test_a_status_that_is_not_a_run_state_is_refused_even_when_the_rule_name_is_right(self):
        def rule(F, dp, project, as_of):
            r = self.good_run('X1')
            r['status'] = 'skipped'
            return [], r
        with self.assertRaisesRegex(ValueError, 'malformed: X1'):
            D._run({}, self.PARAMS, (('X1', rule),), {})

    def test_a_run_record_under_the_wrong_rule_name_is_refused_even_when_the_status_is_right(self):
        def rule(F, dp, project, as_of):
            return [], self.good_run('X2')
        with self.assertRaisesRegex(ValueError, 'malformed: X1'):
            D._run({}, self.PARAMS, (('X1', rule),), {})

    def test_a_well_formed_result_passes(self):
        def rule(F, dp, project, as_of):
            return [], self.good_run('X1')
        out = D._run({}, self.PARAMS, (('X1', rule),), {})
        self.assertEqual((out['counts'], out['rule_runs']['X1']['status']), ({'signals': 0, 'rules': 1, 'rules_not_run': 0}, 'evaluated'))

    def test_two_signals_with_one_identity_are_refused(self):
        sig = self.one_signal()

        def a(F, dp, project, as_of):
            return [copy.deepcopy(sig)], self.good_run('X1')

        def b(F, dp, project, as_of):
            return [copy.deepcopy(sig)], self.good_run('X2')
        with self.assertRaisesRegex(ValueError, 'two signals share one identity'):
            D._run({}, self.PARAMS, (('X1', a), ('X2', b)), {})

    def test_validate_result_refuses_a_bad_status_a_wrong_rule_name_and_a_signal_from_a_rule_that_did_not_run(self):
        res = breach_world().res()
        self.assertTrue(D.validate_result(res))
        bad = copy.deepcopy(res)
        bad['rule_runs']['R01']['status'] = 'skipped'
        with self.assertRaisesRegex(ValueError, 'rule run record'):
            D.validate_result(bad)
        bad = copy.deepcopy(res)
        bad['rule_runs']['R01']['rule'] = 'R02'
        with self.assertRaisesRegex(ValueError, 'rule run record'):
            D.validate_result(bad)
        bad = copy.deepcopy(res)
        bad['rule_runs']['R02']['status'] = 'disabled'
        bad['rule_runs']['R02']['signals'] = 1
        with self.assertRaisesRegex(ValueError, 'did not run'):
            D.validate_result(bad)
        bad = copy.deepcopy(res)
        bad['signals'].append(copy.deepcopy(bad['signals'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate identity'):
            D.validate_result(bad)


class TestCheckOfAStoredRun(unittest.TestCase):
    def stored(self, change):
        m = breach_world()
        rec = m.detect()
        bad = copy.deepcopy(m.s.get(repro.KIND, rec['run_key']).payload)
        change(bad)
        m.s.put(repro.KIND, 'tampered-1', bad)
        return m, rec

    def test_an_untouched_run_has_consistent_pins(self):
        m = breach_world()
        rec = m.detect()
        self.assertTrue(D.check_record(m.s, m.detreg, rec['run_key'])['pins_consistent'])

    def test_a_pin_claimed_at_another_revision_than_the_one_read_is_inconsistent(self):
        def change(p):
            k = sorted(p['params']['pins'])[0]
            p['params']['pins'][k] += 1
        m, _ = self.stored(change)
        self.assertFalse(D.check_record(m.s, m.detreg, 'tampered-1')['pins_consistent'])

    def test_a_pin_claimed_for_a_record_that_was_never_read_is_inconsistent(self):
        m, _ = self.stored(lambda p: p['params']['pins'].update({'notice/N-GHOST': 1}))
        self.assertFalse(D.check_record(m.s, m.detreg, 'tampered-1')['pins_consistent'])

    def test_a_run_that_claims_no_pins_is_not_called_inconsistent(self):
        m, _ = self.stored(lambda p: p['params'].pop('pins'))
        self.assertTrue(D.check_record(m.s, m.detreg, 'tampered-1')['pins_consistent'])


if __name__ == '__main__':
    unittest.main()
