"""APG-F67.3: correction of finding F-74 (the independent audit of APG-F67.2) and the defect class of F-73 and F-74.  A confirmation counts only while the approval it confirms
still holds at the revision being judged (for a run, the exact revision it pinned): the revision the event names added the approver's entry, and in every revision from there
through the judged one the entry is present and unchanged and the approved content (every field except the approvals) is unchanged.  Threat model: whoever can append arbitrary
revisions to the store, but cannot write an audit event as another person, rewrite a past revision or audit event, or change what a pinned revision reads on replay (the store's
guarantees: apg/contracts/record_store_history_contract.py).  Every test runs over all five policy records.  Run against the delivered APG-F67.2 code, the tests of the
attack paths fail or error; the guards of properties F-67.2 already had pass there."""
import unittest
from . import _path                                         # noqa: F401
from .test_f671_approval_recovery import World, RECORDS
from apg import policy_approval as PA, repro
from apg.rec import engine as E, policy as RP


def put(w, name, **change):
    kind = RECORDS[name][0]
    cur = w.stored(name)
    return w.s.put(kind, w.ver[name], dict(cur.payload, **change), expected_revision=cur.revision)


def entry(w, name, who='olive'):
    return [a for a in w.stored(name).payload['approvals'] if a['approver'] == who][0]


def registry(w, name):
    return {'fin': w.m.reg, 'det': w.m.detreg, 'mkt': w.m.mreg, 'spec': w.m.mreg, 'rec': E.registry()}[name]


