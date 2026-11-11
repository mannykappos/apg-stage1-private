"""Materiality policy engine.  ALL THRESHOLDS IN THIS FILE ARE ILLUSTRATIVE TEST VALUES, NOT PROPOSED DEFAULTS."""
import hashlib, os, unittest
from unittest import mock
from . import _path                                          # noqa: F401
from apg import materiality as M, materiality_engine as E
from apg.ports import TenantMismatch
from apg.tenancy import ScopedStore
from apg.values import Known, Unknown
from .helpers import make_env, login

POL = {'version': 'T-1', 'rules': {'invoice': {'abs_cents': 500000, 'rel_bps': 100, 'rel_base': 'contract_value'}, 'delay': {'delay_days': 5},
                                    'calc': {'all_records': True}, 'unset_subject': {}},
       'always_material': ['tax'], 'aggregate': True, 'aggregation': {'keys': ['project'], 'window_days': 30}}


def rec(id='r1', amount=1000, subject='invoice', project='P1', date='2026-10-01', **kw):
    r = {'id': id, 'subject': subject, 'amount_cents': amount, 'bases': {'contract_value': 100000000}, 'date': date, 'group': {'project': project}, 'categories': []}
    r.update(kw); return r


class Base(unittest.TestCase):
    def setUp(self):
        self.env, self.clock = make_env()
        self.proposer = self.who('tp', 'ten-a', 'proposer')
        self.owner1 = self.who('to1', 'ten-a', 'owner1', ('materiality_owner',))
        self.owner2 = self.who('to2', 'ten-a', 'owner2', ('materiality_owner',))
        self.reviewer = self.who('tr', 'ten-a', 'reviewer', ('policy_reviewer',))
        self.po = self.who('tpo', 'ten-a', 'emmanuel', ('product_owner',))

    def who(self, token, tenant, user, roles=(), kind='human'):
        return ScopedStore(self.env.store, self.env.audit, login(self.env, token, tenant, user, roles, kind))

    def activate(self, pol=POL):
        E.propose_policy(self.proposer, pol); E.approve_policy(self.owner1, pol['version']); E.approve_policy(self.owner2, pol['version'])
        return E.activate_policy(self.owner1, pol['version'])

    def code(self, fn):
        try:
            fn()
        except E.PolicyError as e:
            return e.code


class ModelIsTheReference(unittest.TestCase):
    def test_package_model_is_byte_identical_to_cr02_reference(self):
        here = os.path.dirname(os.path.abspath(M.__file__)); ref = os.path.join(here, '..', 'reference', 'cr02', 'cr02_materiality_model.py')
        h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
        self.assertEqual(h(M.__file__), h(ref))


class FailSafe(Base):
    def test_no_active_policy_means_material_with_a_visible_reason(self):
        a = E.assess_record(self.proposer, rec(amount=1))
        self.assertEqual((a.material, a.reasons), (True, (E.NO_ACTIVE,)))

    def test_every_decision_starts_open_and_stays_open_through_normal_use(self):
        self.activate(); E.assess_record(self.proposer, rec())
        self.assertEqual(set(E.decision_status(self.po).values()), {'open'}); self.assertEqual(len(E.DECISIONS), 8)

    def test_assessments_name_the_open_decisions_they_lean_on(self):
        self.activate(); a = E.assess_record(self.proposer, rec())
        self.assertEqual(a.open_decisions, tuple(E.decisions_relied_on(POL)))
        self.assertIn('DEC-A1-3', a.open_decisions); self.assertIn('DEC-A1-8', a.open_decisions); self.assertFalse(a.settled)

    def test_unset_rule_and_all_records_are_visibly_different(self):
        self.activate()
        u = E.assess_record(self.proposer, rec(subject='unset_subject')); c = E.assess_record(self.proposer, rec(subject='calc'))
        self.assertEqual((u.material, u.reasons), (True, ('M-THRESHOLD-UNSET',))); self.assertEqual((c.material, c.reasons), (True, ('M-ALL-RECORDS',)))

    def test_unknown_subject_and_always_material_category(self):
        self.activate()
        self.assertEqual(E.assess_record(self.proposer, rec(subject='mystery')).reasons, ('M-UNKNOWN-SUBJECT',))
        self.assertIn('M-ALWAYS', E.assess_record(self.proposer, rec(amount=1, categories=['tax'])).reasons)


