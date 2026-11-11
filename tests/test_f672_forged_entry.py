"""APG-F67.2: correction of finding F-73 (the independent audit of APG-F67.1).  The F-67.1 recovery path completed an unconfirmed approval entry in the caller's name after
checking only its role and kind, so an entry written straight into the store with the correct role and kind was completed when the named person approved.  Now approve never
completes an entry it finds: it removes any entry in the caller's name (a new revision), writes a fresh one (another new revision), and the confirming event names that revision.
A confirmation counts only if the revision it names is the one that added that person's entry.  Every test runs over all five policy records.
Run against the delivered APG-F67.1 code, every test fails or errors."""
import unittest
from . import _path                                         # noqa: F401
from .test_f671_approval_recovery import World, RECORDS, failing
from apg import policy_approval as PA
from apg.det import policy as DP
from apg.fin import policy as FP
from apg.mkt import policy as MP
from apg.ports import ConflictError
from apg.rec import policy as RP

ROLE = {'fin': FP.POLICY_ROLE, 'det': DP.POLICY_ROLE, 'mkt': MP.POLICY_ROLE, 'spec': MP.SPEC_ROLE, 'rec': RP.POLICY_ROLE}


def plant(w, name, who='olive', date='2000-01-01', role=None):
    """Write an approval entry naming `who`, with the record's own owner role and kind 'human', straight into the store (as the importer, not through approve)."""
    kind = RECORDS[name][0]
    cur = w.stored(name)
    entry = {'approver': who, 'role': role or ROLE[name], 'kind': 'human', 'date': date}
    return w.s.put(kind, w.ver[name], dict(cur.payload, approvals=cur.payload['approvals'] + [entry]), expected_revision=cur.revision), entry


def lists(rec, who):
    return rec is not None and any(a['approver'] == who for a in rec.payload['approvals'])