class TestAttackPaths(unittest.TestCase):
    """Each attack path of the agreed threat model, after the owner's genuine, confirmed approval."""
    def check_broken(self, w, name):
        self.assertEqual(w.status(name)['confirmed'], [])
        self.assertEqual(w.status(name)['recorded_not_confirmed'], ['olive'] if any(a['approver'] == 'olive' for a in w.stored(name).payload['approvals']) else [])
        self.assertFalse(w.approved_in_run(name))

    def test_an_entry_removed_and_re_planted_identical_no_longer_counts(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                e = entry(w, name)
                put(w, name, approvals=[])
                put(w, name, approvals=[e])
                self.check_broken(w, name)

    def test_an_entry_changed_in_place_no_longer_counts(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                put(w, name, approvals=[dict(entry(w, name), date='2001-01-01')])
                self.check_broken(w, name)
        w = World()
        for name in RECORDS:
            with self.subTest(record=name, change='role'):
                w.approve(name, w.olive)
                put(w, name, approvals=[dict(entry(w, name), role='another_role')])
                self.check_broken(w, name)

    def test_rewritten_approved_content_no_longer_counts(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                put(w, name, note='rewritten after the approval')
                self.check_broken(w, name)
        w = World()
        for name in RECORDS:
            with self.subTest(record=name, change='proposer'):
                w.approve(name, w.olive)
                put(w, name, proposer='someone.else')
                self.check_broken(w, name)

    def test_content_rewritten_and_then_restored_no_longer_counts(self):
        """The approved content must stay unchanged throughout, not merely match at the end."""
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                orig = w.stored(name).payload
                put(w, name, note='rewritten')
                w.s.put(RECORDS[name][0], w.ver[name], orig, expected_revision=w.stored(name).revision)
                self.assertEqual(w.stored(name).payload, orig)
                self.check_broken(w, name)

    def test_a_confirmation_is_not_reused_for_a_new_version_with_the_same_content_and_entry(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                copy = w.ver[name] + '-COPY'
                w.s.put(RECORDS[name][0], copy, dict(w.stored(name).payload, version=copy), expected_revision=0)
                self.assertEqual(PA.confirmed(w.s, RECORDS[name][0], copy) if name != 'rec' else
                                 RP.verified_approvers(w.s, w.s.get(RECORDS[name][0], copy).payload), [])
                w.ver[name], keep = copy, w.ver[name]
                self.assertFalse(w.approved_in_run(name))
                w.ver[name] = keep

    def test_an_old_confirmation_does_not_count_after_a_fresh_approval_replaces_it(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                put(w, name, note='rewritten')
                w.approve(name, w.olive, 'approve the rewritten content in person')
                ev = w.events(name, 'olive')
                self.assertEqual(len(ev), 2)
                self.assertEqual(ev[-1].detail['revision'], w.stored(name).revision)
                self.assertEqual(w.status(name)['confirmed'], ['olive'])
                self.assertTrue(w.approved_in_run(name))


class TestWhatKeepsAnApproval(unittest.TestCase):
    def test_another_persons_approval_keeps_the_existing_ones(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                w.approve(name, w.otto)
                self.assertEqual(w.status(name)['confirmed'], ['olive', 'otto'])
                self.assertTrue(w.approved_in_run(name))

    def test_the_owner_is_never_stuck_after_a_broken_confirmation(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                e = entry(w, name)
                put(w, name, approvals=[]); put(w, name, approvals=[e])
                self.assertFalse(w.approved_in_run(name))
                w.approve(name, w.olive, 'again')
                self.assertTrue(w.approved_in_run(name))


class TestPinnedRevisions(unittest.TestCase):
    def test_a_run_before_tampering_replays_as_approved_and_a_run_after_is_unapproved(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                before = w.run(name)
                put(w, name, note='tampered')
                after = w.run(name)
                self.assertEqual((w.approved_in_run(name, before), w.approved_in_run(name, after)), (True, False))
                self.assertTrue(repro.replay(w.s, registry(w, name), before['run_key']).ok)
                self.assertTrue(repro.replay(w.s, registry(w, name), after['run_key']).ok)
                self.assertTrue(w.approved_in_run(name, {'result': w.s.get(repro.KIND, before['run_key']).payload['result']}))

    def test_confirmations_are_judged_at_the_revision_given(self):
        w = World()
        for name in ('fin', 'det', 'mkt', 'spec'):
            kind = RECORDS[name][0]
            with self.subTest(record=name):
                w.approve(name, w.olive)
                good = w.stored(name)
                put(w, name, note='tampered')
                self.assertEqual(PA.confirmed(w.s, kind, w.ver[name], good.revision), ['olive'])
                self.assertEqual(PA.confirmed(w.s, kind, w.ver[name]), [])
                self.assertEqual(PA.confirmed(w.s, kind, w.ver[name], good.revision - 1), [])          # before the approval
                self.assertEqual(PA.confirmed(w.s, kind, w.ver[name], good.revision + 5), [])          # no such revision
                self.assertEqual(PA.confirmed(w.s, kind, w.ver[name], True), [])
                ref = repro.InputRef(kind, w.ver[name], good.revision, good.payload_hash)
                self.assertEqual(PA.confirmations(w.s, [ref]), {'%s/%s' % (kind, w.ver[name]): ['olive']})
                self.assertEqual(PA.confirmations(w.s, [(kind, w.ver[name])]), {'%s/%s' % (kind, w.ver[name]): []})

    def test_the_recommendation_policy_is_judged_at_the_revision_given(self):
        w = World()
        w.approve('rec', w.olive)
        good = w.stored('rec')
        put(w, 'rec', note='tampered')
        self.assertEqual(RP.verified_approvers(w.s, good.payload, good.revision), ['olive'])
        self.assertEqual(RP.verified_approvers(w.s, w.stored('rec').payload), [])

    def test_holds_unit(self):
        w = World()
        name, kind = 'fin', RECORDS['fin'][0]
        w.approve(name, w.olive)
        r = w.stored(name).revision
        self.assertTrue(PA.holds(w.s, kind, w.ver[name], r, 'olive'))
        self.assertTrue(PA.holds(w.s, kind, w.ver[name], r, 'olive', r))
        self.assertFalse(PA.holds(w.s, kind, w.ver[name], r, 'otto'))
        self.assertFalse(PA.holds(w.s, kind, w.ver[name], r - 1, 'olive'))
        self.assertFalse(PA.holds(w.s, kind, w.ver[name], r, 'olive', r - 1))
        self.assertFalse(PA.holds(w.s, kind, w.ver[name], r, 'olive', r + 1))
        w.approve(name, w.otto)
        self.assertTrue(PA.holds(w.s, kind, w.ver[name], r, 'olive', r + 1))
        self.assertEqual(PA.content({'a': 1, 'approvals': [2]}), {'a': 1})


if __name__ == '__main__':
    unittest.main()
