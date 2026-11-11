import unittest
from . import _path                                          # noqa: F401
from .helpers import make_env, login
from apg import source_authority as SA, tenancy
from apg.values import Known, Unknown, NO_DATA, AMBIGUOUS


def rule(**kw):
    d = dict(entity_kind='ap_invoice', field='ex_gst_cents', authoritative_source='accounting', permitted_secondary=('pm-system',), nature='source_owned',
             on_secondary_disagreement='quarantine', conflict_resolver_role='finance_reviewer', required_approvals=1, effective_from='2025-01-01', effective_to=None,
             owner='finance-owner', evidence_basis='SYNTHETIC test rule - not a real authority decision')
    d.update(kw); return SA.AuthorityRule(**d)


def reg(rules=None, version='R1', proposer='prop', approvals=None, supersedes=None):
    ap = (SA.Approval('alice', 'authority_owner', 'human', '2026-10-01'),) if approvals is None else approvals
    return SA.AuthorityRegister(version, tuple(rules if rules is not None else [rule()]), proposer, ap, supersedes)


def ob(source, v, ref='r', rev=None, ts='2026-10-01T00:00:00Z', **kw):
    return SA.Observation(source, v, ref, ts, rev, **kw)


def res(register, obs, field='ex_gst_cents', kind='ap_invoice', as_of='2026-09-30'):
    return SA.resolve_field(register, 'INV-1', kind, field, obs, as_of)


class RegisterApproval(unittest.TestCase):
    def test_no_register_or_unapproved_register_gives_pending_never_a_value(self):
        for r in (None, reg(approvals=()), reg(approvals=(SA.Approval('prop', 'authority_owner', 'human', 'd'),)),
                  reg(approvals=(SA.Approval('ai-bot', 'authority_owner', 'ai', 'd'),)), reg(approvals=(SA.Approval('alice', 'viewer', 'human', 'd'),))):
            x = res(r, [ob('accounting', 100)])
            self.assertEqual(x.outcome, SA.PENDING); self.assertFalse(x.authoritative); self.assertEqual(x.reasons, ('NO_APPROVED_REGISTER',))
            self.assertIsInstance(x.value, Unknown)

    def test_no_rule_for_field_goes_to_reconciliation_and_shows_candidates(self):
        x = res(reg(), [ob('accounting', 100), ob('pm-system', 100)], field='gst_cents')
        self.assertEqual(x.outcome, SA.PENDING); self.assertEqual(x.reasons, ('NO_AUTHORITY_RULE',)); self.assertFalse(x.authoritative)
        self.assertEqual(len(x.candidates), 2)

    def test_rule_outside_effective_period_does_not_apply(self):
        r = reg([rule(effective_from='2026-10-01')])
        self.assertEqual(res(r, [ob('accounting', 1)], as_of='2026-09-30').reasons, ('NO_AUTHORITY_RULE',))
        self.assertEqual(res(r, [ob('accounting', 1)], as_of='2026-10-01').outcome, SA.ACCEPTED)

    def test_bad_as_of_fails_safe(self):
        for a in (None, '', '2026-9-30', '2026-09-30\n', '２026-09-30', 20260930):
            self.assertEqual(res(reg(), [ob('accounting', 1)], as_of=a).outcome, SA.PENDING, repr(a))

    def test_overlapping_rules_rejected(self):
        with self.assertRaises(SA.AuthorityError):
            reg([rule(), rule(authoritative_source='procurement')])
        reg([rule(effective_to='2025-12-31'), rule(authoritative_source='procurement', effective_from='2026-01-01')])

    def test_rule_validation(self):
        for kw in ({'nature': 'x'}, {'on_secondary_disagreement': 'newest'}, {'required_approvals': 0}, {'required_approvals': True}, {'effective_from': '2026-1-1'},
                   {'effective_to': '2024-01-01'}, {'permitted_secondary': ('accounting',)}, {'owner': ' '}, {'permitted_secondary': ['pm-system']}):
            with self.assertRaises(SA.AuthorityError, msg=str(kw)):
                rule(**kw)

    def test_history_is_versioned_and_never_replaced(self):
        h = SA.RegisterHistory(); h.add(reg(version='R1'))
        with self.assertRaises(SA.AuthorityError): h.add(reg(version='R1', supersedes='R1'))
        with self.assertRaises(SA.AuthorityError): h.add(reg(version='R2', supersedes=None))
        h.add(reg(version='R2', supersedes='R1', rules=[rule(authoritative_source='procurement')]))
        self.assertEqual(h.versions(), ('R1', 'R2')); self.assertEqual(h.get('R1').rules[0].authoritative_source, 'accounting')
        x = SA.resolve_field(h.get('R1'), 'INV-1', 'ap_invoice', 'ex_gst_cents', [ob('accounting', 5)], '2026-09-30')
        self.assertEqual(x.register_version, 'R1')