class PolicyLifecycle(Base):
    def test_first_activation_is_treated_as_loosening_and_needs_two_humans_including_an_owner(self):
        E.propose_policy(self.proposer, POL)
        self.assertEqual(self.code(lambda: E.activate_policy(self.owner1, 'T-1')), 'C-APPROVAL')
        E.approve_policy(self.owner1, 'T-1'); self.assertEqual(self.code(lambda: E.activate_policy(self.owner1, 'T-1')), 'C-APPROVAL')
        E.approve_policy(self.reviewer, 'T-1'); self.assertEqual(E.activate_policy(self.owner1, 'T-1'), 'mixed')
        self.assertEqual(E.active_policy(self.owner1)[1], 'T-1')

    def test_two_non_owner_reviewers_are_not_enough(self):
        E.propose_policy(self.proposer, POL); r2 = self.who('tr2', 'ten-a', 'reviewer2', ('policy_reviewer',))
        E.approve_policy(self.reviewer, 'T-1'); E.approve_policy(r2, 'T-1')
        self.assertEqual(self.code(lambda: E.activate_policy(self.owner1, 'T-1')), 'C-APPROVAL')

    def test_proposer_cannot_approve_even_with_the_owner_role(self):
        p = self.who('tp2', 'ten-a', 'both', ('materiality_owner',)); E.propose_policy(p, POL)
        self.assertEqual(self.code(lambda: E.approve_policy(p, 'T-1')), 'SELF_APPROVAL')
        self.assertIn('policy.approval_refused', [e.event_type for e in self.env.audit.read(p.ctx)])

    def test_ai_and_roleless_users_cannot_approve(self):
        E.propose_policy(self.proposer, POL)
        ai = self.who('tai', 'ten-a', 'bot', ('materiality_owner',), 'ai'); nobody = self.who('tn', 'ten-a', 'nobody')
        self.assertEqual(self.code(lambda: E.approve_policy(ai, 'T-1')), 'HUMAN_REQUIRED'); self.assertEqual(self.code(lambda: E.approve_policy(nobody, 'T-1')), 'NO_APPROVAL_ROLE')

    def test_ai_may_propose_but_never_alone_activates(self):
        ai = self.who('tai', 'ten-a', 'bot', (), 'ai'); E.propose_policy(ai, POL)
        self.assertEqual(self.code(lambda: E.activate_policy(ai, 'T-1')), 'C-APPROVAL')

    def test_approval_does_not_carry_to_different_content(self):
        E.propose_policy(self.proposer, POL); E.approve_policy(self.owner1, 'T-1'); E.approve_policy(self.owner2, 'T-1')
        forged = dict(POL, rules=dict(POL['rules'], invoice={'abs_cents': 999999999}))
        # overwrite the approval records so they point at content the policy no longer has
        for o in (self.owner1, self.owner2):
            o.put(E.APPROVAL_KIND, f'T-1|{o.ctx.user_id}', {'version': 'T-1', 'policy_digest': 'f' * 64, 'approver': o.ctx.user_id, 'role': 'materiality_owner', 'kind': 'human', 'against': ''})
        self.assertEqual(self.code(lambda: E.activate_policy(self.owner1, 'T-1')), 'C-APPROVAL')

    def test_forged_approval_key_does_not_count(self):
        E.propose_policy(self.proposer, POL); E.approve_policy(self.owner1, 'T-1')
        d = E.POLICY_KIND and self.owner1.get(E.POLICY_KIND, 'T-1').payload['policy_digest']
        self.owner2.put(E.APPROVAL_KIND, 'T-1|someone-else', {'version': 'T-1', 'policy_digest': d, 'approver': 'owner2', 'role': 'materiality_owner', 'kind': 'human', 'against': ''})
        self.assertEqual(self.code(lambda: E.activate_policy(self.owner1, 'T-1')), 'C-APPROVAL')

    def test_versions_are_immutable(self):
        E.propose_policy(self.proposer, POL); E.propose_policy(self.proposer, POL)           # same content: idempotent
        changed = dict(POL, rules=dict(POL['rules'], delay={'delay_days': 9}))
        self.assertEqual(self.code(lambda: E.propose_policy(self.proposer, changed)), 'VERSION_EXISTS')

    def test_invalid_policies_are_refused(self):
        for bad in ({'version': '', 'rules': {}}, {'version': 'v', 'rules': []}, dict(POL, version='V2', rules={'x': {'abs_cents': 1.5}}), dict(POL, version='V3', rules={'x': {'abs_cents': 0}}),
                    dict(POL, version='V4', rules={'x': {'all_records': 'yes'}}), dict(POL, version='V5', aggregation={'keys': ['supplier'], 'window_days': 3})):
            self.assertIn(self.code(lambda b=bad: E.propose_policy(self.proposer, b)), ('POLICY_INVALID', 'RULE_INVALID'), str(bad))

    def test_tightening_needs_one_owner_and_loosening_two(self):
        self.activate()
        tight = dict(POL, version='T-2', rules=dict(POL['rules'], delay={'delay_days': 3}))
        E.propose_policy(self.proposer, tight); E.approve_policy(self.owner1, 'T-2'); self.assertEqual(E.activate_policy(self.owner1, 'T-2'), 'tighten')
        loose = dict(POL, version='T-3', rules=dict(POL['rules'], delay={'delay_days': 30}))
        E.propose_policy(self.proposer, loose); E.approve_policy(self.owner1, 'T-3'); self.assertEqual(self.code(lambda: E.activate_policy(self.owner1, 'T-3')), 'C-APPROVAL')
        E.approve_policy(self.reviewer, 'T-3'); self.assertEqual(E.activate_policy(self.owner1, 'T-3'), 'loosen')

    def test_reactivating_the_active_version_is_refused(self):
        self.activate(); self.assertEqual(self.code(lambda: E.activate_policy(self.owner1, 'T-1')), 'C-NOCHANGE')

    def test_rollback_to_an_older_looser_version_still_needs_loosening_approval(self):
        self.activate(); tight = dict(POL, version='T-2', rules=dict(POL['rules'], delay={'delay_days': 3}))
        E.propose_policy(self.proposer, tight); E.approve_policy(self.owner1, 'T-2'); E.activate_policy(self.owner1, 'T-2')
        self.assertEqual(self.code(lambda: E.activate_policy(self.owner1, 'T-1')), 'C-APPROVAL')

    def test_activation_race_is_detected(self):
        E.propose_policy(self.proposer, POL); E.approve_policy(self.owner1, 'T-1'); E.approve_policy(self.owner2, 'T-1')
        other = dict(POL, version='T-9'); E.propose_policy(self.proposer, other); E.approve_policy(self.owner1, 'T-9'); E.approve_policy(self.owner2, 'T-9')
        real = E.active_policy
        def stale(scoped):
            r = real(scoped)
            E.activate_policy.__globals__['active_policy'] = real
            E.activate_policy(self.owner2, 'T-9')           # someone else activates in between
            return r
        with mock.patch.object(E, 'active_policy', stale):
            with self.assertRaises(E.PolicyError) as c:
                E.activate_policy(self.owner1, 'T-1')
        self.assertEqual(c.exception.code, 'ACTIVATION_RACE'); self.assertEqual(real(self.owner1)[1], 'T-9')

    def test_tampered_stored_policy_is_detected(self):
        self.activate(); self.proposer.put(E.POLICY_KIND, 'T-1', {**self.proposer.get(E.POLICY_KIND, 'T-1').payload, 'policy': dict(POL, rules={'invoice': {'abs_cents': 99999999}})})
        self.assertRaises(E.PolicyError, lambda: E.active_policy(self.owner1)); self.assertEqual(self.code(lambda: E.active_policy(self.owner1)), 'POLICY_TAMPERED')
        self.assertEqual(self.code(lambda: E.assess_record(self.proposer, rec())), 'POLICY_TAMPERED')    # fail closed: no assessment is made on a tampered policy

    def test_tampered_active_pointer_is_detected(self):
        self.activate(); cur = self.owner1.get(E.ACTIVE_KIND, E.ACTIVE_KEY).payload
        self.owner1.put(E.ACTIVE_KIND, E.ACTIVE_KEY, dict(cur, policy_digest='e' * 64))
        self.assertEqual(self.code(lambda: E.active_policy(self.owner1)), 'ACTIVE_POINTER_TAMPERED')

    def test_audit_trail_has_proposal_approvals_and_activation(self):
        self.activate(); types = [e.event_type for e in self.env.audit.read(self.owner1.ctx)]
        for t in ('policy.proposed', 'policy.approved', 'policy.activated'):
            self.assertIn(t, types)


