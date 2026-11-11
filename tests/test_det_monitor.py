import unittest
from . import _path                                         # noqa: F401
from .helpers_det import AS_OF, det_world, inv, var, comp
from apg.det import findings as FD, monitor as MON


def args(m, as_of=AS_OF):
    return (m.svc, m.clock, m.detreg), as_of, m.policy['version'], m.dp['version']


def sweep(m, as_of=AS_OF, dp=None):
    (s, c, r), a, fp, dpv = args(m, as_of)
    return MON.sweep(s, c, r, a, fp, dp or dpv)


class TestSweep(unittest.TestCase):
    def test_a_sweep_runs_every_project_and_the_tenant_and_logs_it(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        rec = sweep(m)
        self.assertEqual((rec['status'], rec['trigger'], rec['scopes']), ('ok', 'sweep', ['PRJ-001', 'tenant']))
        self.assertEqual(rec['failures'], [])
        self.assertEqual(len(FD.all_findings(m.svc)), 1)
        self.assertEqual(rec['results'][0]['created'], 1)

    def test_a_time_driven_condition_is_found_only_when_a_later_sweep_runs(self):
        m = det_world()
        m.variations(var('VAR-2', raised='2026-08-15', status='submitted', value='3500000'))
        m.reconcile()
        sweep(m)
        self.assertEqual(FD.all_findings(m.svc), [])                                         # 46 days old: inside the 60 day period
        m.clock.advance(86400)
        sweep(m, '2026-10-20')
        (f,) = FD.all_findings(m.svc)
        self.assertEqual((f['rule_id'], f['subject'], f['signal']['extra']['age_days']), ('DET-R04', 'VAR-2', 66))

    def test_a_repeat_sweep_with_no_change_creates_and_sends_nothing_new(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        sweep(m)
        FD.flush_notifications(m.svc, m.clock, m.notifier)
        m.clock.advance(86400)
        rec = sweep(m, '2026-10-01')
        self.assertEqual((rec['results'][0]['created'], rec['results'][0]['updated']), (0, 0))
        self.assertEqual(FD.flush_notifications(m.svc, m.clock, m.notifier), {'sent': 0, 'duplicate': 0, 'failed': 0})

    def test_the_same_sweep_twice_is_a_replay_and_changes_nothing(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        sweep(m)
        before = FD.all_findings(m.svc)
        rec = sweep(m)
        self.assertTrue(all(x['replay'] for x in rec['results']))
        self.assertEqual(FD.all_findings(m.svc), before)


class TestEvents(unittest.TestCase):
    def test_a_new_invoice_triggers_only_its_project_and_the_tenant(self):
        m = det_world()
        m.projects(['PRJ-002', 'P2', '1', '2026-01-01', '2027-01-01'])
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        (s, c, r), a, fp, dpv = args(m)
        self.assertEqual(MON.scopes_for_event(m.s, {'kind': 'ap_invoice', 'key': 'INV-1'}), (['PRJ-001'], False))
        rec = MON.on_event(s, c, r, {'kind': 'ap_invoice', 'key': 'INV-1'}, a, fp, dpv)
        self.assertEqual(rec['scopes'], ['PRJ-001'])
        self.assertEqual(rec['trigger'], 'event:ap_invoice/INV-1')

    def test_a_compliance_record_triggers_the_tenant_scope_only(self):
        m = det_world()
        m.compliance(comp('SUP-001', 'insurance', '2026-09-01'))
        m.reconcile()
        keys = [r.key for r in m.s.query('compliance')]
        self.assertEqual(MON.scopes_for_event(m.s, {'kind': 'compliance', 'key': keys[0]}), ([], True))
        (s, c, r), a, fp, dpv = args(m)
        rec = MON.on_event(s, c, r, {'kind': 'compliance', 'key': keys[0]}, a, fp, dpv)
        self.assertEqual(rec['scopes'], ['tenant'])
        self.assertEqual([f['rule_id'] for f in FD.all_findings(m.svc)], ['DET-R06'])

    def test_a_policy_change_re_evaluates_everything(self):
        m = det_world()
        m.rules(R01={'tolerance_bps': 100})
        self.assertEqual(MON.scopes_for_event(m.s, {'kind': 'det_policy', 'key': m.dp['version']}), (['PRJ-001'], True))

    def test_an_event_about_a_record_that_cannot_be_found_affects_everything(self):
        m = det_world()
        self.assertEqual(MON.scopes_for_event(m.s, {'kind': 'ap_invoice', 'key': 'NOPE'}), (['PRJ-001'], True))

    def test_the_same_event_twice_is_safe(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        (s, c, r), a, fp, dpv = args(m)
        ev = {'kind': 'ap_invoice', 'key': 'INV-1'}
        MON.on_event(s, c, r, ev, a, fp, dpv)
        before = FD.all_findings(m.svc)
        rec = MON.on_event(s, c, r, ev, a, fp, dpv)
        self.assertTrue(all(x['replay'] for x in rec['results']))
        self.assertEqual(FD.all_findings(m.svc), before)


class TestFailureVisibility(unittest.TestCase):
    def test_a_failed_scope_is_logged_with_a_code_and_the_other_scopes_still_run(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        rec = sweep(m, dp='D-none')                                                          # a policy version that does not exist
        self.assertEqual(rec['status'], 'failed')
        self.assertEqual({f['scope'] for f in rec['failures']}, {'PRJ-001', 'tenant'})
        self.assertTrue(all(f['code'] for f in rec['failures']))
        self.assertEqual(FD.all_findings(m.svc), [])

    def test_health_reports_the_failing_scopes_the_statement_and_clears_after_a_good_run(self):
        m = det_world()
        sweep(m, dp='D-none')
        h = MON.health(m.s, AS_OF)
        self.assertEqual(sorted(h['scopes_currently_failing']), ['PRJ-001', 'tenant'])
        self.assertIsNone(h['last_successful_sweep_as_of'])
        self.assertEqual(h['statement'], MON.STATEMENT)
        self.assertIn('absence of an alert is not evidence', h['statement'])
        sweep(m)
        h = MON.health(m.s, '2026-10-05')
        self.assertEqual((h['scopes_currently_failing'], h['last_successful_sweep_as_of'], h['days_since_successful_sweep']), ({}, AS_OF, 5))

    def test_health_lists_rules_that_did_not_run_and_undelivered_notifications(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        m.rules(R03=None)
        sweep(m)
        h = MON.health(m.s, AS_OF)
        self.assertEqual(h['rules_not_run_in_latest_run']['PRJ-001'], ['R03'])
        self.assertEqual(h['undelivered_notifications'], 1)
        m.notifier._contract_set_transport_failure(True)
        FD.flush_notifications(m.svc, m.clock, m.notifier)
        self.assertEqual(MON.health(m.s, AS_OF)['undelivered_notifications'], 1)
        m.notifier._contract_set_transport_failure(False)
        FD.flush_notifications(m.svc, m.clock, m.notifier)
        self.assertEqual(MON.health(m.s, AS_OF)['undelivered_notifications'], 0)

    def test_a_partial_failure_is_marked_partial(self):
        m = det_world()
        (s, c, r), a, fp, dpv = args(m)
        rec = MON.run_scopes(s, c, r, ['PRJ-001', 'tenant'], a, fp, dpv, 'manual')
        self.assertEqual(rec['status'], 'ok')
        rec = MON.run_scopes(s, c, r, ['PRJ-NOPE', 'tenant'], a, fp, dpv, 'manual')
        self.assertEqual(rec['status'], 'partial')
        self.assertEqual([(f['scope'], f['code']) for f in rec['failures']], [('PRJ-NOPE', 'PROJECT_UNKNOWN')])
        self.assertEqual([x['scope'] for x in rec['results']], ['tenant'])