class Resolution(unittest.TestCase):
    def test_authoritative_value_accepted(self):
        x = res(reg(), [ob('accounting', 1000)])
        self.assertEqual((x.outcome, x.value, x.authoritative, x.sources_used), (SA.ACCEPTED, Known(1000), True, ('accounting',)))

    def test_secondary_agreeing_is_fine_disagreeing_is_quarantined(self):
        self.assertEqual(res(reg(), [ob('accounting', 1000), ob('pm-system', 1000)]).outcome, SA.ACCEPTED)
        x = res(reg(), [ob('accounting', 1000), ob('pm-system', 1900)])
        self.assertEqual(x.outcome, SA.QUARANTINED); self.assertFalse(x.authoritative); self.assertIsInstance(x.value, Unknown)
        self.assertEqual(x.reasons, ('SECONDARY_DISAGREES:pm-system',))

    def test_disagreement_policy_warning_mode_keeps_authoritative_value_with_warning(self):
        x = res(reg([rule(on_secondary_disagreement='authoritative_wins_with_warning')]), [ob('accounting', 1000), ob('pm-system', 1900)])
        self.assertEqual((x.outcome, x.value.cents), (SA.ACCEPTED_W, 1000)); self.assertTrue(x.warnings)

    def test_secondary_alone_is_never_authoritative(self):
        x = res(reg(), [ob('pm-system', 1000)])
        self.assertEqual((x.outcome, x.authoritative, x.reasons), (SA.PENDING, False, ('AUTHORITATIVE_SOURCE_ABSENT',)))

    def test_unpermitted_source_is_ignored_with_warning_never_used(self):
        x = res(reg(), [ob('random-connector', 5)])
        self.assertEqual(x.outcome, SA.PENDING); self.assertIn('SOURCE_NOT_PERMITTED:random-connector', x.warnings)
        y = res(reg(), [ob('accounting', 7), ob('random-connector', 5)])
        self.assertEqual((y.outcome, y.value.cents), (SA.ACCEPTED_W, 7))

    def test_newest_timestamp_never_decides(self):
        x = res(reg(), [ob('accounting', 100, rev=2, ts='2026-01-01T00:00:00Z'), ob('accounting', 999, rev=1, ts='2026-09-01T00:00:00Z')])
        self.assertEqual(x.value.cents, 100)          # higher revision wins even though its timestamp is older

    def test_same_revision_different_values_is_conflict(self):
        x = res(reg(), [ob('accounting', 100, rev=2), ob('accounting', 101, rev=2)])
        self.assertEqual((x.outcome, x.reasons), (SA.QUARANTINED, ('CONFLICT_SAME_REVISION',)))

    def test_unknown_revision_order_with_different_values_is_conflict_whatever_the_timestamps(self):
        x = res(reg(), [ob('accounting', 100, ts='2020-01-01T00:00:00Z'), ob('accounting', 101, ts='2026-09-30T00:00:00Z')])
        self.assertEqual((x.outcome, x.reasons), (SA.QUARANTINED, ('AMBIGUOUS_REVISION',)))
        z = res(reg(), [ob('accounting', 100, rev=1), ob('accounting', 101)])
        self.assertEqual(z.outcome, SA.QUARANTINED)

    def test_duplicate_delivery_same_value_is_not_a_conflict(self):
        x = res(reg(), [ob('accounting', 100, ref='a'), ob('accounting', 100, ref='b', ts='2026-10-02T00:00:00Z')])
        self.assertEqual((x.outcome, x.value.cents), (SA.ACCEPTED, 100))

    def test_cancelled_observation_ignored(self):
        x = res(reg(), [ob('accounting', 100, rev=1), ob('accounting', 999, rev=2, cancelled=True)])
        self.assertEqual(x.value.cents, 100)

    def test_bad_revision_numbers_quarantine(self):
        for rv in ('2', 1.5, True):
            self.assertEqual(res(reg(), [ob('accounting', 1, rev=rv)]).outcome, SA.QUARANTINED, repr(rv))

    def test_unknown_authoritative_value_is_pending_with_reason(self):
        x = res(reg(), [ob('accounting', Unknown(NO_DATA, 'blank in export'))])
        self.assertEqual((x.outcome, x.reasons), (SA.PENDING, ('AUTHORITATIVE_VALUE_UNKNOWN:no_data',)))
        y = res(reg(), [ob('accounting', '12.50')]);  self.assertEqual(y.reasons, ('AUTHORITATIVE_VALUE_UNKNOWN:invalid',))

    def test_ai_extracted_value_needs_human_verification(self):
        x = res(reg(), [ob('accounting', 100, origin='ai_extracted')])
        self.assertEqual((x.outcome, x.reasons), (SA.PENDING, ('AWAITING_HUMAN_VERIFICATION',)))
        self.assertEqual(res(reg(), [ob('accounting', 100, origin='ai_extracted', human_verified=True)]).outcome, SA.ACCEPTED)

    def test_human_approved_and_provisional_natures(self):
        r = reg([rule(nature='human_approved')])
        self.assertEqual(res(r, [ob('accounting', 5)]).reasons, ('AWAITING_HUMAN_APPROVAL',))
        self.assertEqual(res(r, [ob('accounting', 5, approved_by_role='finance_reviewer')]).outcome, SA.ACCEPTED)
        p = res(reg([rule(nature='provisional')]), [ob('accounting', 5)])
        self.assertFalse(p.authoritative)

    def test_record_status_is_the_worst_field(self):
        a = res(reg(), [ob('accounting', 1)]); q = res(reg(), [ob('accounting', 1), ob('pm-system', 2)])
        self.assertEqual(SA.record_status([a]), SA.ACCEPTED); self.assertEqual(SA.record_status([a, q]), SA.QUARANTINED)
        self.assertEqual(SA.record_status([a, res(reg(), [], field='gst_cents')]), SA.PENDING)