class TenantIsolation(Base):
    def test_another_tenant_has_no_policy_and_cannot_use_or_activate_ours(self):
        self.activate(); b = self.who('tb', 'ten-b', 'bob', ('materiality_owner',))
        self.assertEqual(E.assess_record(b, rec(amount=1)).reasons, (E.NO_ACTIVE,))
        self.assertEqual(self.code(lambda: E.activate_policy(b, 'T-1')), 'POLICY_UNKNOWN'); self.assertEqual(self.code(lambda: E.approve_policy(b, 'T-1')), 'POLICY_UNKNOWN')

    def test_decisions_are_per_tenant(self):
        E.record_decision(self.po, 'DEC-A1-1', 'Accept', 'test'); b = self.who('tb2', 'ten-b', 'bpo', ('product_owner',))
        self.assertEqual(E.decision_status(b)['DEC-A1-1'], 'open'); self.assertEqual(E.decision_status(self.po)['DEC-A1-1'], 'decided')


class Decisions(Base):
    def test_only_a_human_product_owner_can_record_a_decision(self):
        ai_po = self.who('tai', 'ten-a', 'bot', ('product_owner',), 'ai'); svc = self.who('tsv', 'ten-a', 'svc', ('product_owner',), 'service')
        self.assertEqual(self.code(lambda: E.record_decision(ai_po, 'DEC-A1-1', 'Accept', 'x')), 'HUMAN_REQUIRED'); self.assertEqual(self.code(lambda: E.record_decision(svc, 'DEC-A1-1', 'Accept', 'x')), 'HUMAN_REQUIRED')
        self.assertEqual(self.code(lambda: E.record_decision(self.owner1, 'DEC-A1-1', 'Accept', 'x')), 'NOT_PRODUCT_OWNER')
        self.assertEqual(self.code(lambda: E.record_decision(self.po, 'DEC-A1-99', 'Accept', 'x')), 'UNKNOWN_DECISION')
        self.assertEqual(self.code(lambda: E.record_decision(self.po, 'DEC-A1-1', '', 'x')), 'DECISION_INCOMPLETE')
        self.assertEqual(set(E.decision_status(self.po).values()), {'open'})

    def test_recording_a_decision_closes_only_that_decision_and_keeps_history(self):
        self.activate(); E.record_decision(self.po, 'DEC-A1-3', 'Approve all_records for calculations', 'test'); E.record_decision(self.po, 'DEC-A1-3', 'Amend', 'test 2')
        st = E.decision_status(self.po); self.assertEqual([d for d, s in st.items() if s == 'decided'], ['DEC-A1-3']); self.assertEqual(len(self.po.history(E.LEDGER_KIND, 'DEC-A1-3')), 2)
        a = E.assess_record(self.proposer, rec()); self.assertNotIn('DEC-A1-3', a.open_decisions); self.assertIn('DEC-A1-8', a.open_decisions)

    def test_which_decisions_each_kind_of_content_leans_on(self):
        mk = lambda rules, **kw: dict({'version': 'v', 'rules': rules, 'aggregate': True, 'aggregation': {'keys': ['project'], 'window_days': 7}}, **kw)
        cases = [(mk({'a': {}}), ['DEC-A1-1', 'DEC-A1-5', 'DEC-A1-8']), (mk({'a': {'all_records': True}}), ['DEC-A1-3', 'DEC-A1-5', 'DEC-A1-8']),
                 (mk({'a': {'abs_cents': 5}}), ['DEC-A1-5', 'DEC-A1-8']), (mk({'a': {'abs_cents': 5, 'delay_days': 2}}), ['DEC-A1-4', 'DEC-A1-5', 'DEC-A1-8']),
                 (mk({'a': {'abs_cents': 5}}, always_material=['tax']), ['DEC-A1-2', 'DEC-A1-5', 'DEC-A1-8']), (mk({'a': {'abs_cents': 5}}, aggregate=False), ['DEC-A1-5', 'DEC-A1-8']),
                 ({'version': 'v', 'rules': {'a': {'abs_cents': 5}}}, ['DEC-A1-5'])]
        for pol, want in cases:
            self.assertEqual(E.decisions_relied_on(pol), want, str(pol))

    def test_a_policy_with_no_discretionary_content_still_depends_on_the_approval_rule(self):
        self.assertEqual(E.decisions_relied_on({'version': 'v', 'rules': {'x': {'abs_cents': 1}}, 'aggregate': False}), ['DEC-A1-5', 'DEC-A1-8'])
        self.assertEqual(E.decisions_relied_on({'version': 'v', 'rules': {}}), ['DEC-A1-1', 'DEC-A1-5'])
        self.assertEqual(E.decisions_relied_on('garbage'), ['DEC-A1-5'])