class TestPlantedMatchingEntry(unittest.TestCase):
    def test_a_planted_matching_role_entry_never_counts_on_its_own(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                plant(w, name)
                self.assertEqual(w.status(name)['recorded_not_confirmed'], ['olive'])
                self.assertEqual(w.events(name, 'olive'), [])
                self.assertFalse(w.approved_in_run(name))

    def test_the_named_person_approving_replaces_it_and_the_confirmation_names_the_new_revision(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                planted, entry = plant(w, name)
                w.approve(name, w.olive)
                now = w.stored(name)
                kind = RECORDS[name][0]
                self.assertNotIn(entry, now.payload['approvals'])                                   # the planted entry is gone, not completed
                self.assertEqual(now.payload['approvals'], [{'approver': 'olive', 'role': ROLE[name], 'kind': 'human', 'date': w.clock.now()[:10]}])
                self.assertEqual(now.revision, planted.revision + 2)
                self.assertFalse(lists(w.s.get(kind, w.ver[name], planted.revision + 1), 'olive'))     # the revision approve wrote without it
                ev = w.events(name, 'olive')
                self.assertEqual([(e.detail['revision'], e.detail['replaced_unconfirmed_entries']) for e in ev], [(now.revision, 1)])
                self.assertEqual(w.status(name)['confirmed'], ['olive'])
                self.assertTrue(w.approved_in_run(name))

    def test_an_identical_planted_entry_is_still_replaced_by_a_new_revision(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                planted, entry = plant(w, name, date=w.clock.now()[:10])                            # exactly what approve would write
                w.approve(name, w.olive)
                now = w.stored(name)
                self.assertEqual(now.revision, planted.revision + 2)
                self.assertEqual([e.detail['revision'] for e in w.events(name, 'olive')], [now.revision])
                self.assertTrue(w.approved_in_run(name))

    def test_another_person_cannot_turn_the_planted_entry_into_the_owners_approval(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                plant(w, name)
                w.approve(name, w.otto)
                st = w.status(name)
                self.assertEqual((st['confirmed'], st['recorded_not_confirmed']), (['otto'], ['olive']))
                self.assertEqual(w.events(name, 'olive'), [])

    def test_other_approvers_entries_are_kept_when_an_entry_is_replaced(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.otto)
                plant(w, name)
                w.approve(name, w.olive)
                self.assertEqual([a['approver'] for a in w.stored(name).payload['approvals']], ['otto', 'olive'])
                self.assertEqual(w.status(name)['confirmed'], ['olive', 'otto'])

    def test_a_concurrent_change_between_the_two_writes_is_refused_and_nothing_counts(self):
        w = World()
        for name, (kind, ev, err, approve, st) in RECORDS.items():
            with self.subTest(record=name):
                plant(w, name)
                real, calls = w.olive.put, []

                def second_fails(*a, **k):
                    calls.append(1)
                    if len(calls) == 2:
                        raise ConflictError('changed concurrently')
                    return real(*a, **k)
                w.olive.put = second_fails
                try:
                    with self.assertRaises(err) as cm:
                        w.approve(name, w.olive)
                finally:
                    w.olive.put = real
                self.assertIn('changed while it was being approved', str(cm.exception))
                self.assertEqual(w.stored(name).payload['approvals'], [])                           # the planted entry was removed; no fresh one was written
                self.assertEqual(w.events(name, 'olive'), [])
                self.assertFalse(w.approved_in_run(name))
                w.approve(name, w.olive, 'again')
                self.assertTrue(w.approved_in_run(name))

    def test_an_audit_failure_after_the_replacement_is_reported_and_a_later_approval_records_afresh(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                plant(w, name)
                restore = failing(w.olive)
                with self.assertRaises(PA.ApprovalNotConfirmed):
                    w.approve(name, w.olive)
                restore()
                self.assertFalse(w.approved_in_run(name))
                w.approve(name, w.olive, 'again')
                ev = w.events(name, 'olive')
                self.assertEqual([(e.detail['revision'], e.detail['replaced_unconfirmed_entries']) for e in ev], [(w.stored(name).revision, 1)])
                self.assertTrue(w.approved_in_run(name))


class TestRevisionBinding(unittest.TestCase):
    """A confirming event counts only if the revision it names is the one that added that person's entry."""
    def event(self, w, name, scoped, revision, **extra):
        kind, ev = RECORDS[name][0], RECORDS[name][1]
        detail = {'version': w.ver[name], 'approver': scoped.ctx.user_id, **extra}
        if name != 'rec':
            detail['kind'] = kind
        if revision is not None:
            detail['revision'] = revision
        scoped.log(ev, '%s/%s' % (kind, w.ver[name]), 'ok', detail=detail)

    def test_an_event_naming_a_revision_that_did_not_add_the_entry_is_not_counted(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                planted, _ = plant(w, name)
                for rev in (None, planted.revision - 1, planted.revision + 5, 0, -1, True, str(planted.revision)):
                    self.event(w, name, w.olive, rev)
                self.assertEqual(w.status(name)['confirmed'], [])
                self.assertFalse(w.approved_in_run(name))

    def test_an_event_naming_a_later_revision_that_still_lists_the_entry_is_not_counted(self):
        """Only the revision that ADDED the entry binds; a later revision that merely still lists it (here, after another person approved) does not."""
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                planted, _ = plant(w, name)
                w.approve(name, w.otto)
                self.event(w, name, w.olive, w.stored(name).revision)
                self.assertEqual(w.status(name)['confirmed'], ['otto'])

    def test_added_at_reads_the_revision_and_the_one_before(self):
        w = World()
        name, kind = 'fin', FP.POLICY_KIND
        first = w.stored(name).revision
        planted, _ = plant(w, name)
        self.assertTrue(PA.added_at(w.s, kind, w.ver[name], planted.revision, 'olive'))
        self.assertFalse(PA.added_at(w.s, kind, w.ver[name], first, 'olive'))
        self.assertFalse(PA.added_at(w.s, kind, w.ver[name], planted.revision, 'otto'))
        self.assertFalse(PA.added_at(w.s, kind, w.ver[name], planted.revision + 1, 'olive'))        # no such revision

    def test_added_at_for_a_first_revision_that_already_lists_the_entry(self):
        """A version whose first revision lists the entry (possible only by a direct write) has nothing before it: revision 1 added it.  added_at reads it exactly so."""
        w = World()
        p = dict(w.stored('fin').payload, version='DIRECT-1', approvals=[{'approver': 'olive', 'role': FP.POLICY_ROLE, 'kind': 'human', 'date': '2000-01-01'}])
        w.s.put(FP.POLICY_KIND, 'DIRECT-1', p, expected_revision=0)
        self.assertTrue(PA.added_at(w.s, FP.POLICY_KIND, 'DIRECT-1', 1, 'olive'))
        self.assertFalse(PA.added_at(w.s, FP.POLICY_KIND, 'DIRECT-1', 1, 'otto'))
        self.assertFalse(PA.added_at(w.s, FP.POLICY_KIND, w.ver['fin'], 1, 'olive'))                 # the proposal's first revision lists nobody


if __name__ == '__main__':
    unittest.main()