class Views(unittest.TestCase):
    def test_conflicting_record_is_excluded_from_authoritative_total_but_listed(self):
        rows = [('I1', SA.ACCEPTED, 1000, ()), ('I2', SA.QUARANTINED, Unknown('conflicted'), ('SECONDARY_DISAGREES:pm-system',)), ('I3', SA.ACCEPTED, 500, ())]
        t = SA.authoritative_total(rows, 'R1')
        self.assertEqual((t.cents, t.complete, t.included), (1500, False, ('I1', 'I3')))
        self.assertEqual(t.excluded[0][:2], ('I2', SA.QUARANTINED))

    def test_known_amount_on_unaccepted_record_is_still_excluded(self):
        t = SA.authoritative_total([('I1', SA.PENDING, 700, ()), ('I2', SA.QUARANTINED, 800, ())])
        self.assertEqual((t.cents, t.complete, len(t.excluded)), (0, False, 2))

    def test_accepted_record_with_unknown_amount_is_excluded_not_zero(self):
        t = SA.authoritative_total([('I1', SA.ACCEPTED, Unknown(NO_DATA), ()), ('I2', SA.ACCEPTED, 5, ())])
        self.assertEqual((t.cents, t.complete), (5, False)); self.assertTrue(t.excluded[0][2][0].startswith('AMOUNT_UNKNOWN'))

    def test_views_cannot_be_mixed(self):
        a = SA.authoritative_total([('I1', SA.ACCEPTED, 100, ())]); p = SA.provisional_total([('I2', SA.QUARANTINED, 900)], '2026-09-30')
        for f in (lambda: a + p, lambda: p + a, lambda: a + 1, lambda: 1 + p, lambda: p + p):
            with self.assertRaises(TypeError): f()
        self.assertTrue(p.label.startswith('PROVISIONAL')); self.assertEqual(p.cents, 900); self.assertEqual(p.unverified[0][0], 'I2')

    def test_provisional_total_never_includes_authoritative_records(self):
        p = SA.provisional_total([('I1', SA.ACCEPTED, 100), ('I2', SA.PENDING, 40), ('I3', SA.QUARANTINED, Unknown('conflicted'))], '2026-09-30')
        self.assertEqual(p.cents, 40); self.assertEqual([u[0] for u in p.unverified], ['I2', 'I3'])

    def test_compare_views_labels_both(self):
        c = SA.compare_views(SA.authoritative_total([('I1', SA.ACCEPTED, 100, ())]), SA.provisional_total([('I2', SA.PENDING, 40)], 'x'))
        self.assertEqual((c['authoritative_cents'], c['provisional_only_cents']), (100, 40))
        with self.assertRaises(TypeError): SA.compare_views(1, 2)