class AssessmentBehaviour(Base):
    def setUp(self):
        super().setUp(); self.activate()

    def test_boundaries_follow_the_model(self):
        for amt, mat in ((499999, False), (500000, True), (-500000, True), (0, False)):
            a = E.assess_record(self.proposer, rec(id=f'x{amt}', amount=amt)); self.assertEqual(a.material, mat, amt)

    def test_unknown_amount_is_never_not_material(self):
        for v in (Unknown('no_data'), Unknown('conflicted'), Unknown('stale'), None):
            a = E.assess_record(self.proposer, rec(id=f'u{v}', amount=v)); self.assertEqual((a.material, a.reasons), (True, ('M-AMOUNT-MISSING',)), str(v))

    def test_known_amount_is_used_and_unknown_base_is_flagged(self):
        self.assertFalse(E.assess_record(self.proposer, rec(id='k1', amount=Known(1000))).material)
        a = E.assess_record(self.proposer, rec(id='k2', amount=1000, bases={'contract_value': Unknown('no_data')})); self.assertEqual((a.material, a.reasons), (True, ('M-BASE-INVALID',)))
        a = E.assess_record(self.proposer, rec(id='k3', amount=1000, bases={'contract_value': 0})); self.assertEqual((a.material, a.reasons), (True, ('M-BASE-INVALID',)))

    def test_floats_nan_strings_and_bools_are_material_not_trusted(self):
        for v in (1000.0, float('nan'), '1000', True, [1]):
            a = E.assess_record(self.proposer, rec(id='f', amount=v)); self.assertTrue(a.material, repr(v))
            self.assertNotIn('NM-BELOW', a.reasons)

    def test_unstorable_input_leaves_an_honest_non_replayable_trace(self):
        a = E.assess_record(self.proposer, rec(id='f', amount=1.5)); self.assertEqual(E.verify_assessment(self.proposer, a.key), (False, 'NOT_REPLAYABLE'))
        self.assertIn('unstorable_repr', a.stored['record'])

    def test_splitting_is_caught_by_aggregation_and_other_project_is_not_mixed_in(self):
        parts = [rec(id=f's{i}', amount=200000, date=f'2026-10-0{i + 1}') for i in range(3)]
        a = E.assess_record(self.proposer, parts[0], parts[1:]); self.assertEqual((a.material, a.reasons), (True, ('M-AGG',)))
        other = [dict(p, group={'project': 'P2'}) for p in parts[1:]]
        self.assertFalse(E.assess_record(self.proposer, parts[0], other).material)
        far = [dict(p, date='2026-12-01') for p in parts[1:]]
        self.assertFalse(E.assess_record(self.proposer, parts[0], far).material)

    def test_candidate_that_cannot_be_placed_makes_the_result_material(self):
        a = E.assess_record(self.proposer, rec(), [rec(id='z', date='not a date')]); self.assertIn('M-AGG-UNKNOWN', a.reasons)
        a = E.assess_record(self.proposer, rec(id='y'), [rec(id='z2', group={})]); self.assertIn('M-AGG-UNKNOWN', a.reasons)

    def test_aggregation_spec_missing_is_material(self):
        p = {k: v for k, v in POL.items() if k != 'aggregation'}; p['version'] = 'T-NA'
        tight = self.who('tt', 'ten-t', 'x1', ('materiality_owner',)); t2 = self.who('tt2', 'ten-t', 'x2', ('materiality_owner',)); t3 = self.who('tt3', 'ten-t', 'x3')
        E.propose_policy(t3, p); E.approve_policy(tight, 'T-NA'); E.approve_policy(t2, 'T-NA'); E.activate_policy(tight, 'T-NA')
        self.assertIn('M-AGG-SPEC-MISSING', E.assess_record(t3, rec(), []).reasons)

    def test_delay_measure(self):
        self.assertTrue(E.assess_record(self.proposer, {'id': 'd1', 'subject': 'delay', 'delay_days': 5}).material)
        self.assertFalse(E.assess_record(self.proposer, {'id': 'd2', 'subject': 'delay', 'delay_days': 4}).material)
        self.assertEqual(E.assess_record(self.proposer, {'id': 'd3', 'subject': 'delay', 'delay_days': Unknown('no_data')}).reasons, ('M-DAYS-MISSING',))


