"""M7: boundaries, displayed values, concurrency and record details (added after the builder's first mutation run over apg/rec showed which of them no test pinned down)."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import COMPLETE_ALT, RecWorld
from apg import canon, repro, tenancy
from apg.ports import ConflictError
from apg.rec import engine as E, inputs as IN, lifecycle as L, policy as RP, verify as V


class Racing(tenancy.ScopedStore):
    """A scoped store whose next write of one kind meets a concurrent change (ConflictError)."""
    def __init__(self, base, kind):
        super().__init__(base._store, base._audit, base.ctx)
        self.kind = kind

    def put(self, kind, key, payload, expected_revision=None):
        if kind == self.kind:
            raise ConflictError('someone else wrote first')
        return super().put(kind, key, payload, expected_revision)

    def atomic(self, ops):
        if any(o[0] == self.kind for o in ops):
            raise ConflictError('someone else wrote first')
        return super().atomic(ops)


class TestTimingBoundaries(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def e(self, **kw):
        f = self.w.finding(**kw)
        return self.w.entry(self.w.run(ingest=False), f)

    def test_urgency_classes_at_their_edges(self):
        cases = {'2026-09-29': 'overdue', '2026-09-30': 'soon', '2026-10-14': 'soon', '2026-10-15': 'later'}
        for date, cls in cases.items():
            with self.subTest(date=date):
                self.assertEqual(self.e(date=date)['dimensions']['urgency']['class'], cls)

    def test_window_states_at_their_edges(self):
        cases = {'2026-10-14': 'closing', '2026-10-15': 'open'}
        for date, st in cases.items():
            with self.subTest(date=date):
                w = self.e(date=date, time_sensitive=True)['dimensions']['time_sensitivity']
                self.assertEqual((w['state'], w['window_date'], w['basis']), (st, date, 'fixture date'))

    def test_a_finding_without_a_window_says_so(self):
        d = self.e()['dimensions']
        self.assertEqual(d['time_sensitivity'], {'state': 'none', 'window_date': None, 'days_left': None, 'basis': 'no decision window in the evidence'})
        self.assertEqual((d['urgency']['class'], d['urgency']['basis'], d['urgency']['days_left']), ('not_dated', 'no date in the evidence', None))
        self.assertEqual(self.e(date='2026-10-20', time_sensitive=True)['dimensions']['time_sensitivity']['days_left'], 20)

    def test_without_a_due_soon_value_only_overdue_today_and_later_are_told_apart(self):
        self.w.set_policy(eligibility={'stale_after_days': 30, 'min_strength_for_action': 'moderate'})
        self.assertEqual(self.e(date='2026-09-30')['dimensions']['urgency']['class'], 'soon')
        self.assertEqual(self.e(date='2026-10-01')['dimensions']['urgency']['class'], 'later')
        w = self.e(date='2026-10-01', time_sensitive=True)['dimensions']['time_sensitivity']
        self.assertEqual(w['state'], 'open')

    def test_stale_evidence_ranks_after_current_evidence_on_confidence(self):
        self.w.set_policy(rank_order=['confidence'])
        stale = self.w.finding(as_of='2026-08-01')
        fresh = self.w.finding()
        run = self.w.run(ingest=False)
        self.assertLess(self.w.entry(run, fresh)['rank'], self.w.entry(run, stale)['rank'])


class TestDisplayedValues(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def test_money_text(self):
        self.assertEqual([E.money(c) for c in (0, 1, -1, 12345, None)], ['$0.00', '$0.01', '-$0.01', '$123.45', 'unquantified'])

    def test_magnitude_and_benefit_fields(self):
        q = self.w.finding(gross=5000000)
        u = self.w.finding(gross=None)
        IN.set_inputs(self.w.owner, self.w.clock, self.w.rid(q), expected_benefit={'cents': 7, 'basis': 'the owner said so'}, incremental_costs=[{'component': 'c', 'cents': 1, 'basis': 'x'}])
        run = self.w.run(ingest=False)
        dq, du = self.w.entry(run, q)['dimensions'], self.w.entry(run, u)['dimensions']
        self.assertEqual((dq['magnitude']['label'], dq['magnitude']['basis']), ('record', 'synthetic test amount'))
        self.assertEqual((du['magnitude']['label'], du['magnitude']['basis']), ('none', 'no defensible amount in the fixture'))
        self.assertEqual(dq['expected_benefit'], {'status': 'estimated', 'cents': 7, 'basis': 'the owner said so'})
        self.assertEqual(du['expected_benefit'], {'status': 'not_estimated', 'cents': None, 'basis': ''})
        self.assertEqual(dq['implementation_cost']['note'], 'entered by olly')
        self.assertEqual(du['net_benefit']['formula'], 'needs the expected benefit of the action and every incremental cost')

    def test_the_shown_value_of_each_rank_factor(self):
        self.w.set_policy(rank_order=['magnitude', 'net_benefit'])
        q = self.w.finding(gross=5000000)
        u = self.w.finding(gross=None)
        IN.set_inputs(self.w.owner, self.w.clock, self.w.rid(q), expected_benefit={'cents': 700, 'basis': 'b'}, incremental_costs=[{'component': 'c', 'cents': 200, 'basis': 'x'}])
        run = self.w.run(ingest=False)
        self.assertEqual([x['shown'] for x in self.w.entry(run, q)['rank_factors']], ['potential gross $50000.00', 'estimated net benefit $5.00'])
        self.assertEqual([x['shown'] for x in self.w.entry(run, u)['rank_factors']], ['magnitude unquantified (placed after quantified ones)', 'net benefit unquantified (placed after quantified ones)'])

    def test_actionability_reasons(self):
        inv = self.w.finding(status='detected')
        act = self.w.finding(gross=500000)
        self.w.ready(act)
        run = self.w.run()
        self.assertEqual(self.w.entry(run, inv)['dimensions']['actionability'], {'actionable_now': False, 'why': ['evidence or review needed first']})
        self.assertEqual(self.w.entry(run, act)['dimensions']['actionability'], {'actionable_now': True, 'why': ['nothing blocks it']})

    def test_an_action_that_is_not_ready_lists_its_blockers_as_the_reasons(self):
        f = self.w.finding()
        e = self.w.entry(self.w.run(ingest=False), f)
        self.assertEqual(e['route'], 'action')
        self.assertEqual(e['dimensions']['actionability']['why'], e['constraints']['blocked_by'])
        self.assertIn('incremental costs not estimated', e['dimensions']['actionability']['why'])

    def test_dependencies_name_pending_reviews_and_overlaps_only(self):
        a = self.w.finding(family='quality_defects', gross=300000, overlap='g')
        b = self.w.finding(family='quality_defects', gross=200000, overlap='g')
        IN.record_review(self.w.creview, self.w.clock, self.w.rid(b), 'quality', 'cleared', 'ok')
        run = self.w.run(ingest=False)
        self.assertEqual(self.w.entry(run, a)['dimensions']['dependencies'], ['approval by a person with the role project_manager', 'quality review', 'overlaps with %s (amounts not added)' % b])
        self.assertEqual(self.w.entry(run, b)['dimensions']['dependencies'], ['approval by a person with the role project_manager', 'overlaps with %s (amounts not added)' % a])

    def test_unquantified_overlap_note_and_assessed_items(self):
        u = self.w.finding(gross=None, missing=('a', 'b'))
        IN.record_evidence_assessment(self.w.creview, self.w.clock, self.w.rid(u), 'a', False, 'not needed')
        e = self.w.entry(self.w.run(ingest=False), u)
        self.assertEqual(e['overlap']['note'], 'unquantified: listed, not counted as zero')
        self.assertEqual(e['dimensions']['confidence']['assessed_not_critical'], [{'item': 'a', 'by': 'cora', 'rationale': 'not needed'}])
        self.assertEqual(e['dimensions']['confidence']['critical_missing'], ['b'])

    def test_the_explanation_text_in_full_for_a_known_case(self):
        f = self.w.finding(family='quality_defects', gross=500000, missing=('the inspection report', 'the photo'))
        IN.record_evidence_assessment(self.w.creview, self.w.clock, self.w.rid(f), 'the photo', False, 'the report suffices')
        x = self.w.entry(self.w.run(ingest=False), f)['explanation']
        self.assertEqual(x['evidence_and_uncertainty'], '1 stored record(s); evidence strong; amount $5000.00 (authoritative); missing and treated as critical: the inspection report; '
                                                         'missing, assessed not critical: the photo (by cora: the report suffices); alternative explanations: none recorded; freshness: current.')
        self.assertEqual(x['benefits_costs_tradeoffs'], 'Potential gross $5000.00; expected benefit unquantified; incremental costs not estimated; estimated net unquantified '
                                                         '(needs the expected benefit of the action and every incremental cost). Risks and constraints: none recorded.')
        self.assertEqual(x['required_approval'], 'Approval by a person with the role project_manager; quality review pending. APG records the decision; it does not carry out any action.')
        g = self.w.finding()
        y = self.w.entry(self.w.run(ingest=False), g)['explanation']
        self.assertIn('no mandatory review applies to this kind of finding', y['required_approval'])
        self.assertIn('missing and treated as critical: none; missing, assessed not critical: none', y['evidence_and_uncertainty'])

    def test_a_resolved_finding_names_who_resolved_it(self):
        f = self.w.finding(status='resolved')
        e = self.w.entry(self.w.run(ingest=False), f)
        self.assertEqual(e['eligibility']['detail'], ['the finding was resolved by fred; a person records the closure of the recommendation'])

    def test_the_policy_must_be_pinned(self):
        r = self.w.run(ingest=False)
        rec = self.w.s.get(repro.KIND, r['run_key']).payload
        inputs = {f"{i['kind']}/{i['key']}": self.w.s.get(i['kind'], i['key'], i['revision']).payload for i in rec['inputs']}
        with self.assertRaises(E.EngineError) as cm:
            E.compute(inputs, dict(rec['params'], policy='NOT-PINNED'))
        self.assertEqual(cm.exception.code, 'POLICY_NOT_PINNED')

    def test_the_materiality_amount_itself_needs_an_alternative(self):
        f = self.w.finding(gross=1000000)
        self.w.ready(f, alts=[])
        self.assertTrue(self.w.entry(self.w.run(), f)['scenarios']['required'])
        g = self.w.finding(gross=999999)
        self.w.ready(g, alts=[])
        self.assertFalse(self.w.entry(self.w.run(), g)['scenarios']['required'])


class TestGateMessages(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def test_an_incomplete_extra_alternative_also_blocks_a_material_decision(self):
        f = self.w.finding(gross=5000000)
        good = dict(COMPLETE_ALT, baseline_ref='repro_record/' + self.w.baseline['run_key'])
        rid = self.w.ready(f, alts=[good, {'name': 'half-thought-through'}])
        e = self.w.entry(self.w.run(), f)
        self.assertFalse(e['scenarios']['complete'])
        with self.assertRaises(L.RecError) as cm:
            L.submit(self.w.owner2, self.w.clock, rid)
        self.assertIn('scenario comparison incomplete', str(cm.exception))

    def test_an_investigation_lists_every_reason_it_cannot_be_submitted(self):
        f = self.w.finding(status='detected')
        rid = self.w.rid(f)
        self.w.run()
        with self.assertRaises(L.RecError) as cm:
            L.submit(self.w.owner2, self.w.clock, rid)
        self.assertIn('not action', str(cm.exception))
        self.assertIn('incremental costs not estimated', str(cm.exception))
        self.assertIn('the kind of action is not stated', str(cm.exception))

    def test_a_partial_token_is_refused_by_the_lowest_level_call_too(self):
        f = self.w.finding()
        rid = self.w.ready(f)
        self.w.run()
        L.submit(self.w.owner2, self.w.clock, rid)
        t = L.approval_token(L.get(self.w.s, rid))
        for v, d, s in ((t['version'], None, t['submission']), (t['version'], t['digest'], None), (None, t['digest'], t['submission'])):
            with self.assertRaises(L.RecError) as cm:
                L.transition(self.w.pm, self.w.clock, rid, 'approved', rationale='x', approving_version=v, approving_digest=d, approving_submission=s)
            self.assertEqual(cm.exception.code, 'APPROVAL_TOKEN_REQUIRED')


class TestRecordDetails(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()
        self.f = self.w.finding(gross=500000)
        self.rid = self.w.ready(self.f)
        self.w.run()

    def test_history_entries_are_numbered_attributed_and_detailed(self):
        L.transition(self.w.owner2, self.w.clock, self.rid, 'awaiting_evidence', rationale='need dockets')
        h = L.get(self.w.s, self.rid)['history']
        self.assertEqual([x['seq'] for x in h], list(range(1, len(h) + 1)))
        self.assertEqual((h[0]['actor_kind'], h[-1]['actor_kind'], h[-1]['actor']), ('service', 'human', 'opal'))
        self.assertEqual(h[-1]['detail'], {'rationale': 'need dockets'})

    def test_the_token_of_an_unsubmitted_recommendation_names_no_submission(self):
        r = L.get(self.w.s, self.rid)
        self.assertIsNone(L.approval_token(r)['submission'])
        self.assertIsNone(L.submission_ref(r))
        self.assertFalse(L.submission_current(r))

    def test_a_withdrawn_submission_is_not_current(self):
        L.submit(self.w.owner2, self.w.clock, self.rid)
        self.assertTrue(L.submission_current(L.get(self.w.s, self.rid)))
        L.transition(self.w.owner2, self.w.clock, self.rid, 'generated', rationale='withdrawn')
        r = L.get(self.w.s, self.rid)
        self.assertFalse(L.submission_current(r))
        self.assertEqual(r['submission_history'][-1]['ended_because'], 'withdrawn by the owner')

    def test_listing_by_status(self):
        g = self.w.finding()
        self.w.run()
        L.transition(self.w.owner2, self.w.clock, self.w.rid(g), 'deferred', rationale='later', until='2026-12-01')
        self.assertEqual([r['rec_id'] for r in L.all_recs(self.w.s, 'deferred')], [self.w.rid(g)])
        self.assertNotIn(self.w.rid(g), [r['rec_id'] for r in L.all_recs(self.w.s, 'generated')])
        self.assertEqual(len(L.all_recs(self.w.s)), 2)

    def test_a_finding_excluded_before_it_had_a_recommendation_creates_nothing(self):
        d = self.w.finding(status='dismissed')
        s = L.ingest_run(self.w.svc, self.w.clock, self.w.reg, E.run(self.w.s, self.w.reg, self.w.clock, '2026-10-01', self.w.policy['version'])['run_key'])
        self.assertEqual(s['finding_excluded'], [])
        with self.assertRaises(L.RecError):
            L.get(self.w.s, self.w.rid(d))

    def test_an_approval_ended_while_in_progress_is_recorded_once(self):
        L.submit(self.w.owner2, self.w.clock, self.rid)
        t = L.approval_token(L.get(self.w.s, self.rid))
        L.approve(self.w.pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'ok')
        L.transition(self.w.owner2, self.w.clock, self.rid, 'in_progress')
        for i, day in enumerate(('2026-10-01', '2026-10-02')):
            IN.set_inputs(self.w.owner, self.w.clock, self.rid, risks=['risk %d' % i])
            self.w.run(as_of=day)
        h = L.get(self.w.s, self.rid)['history']
        self.assertEqual(sum(1 for x in h if x['event'] == 'approval_ended_while_in_progress'), 1)

    def test_a_run_that_is_not_a_recommendation_run_is_refused_with_its_reason(self):
        from apg.fin import calc_records as FC
        both = E.registry(FC.fin_registry())                               # the forecast run replays cleanly here, so only the formula check refuses it
        with self.assertRaises(L.RecError) as cm:
            L.ingest_run(self.w.svc, self.w.clock, both, self.w.baseline['run_key'])
        self.assertEqual(cm.exception.code, 'RUN_DOES_NOT_VERIFY')
        self.assertIn('pins or formula', str(cm.exception))
        ev = [e for e in self.w.w.audit.read(self.w.s.ctx) if e.event_type == 'rec.ingest_refused']
        self.assertIn('pins or formula', ev[-1].reason)

    def test_concurrent_changes_are_refused_not_lost(self):
        racing = Racing(self.w.owner2, L.KIND)
        with self.assertRaises(L.RecError) as cm:
            L.transition(racing, self.w.clock, self.rid, 'awaiting_evidence', rationale='x')
        self.assertEqual(cm.exception.code, 'CONCURRENT_CHANGE')
        run = E.run(self.w.s, self.w.reg, self.w.clock, '2026-10-01', self.w.policy['version'])
        with self.assertRaises(L.RecError) as cm:
            L.ingest_run(Racing(self.w.svc, L.KIND), self.w.clock, self.w.reg, run['run_key'])
        self.assertEqual(cm.exception.code, 'CONCURRENT_CHANGE')
        for fn in (lambda s: IN.set_inputs(s, self.w.clock, self.rid, risks=['x']), lambda s: IN.record_review(s, self.w.clock, self.rid, 'quality', 'cleared', 'x'),
                   lambda s: IN.record_evidence_assessment(s, self.w.clock, self.rid, 'x', False, 'y')):
            who = self.w.owner if fn.__code__.co_names.count('set_inputs') else self.w.creview
            with self.assertRaises(IN.InputError) as cm:
                fn(Racing(who, IN.KIND))
            self.assertEqual(cm.exception.code, 'CONCURRENT_CHANGE')


class TestInputDetails(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()
        self.f = self.w.finding()
        self.rid = self.w.rid(self.f)

    def test_the_inputs_history_names_the_fields_written(self):
        IN.set_inputs(self.w.owner, self.w.clock, self.rid, action_kind='internal_review', risks=['r'])
        inp = IN.get(self.w.s, self.rid)
        self.assertEqual(inp['history'][-1]['fields'], ['action_kind', 'risks'])
        ev = [e for e in self.w.w.audit.read(self.w.s.ctx) if e.event_type == 'rec.inputs_written']
        self.assertEqual(ev[-1].detail, {'fields': ['action_kind', 'risks']})

    def test_reviews_of_different_types_are_kept_and_a_repeat_replaces_only_its_own_type(self):
        IN.record_review(self.w.creview, self.w.clock, self.rid, 'quality', 'cleared', 'q1')
        IN.record_review(self.w.creview, self.w.clock, self.rid, 'legal', 'cleared', 'l1')
        IN.record_review(self.w.creview, self.w.clock, self.rid, 'quality', 'not_cleared', 'q2')
        rv = {r['type']: r['rationale'] for r in IN.get(self.w.s, self.rid)['reviews']}
        self.assertEqual(rv, {'quality': 'q2', 'legal': 'l1'})

    def test_a_repeated_assessment_records_what_it_replaces(self):
        IN.record_evidence_assessment(self.w.creview, self.w.clock, self.rid, 'x', False, 'first')
        IN.record_evidence_assessment(self.w.creview, self.w.clock, self.rid, 'y', False, 'other')
        IN.record_evidence_assessment(self.w.creview, self.w.clock, self.rid, 'x', True, 'second')
        h = [x for x in IN.get(self.w.s, self.rid)['history'] if x['event'] == 'evidence_assessed']
        self.assertIsNone(h[0]['replaces'])
        self.assertEqual(h[2]['replaces']['rationale'], 'first')


class TestPolicyDetails(unittest.TestCase):
    def test_malformed_approvals_are_refused(self):
        for ap in ([{'approver': 'x'}], ['x'], [{'approver': 'a', 'role': 'r', 'kind': 'human', 'date': ''}], {'approver': 'a'}):
            with self.subTest(ap=ap):
                self.assertTrue(RP.validate_policy({'version': 'v', 'proposer': 'p', 'approvals': ap}))

    def test_storing_an_invalid_policy_is_refused(self):
        w = RecWorld()
        with self.assertRaises(RP.RecPolicyError):
            RP.store_policy(w.s, {'version': 'v', 'proposer': 'p', 'approvals': [], 'rank_order': ['score']})

    def test_approvals_of_a_stored_version_can_only_be_appended(self):
        w = RecWorld()
        RP.store_policy(w.polprop, RP.new_policy('V-A', 'paula'))
        RP.approve_policy(w.polown, w.clock, 'V-A', 'ok')
        rhea = w.w.who('rhea', 'zero_one', 'rhea', (RP.POLICY_ROLE,), ttl=10 ** 8)
        RP.approve_policy(rhea, w.clock, 'V-A', 'ok too')
        self.assertEqual([a['approver'] for a in w.s.get(RP.POLICY_KIND, 'V-A').payload['approvals']], ['quentin', 'rhea'])
        with self.assertRaises(RP.RecPolicyError):
            RP.store_policy(w.polprop, dict(RP.new_policy('V-A', 'paula'), approvals=[{'approver': 'rhea', 'role': RP.POLICY_ROLE, 'kind': 'human', 'date': '2026-10-19'}]))


class TestVerifyDetails(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def test_an_unknown_recommendation(self):
        with self.assertRaises(V.VerifyError) as cm:
            V.verify(self.w.verifier, self.w.clock, self.w.reg, self.w.m.reg, 'REC-nope', self.w.baseline['run_key'], 1, self.w.offsets(), 'x', self.w.policy)
        self.assertEqual(cm.exception.code, 'RECOMMENDATION_UNKNOWN')

    def test_details_of_a_verification(self):
        f, g = self.w.finding(gross=500000), self.w.finding(gross=600000)
        self.w.to_completed(f)
        self.w.to_completed(g, benefit=700000)
        o = self.w.offsets(financing={'cents': 0, 'basis': 'paid from cash on hand'})
        a = V.verify(self.w.verifier, self.w.clock, self.w.reg, self.w.m.reg, self.w.rid(f), self.w.baseline['run_key'], 10, o, 'x', self.w.policy)
        b = V.verify(self.w.verifier, self.w.clock, self.w.reg, self.w.m.reg, self.w.rid(g), self.w.baseline['run_key'], 10, o, 'x', self.w.policy)
        self.assertEqual((a['outcome']['verification'], b['outcome']['verification']), (self.w.rid(f) + '|1', self.w.rid(g) + '|1'))
        pinned = {(i['kind'], i['key']) for i in self.w.s.get(repro.KIND, a['outcome']['run_key']).payload['inputs']}
        self.assertIn(('ap_invoice', 'INV-1'), pinned)
        self.assertIn((repro.KIND, self.w.baseline['run_key']), pinned)
        self.assertEqual(a['outcome']['result']['offsetting_costs_cents'], 0)

    def test_a_realised_net_of_exactly_zero_is_not_a_benefit(self):
        f = self.w.finding()
        self.w.to_completed(f)
        r = V.verify(self.w.verifier, self.w.clock, self.w.reg, self.w.m.reg, self.w.rid(f), self.w.baseline['run_key'], 5000,
                     self.w.offsets(financing={'cents': 5000, 'basis': 'interest'}), 'x', self.w.policy)
        self.assertEqual((r['outcome']['result']['realised_net_cents'], r['outcome']['result']['label']), (0, 'verified: no realised net benefit'))

    def test_without_an_expected_net_the_variance_is_not_stated(self):
        f = self.w.finding(gross=500000)
        rid = self.w.rid(f)
        IN.set_inputs(self.w.owner, self.w.clock, rid, action_kind='internal_review', incremental_costs=[{'component': 'c', 'cents': 0, 'basis': 'none'}])
        self.w.run()
        L.submit(self.w.owner2, self.w.clock, rid)
        t = L.approval_token(L.get(self.w.s, rid))
        L.approve(self.w.pm, self.w.clock, rid, t['version'], t['digest'], t['submission'], 'ok')
        L.transition(self.w.owner2, self.w.clock, rid, 'in_progress')
        L.transition(self.w.owner2, self.w.clock, rid, 'completed_pending_verification', evidence_refs=[('ap_invoice', 'INV-1', 1)])
        r = V.verify(self.w.verifier, self.w.clock, self.w.reg, self.w.m.reg, rid, self.w.baseline['run_key'], 10, self.w.offsets(), 'x', self.w.policy)
        self.assertEqual((r['outcome']['result']['expected_net_cents'], r['outcome']['result']['variance_cents']), (None, None))

    def test_the_submitter_cannot_verify_even_when_someone_else_carried_it_out(self):
        f = self.w.finding(gross=500000)
        rid = self.w.ready(f)
        self.w.run()
        L.submit(self.w.owner2, self.w.clock, rid)
        t = L.approval_token(L.get(self.w.s, rid))
        L.approve(self.w.pm, self.w.clock, rid, t['version'], t['digest'], t['submission'], 'ok')
        owen = self.w.w.who('owen', 'zero_one', 'owen', (IN.OWNER,), ttl=10 ** 8)
        L.transition(owen, self.w.clock, rid, 'in_progress')
        L.transition(owen, self.w.clock, rid, 'completed_pending_verification', evidence_refs=[('ap_invoice', 'INV-1', 1)])
        opal_v = self.w.w.who('opal-v', 'zero_one', 'opal', (L.VERIFIER,), ttl=10 ** 8)
        with self.assertRaises(V.VerifyError) as cm:
            V.verify(opal_v, self.w.clock, self.w.reg, self.w.m.reg, rid, self.w.baseline['run_key'], 1, self.w.offsets(), 'x', self.w.policy)
        self.assertEqual(cm.exception.code, 'VERIFIER_NOT_INDEPENDENT')

    def test_the_refusal_names_what_is_missing_and_what_is_malformed(self):
        f = self.w.finding()
        self.w.to_completed(f)
        o = self.w.offsets(storage_and_waste={'cents': 1})
        o.pop('financing')
        with self.assertRaises(V.VerifyError) as cm:
            V.verify(self.w.verifier, self.w.clock, self.w.reg, self.w.m.reg, self.w.rid(f), self.w.baseline['run_key'], 1, o, 'x', self.w.policy)
        self.assertIn('missing: financing; malformed: storage_and_waste', str(cm.exception))
        o2 = self.w.offsets()
        o2.pop('financing')
        with self.assertRaises(V.VerifyError) as cm:
            V.verify(self.w.verifier, self.w.clock, self.w.reg, self.w.m.reg, self.w.rid(f), self.w.baseline['run_key'], 1, o2, 'x', self.w.policy)
        self.assertIn('missing: financing; malformed: none', str(cm.exception))

    def test_a_record_with_its_implementation_evidence_removed_cannot_be_verified(self):
        f = self.w.finding()
        r = self.w.to_completed(f)
        rec = self.w.s.get(L.KIND, r['rec_id'])
        p = canon.deep_copy(rec.payload)
        p['implementation']['evidence_refs'] = []
        self.w.s.put(L.KIND, r['rec_id'], p, expected_revision=rec.revision)
        with self.assertRaises(V.VerifyError) as cm:
            V.verify(self.w.verifier, self.w.clock, self.w.reg, self.w.m.reg, r['rec_id'], self.w.baseline['run_key'], 1, self.w.offsets(), 'x', self.w.policy)
        self.assertEqual(cm.exception.code, 'IMPLEMENTATION_EVIDENCE_REQUIRED')

    def test_a_recommendation_that_changes_during_verification_is_not_marked_verified(self):
        f = self.w.finding()
        r = self.w.to_completed(f)
        rid = r['rec_id']
        w = self.w

        class Meddling(tenancy.ScopedStore):
            def put(self, kind, key, payload, expected_revision=None):
                out = super().put(kind, key, payload, expected_revision)
                if kind == V.VKIND:                                         # someone closes the recommendation while the verification is being computed
                    cur = w.s.get(L.KIND, rid)
                    w.s.put(L.KIND, rid, dict(cur.payload, status='closed_without_implementation'), expected_revision=cur.revision)
                return out
        v = Meddling(w.verifier._store, w.verifier._audit, w.verifier.ctx)
        with self.assertRaises(V.VerifyError) as cm:
            V.verify(v, w.clock, w.reg, w.m.reg, rid, w.baseline['run_key'], 1, w.offsets(), 'x', w.policy)
        self.assertEqual(cm.exception.code, 'CONCURRENT_CHANGE')
        self.assertEqual(L.get(w.s, rid)['status'], 'closed_without_implementation')


if __name__ == '__main__':
    unittest.main()