class Quarantine(unittest.TestCase):
    def setUp(self):
        self.env, _ = make_env()
        self.owner = login(self.env, 'tokO', 'tenant-A', 'olive', ('finance_reviewer',))
        self.owner2 = login(self.env, 'tokO2', 'tenant-A', 'otto', ('finance_reviewer',))
        self.ai = login(self.env, 'tokAI', 'tenant-A', 'bot', ('finance_reviewer',), 'ai')
        self.other = login(self.env, 'tokX', 'tenant-A', 'xena', ('viewer',))
        self.b = login(self.env, 'tokB', 'tenant-B', 'bob', ('finance_reviewer',))
        self.q = SA.QuarantineQueue(tenancy.ScopedStore(self.env.store, self.env.audit, self.owner))
        self.qb = SA.QuarantineQueue(tenancy.ScopedStore(self.env.store, self.env.audit, self.b))
        self.r = res(reg(), [ob('accounting', 1000), ob('pm-system', 1900)])

    def hold(self, approvals=1):
        return self.q.hold('INV-1', self.r, 'finance_reviewer', approvals, observations=[{'source': 'accounting', 'value': 1000}, {'source': 'pm-system', 'value': 1900}])

    def as_q(self, ctx):
        return SA.QuarantineQueue(tenancy.ScopedStore(self.env.store, self.env.audit, ctx))

    def test_held_item_is_visible_and_keeps_evidence(self):
        self.hold(); items = self.q.open_items()
        self.assertEqual(len(items), 1); self.assertEqual(items[0].payload['evidence'][1]['value'], 1900); self.assertEqual(items[0].payload['outcome'], SA.QUARANTINED)

    def test_other_tenant_sees_nothing(self):
        self.hold(); self.assertEqual(self.qb.open_items(), ())

    def test_wrong_role_ai_and_blank_note_refused_and_audited(self):
        self.hold()
        for ctx, note in ((self.other, 'ok'), (self.ai, 'ok'), (self.owner, ''), (self.owner, '  ')):
            with self.assertRaises(SA.AuthorityError, msg=str((ctx.user_id, note))):
                self.as_q(ctx).dispose(ctx, 'INV-1', 'accept', note)
        self.assertEqual(self.q.s.get('quarantine', 'INV-1').payload['status'], 'held')
        self.assertTrue(any(e.event_type == 'quarantine.refused' for e in self.env.audit.read(self.owner)))

    def test_accept_promotes_once_and_is_idempotent_with_history_kept(self):
        self.hold(); a = self.q.dispose(self.owner, 'INV-1', 'accept', 'accounting confirmed by bank statement')
        self.assertEqual(a.payload['status'], 'promoted')
        again = self.q.dispose(self.owner2, 'INV-1', 'accept', 'second click')
        self.assertEqual(again.revision, a.revision)
        h = self.q.s.history('quarantine', 'INV-1'); self.assertEqual([x.payload['status'] for x in h], ['held', 'promoted'])
        self.assertEqual(h[0].payload['evidence'], h[1].payload['evidence'])

    def test_two_approvals_needed_distinct_people_agreeing(self):
        self.hold(approvals=2)
        a = self.q.dispose(self.owner, 'INV-1', 'accept', 'first'); self.assertEqual(a.payload['status'], 'held')
        with self.assertRaises(SA.AuthorityError): self.q.dispose(self.owner, 'INV-1', 'accept', 'same person again')
        with self.assertRaises(SA.AuthorityError): self.q.dispose(self.owner2, 'INV-1', 'correct', 'different action', corrected_cents=1500)
        b = self.q.dispose(self.owner2, 'INV-1', 'accept', 'second'); self.assertEqual(b.payload['status'], 'promoted')

    def test_correction_needs_whole_cents_and_agreeing_values(self):
        self.hold(approvals=2)
        for bad in (None, 12.5, True, '1500'):
            with self.assertRaises(SA.AuthorityError): self.q.dispose(self.owner, 'INV-1', 'correct', 'fix', corrected_cents=bad)
        self.q.dispose(self.owner, 'INV-1', 'correct', 'fix', corrected_cents=1500)
        with self.assertRaises(SA.AuthorityError): self.q.dispose(self.owner2, 'INV-1', 'correct', 'fix', corrected_cents=1600)

    def test_reject_and_retain(self):
        self.hold(); r = self.q.dispose(self.owner, 'INV-1', 'retain', 'need the bank statement')
        self.assertEqual(r.payload['status'], 'retained'); self.assertEqual(len(self.q.open_items()), 1)
        r2 = self.q.dispose(self.owner, 'INV-1', 'reject', 'duplicate of INV-0'); self.assertEqual(r2.payload['status'], 'rejected'); self.assertEqual(self.q.open_items(), ())

    def test_unknown_action_and_missing_item(self):
        self.hold()
        with self.assertRaises(SA.AuthorityError): self.q.dispose(self.owner, 'INV-1', 'delete', 'x')
        with self.assertRaises(SA.AuthorityError): self.q.dispose(self.owner, 'NOPE', 'accept', 'x')