class Spoofing(Base):
    def setUp(self):
        super().setUp(); self.activate()

    def test_record_naming_another_tenant_is_refused_and_audited(self):
        with self.assertRaises(TenantMismatch): E.assess_record(self.proposer, rec(tenant_id='ten-b'))
        with self.assertRaises(TenantMismatch): E.assess_record(self.proposer, rec(), [rec(id='c', **{'Tenant': 'ten-b'})])
        self.assertIn('tenant_claim.refused', [e.event_type for e in self.env.audit.read(self.proposer.ctx)])

    def test_a_foreign_claim_cannot_hide_behind_an_unstorable_value(self):
        with self.assertRaises(TenantMismatch): E.assess_record(self.proposer, rec(amount=1.5, tenant_id='ten-b'))
        with self.assertRaises(TenantMismatch): E.assess_record(self.proposer, rec(), [rec(id='c', amount=float('nan'), org_id='ten-b')])
        self.assertEqual(self.proposer.query(E.DECISION_KIND), ())

    def test_matching_claim_is_stripped_and_does_not_change_the_answer(self):
        a = E.assess_record(self.proposer, rec(id='m', tenant_id='ten-a')); self.assertNotIn('tenant_id', a.stored['record'])


class Reproducible(Base):
    def setUp(self):
        super().setUp(); self.activate()

    def test_same_inputs_same_assessment_one_record_and_verifies(self):
        a = E.assess_record(self.proposer, rec()); self.clock.advance(100); b = E.assess_record(self.proposer, rec())
        self.assertEqual(a.key, b.key); self.assertEqual(len(self.proposer.history(E.DECISION_KIND, a.key)), 1); self.assertEqual(E.verify_assessment(self.proposer, a.key), (True, ''))

    def test_old_assessment_still_verifies_after_the_policy_changes(self):
        a = E.assess_record(self.proposer, rec(amount=499999)); self.assertFalse(a.material)
        t = dict(POL, version='T-2', rules=dict(POL['rules'], invoice={'abs_cents': 400000, 'rel_bps': 100, 'rel_base': 'contract_value'}))
        E.propose_policy(self.proposer, t); E.approve_policy(self.owner1, 'T-2'); E.activate_policy(self.owner1, 'T-2')
        self.assertEqual(E.verify_assessment(self.proposer, a.key), (True, '')); b = E.assess_record(self.proposer, rec(amount=499999))
        self.assertTrue(b.material); self.assertNotEqual(a.key, b.key)

    def test_tampered_result_inputs_or_policy_are_detected(self):
        a = E.assess_record(self.proposer, rec(amount=499999)); p = self.proposer.get(E.DECISION_KIND, a.key).payload
        self.proposer.put(E.DECISION_KIND, a.key, dict(p, result=dict(p['result'], material=True)))
        self.assertEqual(E.verify_assessment(self.proposer, a.key), (False, 'RESULT_DIFFERS'))
        b = E.assess_record(self.proposer, rec(id='q', amount=10)); q = self.proposer.get(E.DECISION_KIND, b.key).payload
        self.proposer.put(E.DECISION_KIND, b.key, dict(q, record=dict(q['record'], amount_cents=999999999)))
        self.assertEqual(E.verify_assessment(self.proposer, b.key), (False, 'DECISION_INPUTS_ALTERED'))
        self.assertEqual(E.verify_assessment(self.proposer, 'nope'), (False, 'DECISION_MISSING'))

    def test_a_decision_pointed_at_a_different_policy_version_is_detected(self):
        a = E.assess_record(self.proposer, rec(amount=499999))
        t = dict(POL, version='T-2', rules=dict(POL['rules'], invoice={'abs_cents': 400000, 'rel_bps': 100, 'rel_base': 'contract_value'}))
        E.propose_policy(self.proposer, t); p = self.proposer.get(E.DECISION_KIND, a.key).payload
        self.proposer.put(E.DECISION_KIND, a.key, dict(p, policy_version='T-2'))
        self.assertEqual(E.verify_assessment(self.proposer, a.key), (False, 'POLICY_CONTENT_DIFFERS'))

    def test_no_policy_assessment_verifies_too(self):
        env, c = make_env(); p = ScopedStore(env.store, env.audit, login(env, 't', 'ten-z', 'u')); a = E.assess_record(p, rec())
        self.assertEqual(E.verify_assessment(p, a.key), (True, ''))


if __name__ == '__main__':
    unittest.main()