if __name__ == '__main__':
    unittest.main()


class MutationGapFixes(unittest.TestCase):
    """Cases added after the first mutation run showed these behaviours were not pinned by any test."""
    def test_a_secondary_value_that_is_LOWER_also_counts_as_disagreement(self):
        for sec in (1500, 500):
            x = res(reg(), [ob('accounting', 1000), ob('pm-system', sec)]); self.assertEqual((x.outcome, x.authoritative), (SA.QUARANTINED, False), sec)
        self.assertEqual(res(reg(), [ob('accounting', 1000), ob('pm-system', 1000)]).outcome, SA.ACCEPTED)

    def test_a_provisional_field_makes_the_whole_record_pending(self):
        r = reg([rule(field='ex_gst_cents', nature='provisional'), rule(field='gst_cents')])
        a = SA.resolve_field(r, 'I', 'ap_invoice', 'ex_gst_cents', [ob('accounting', 100)], '2026-09-30'); b = SA.resolve_field(r, 'I', 'ap_invoice', 'gst_cents', [ob('accounting', 10)], '2026-09-30')
        self.assertEqual(b.outcome, SA.ACCEPTED); self.assertFalse(a.authoritative); self.assertEqual(SA.record_status([a, b]), SA.PENDING)

    def test_rule_effective_period_is_inclusive_at_both_ends(self):
        r = reg([rule(effective_from='2026-01-01', effective_to='2026-06-30')])
        for d, ok in (('2025-12-31', False), ('2026-01-01', True), ('2026-06-30', True), ('2026-07-01', False)):
            self.assertEqual(res(r, [ob('accounting', 1)], as_of=d).outcome == SA.ACCEPTED, ok, d)

    def test_approvers_must_agree_on_what_to_do(self):
        env = make_env()[0]; owner = login(env, 'o1', 'tenant-A', 'olga', ('finance_reviewer',)); two = login(env, 'o2', 'tenant-A', 'omar', ('finance_reviewer',))
        q = SA.QuarantineQueue(tenancy.ScopedStore(env.store, env.audit, owner)); x = res(reg(), [ob('accounting', 1000), ob('pm-system', 1900)])
        q.hold('INV-9', x, 'finance_reviewer', 2); q.dispose(owner, 'INV-9', 'accept', 'looks right')
        with self.assertRaises(SA.AuthorityError): q.dispose(two, 'INV-9', 'correct', 'no, it is 1900', corrected_cents=1900)
        with self.assertRaises(SA.AuthorityError): q.dispose(two, 'INV-9', 'merge', 'merge instead')
        self.assertEqual(q.s.get('quarantine', 'INV-9').payload['status'], 'held')
