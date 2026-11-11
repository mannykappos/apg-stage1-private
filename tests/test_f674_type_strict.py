"""APG-F67.4: correction of finding F-75 (the independent audit of APG-F67.3).  "Unchanged" approved content was compared with Python equality, under which False == 0 and
True == 1, so a direct write that changed an approved value's type kept the approval.  Now the approved content and the approver's entries are compared by the store's own
canonical, type-preserving fingerprint (canon.digest), and so is the re-store check.  Every test runs over all five policy records, on approved content that holds a 0, a 1 or a
boolean (for the specification register, a version with a conversion factor of 1, which its schema permits).  The F-73 and F-74 tests are unchanged.
Run against the delivered APG-F67.3 code, the tests of the defect fail or error."""
import copy, unittest
from . import _path                                         # noqa: F401
from .test_f671_approval_recovery import World, RECORDS
from apg import canon, policy_approval as PA, repro
from apg.fin import policy as FP
from apg.mkt import policy as MP
from apg.rec import engine as E, policy as RP


def swappable(x, pre=()):
    """-> the path of the first 0, 1 or boolean in x (depth first, in key order), or None."""
    if isinstance(x, bool) or (isinstance(x, int) and x in (0, 1)):
        return pre
    items = sorted(x.items()) if isinstance(x, dict) else enumerate(x) if isinstance(x, list) else ()
    for k, v in items:
        p = swappable(v, pre + (k,))
        if p is not None:
            return p
    return None


def at(p, path, value=None, put=False):
    c = p
    for k in path[:-1]:
        c = c[k]
    if put:
        c[path[-1]] = value
    return c[path[-1]]


def typed_world():
    """The test world, with a specification-register version whose approved content holds a 1 (a conversion factor; its schema permits it)."""
    w = World()
    p = copy.deepcopy(w.stored('spec').payload)
    p.update(version='S-INT', approvals=[], proposer=w.s.ctx.user_id)
    p['unit_conversions'] = list(p.get('unit_conversions', [])) + [{'material': 'MAT-CU', 'from_unit': 'm', 'to_unit': 'length', 'factor_micro': 1}]
    MP.store_spec(w.s, p)
    w.ver['spec'] = 'S-INT'
    return w


def swap(w, name):
    """Change the type of the first 0, 1 or boolean in the approved content by a direct write.  -> (path, old value, new value, the new revision)."""
    cur = w.stored(name)
    q = copy.deepcopy(cur.payload)
    path = swappable(PA.content(q))
    old = at(q, path)
    new = int(old) if isinstance(old, bool) else bool(old)
    at(q, path, new, put=True)
    return path, old, new, w.s.put(RECORDS[name][0], w.ver[name], q, expected_revision=cur.revision)


def run_counts(w, name):
    """True or False from a run; None when the run refuses the content (the recommendation run validates its policy and refuses a type-changed one)."""
    try:
        return w.approved_in_run(name)
    except E.EngineError:
        return None


class TestTypeChangingEdits(unittest.TestCase):
    def test_a_type_changing_edit_breaks_the_approval(self):
        w = typed_world()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                self.assertEqual(w.status(name)['confirmed'], ['olive'])
                path, old, new, rec = swap(w, name)
                self.assertTrue(old == new and type(old) is not type(new))                 # equal under Python equality, a different value under the fingerprint
                self.assertEqual((w.status(name)['confirmed'], w.status(name)['recorded_not_confirmed']), ([], ['olive']))
                self.assertIn(run_counts(w, name), (False, None))
                self.assertIsNot(run_counts(w, name), True)

    def test_the_owner_can_approve_the_changed_content_afresh(self):
        w = typed_world()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                swap(w, name)
                w.approve(name, w.olive, 'approve the changed content in person')
                self.assertEqual(w.status(name)['confirmed'], ['olive'])
                self.assertEqual(w.events(name, 'olive')[-1].detail['revision'], w.stored(name).revision)

    def test_every_type_change_breaks_it_at_the_holds_level(self):
        """True for 1, 1 for True, False for 0, 0 for False, '1' for 1, and the same inside a list: each is a change."""
        cases = ((1, True), (True, 1), (0, False), (False, 0), (1, '1'), ([1, 2], [True, 2]), ({'a': 0}, {'a': False}))
        for before, after in cases:
            w = World()
            name, kind = 'fin', FP.POLICY_KIND
            cur = w.stored(name)
            w.s.put(kind, w.ver[name], dict(cur.payload, note=before), expected_revision=cur.revision)    # the content holds `before` when approved
            w.approve(name, w.olive)
            r = w.stored(name).revision
            cur = w.stored(name)
            w.s.put(kind, w.ver[name], dict(cur.payload, note=after), expected_revision=cur.revision)
            with self.subTest(before=before, after=after):
                self.assertTrue(PA.holds(w.s, kind, w.ver[name], r, 'olive', r))
                self.assertFalse(PA.holds(w.s, kind, w.ver[name], r, 'olive'))

    def test_a_change_of_key_order_alone_is_not_a_change(self):
        """The fingerprint is canonical: the same content with its keys in another order is the same content, and the approval holds."""
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                cur = w.stored(name)
                reordered = dict(reversed(list(cur.payload.items())))
                rec = w.s.put(RECORDS[name][0], w.ver[name], reordered, expected_revision=cur.revision)
                self.assertEqual(rec.revision, cur.revision)                            # the store sees the same content: nothing appended
                self.assertEqual(w.status(name)['confirmed'], ['olive'])

    def test_content_that_cannot_be_fingerprinted_never_holds(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                w.approve(name, w.olive)
                r = w.stored(name).revision
                self.assertTrue(PA.holds(w.s, RECORDS[name][0], w.ver[name], r, 'olive', r))
                real = PA.fingerprint
                PA.fingerprint = lambda x: (_ for _ in ()).throw(canon.CanonError('not canonical'))
                try:
                    self.assertFalse(PA.holds(w.s, RECORDS[name][0], w.ver[name], r, 'olive', r))
                    self.assertFalse(PA.same({'a': 1}, {'a': 1}))
                finally:
                    PA.fingerprint = real


class TestReStore(unittest.TestCase):
    """The re-store comparison itself (today's schemas also refuse type-changed content first, so the schema check is stubbed out to reach the comparison)."""
    def test_a_type_changed_re_store_is_refused_as_different_content(self):
        w = typed_world()
        for name in RECORDS:
            with self.subTest(record=name):
                cur = w.stored(name)
                q = copy.deepcopy(dict(cur.payload, approvals=[]))
                path = swappable(PA.content(q))
                old = at(q, path)
                at(q, path, int(old) if isinstance(old, bool) else bool(old), put=True)
                if name == 'rec':
                    real, RP.validate_policy = RP.validate_policy, (lambda p: [])
                    try:
                        with self.assertRaises(RP.RecPolicyError) as cm:
                            RP.store_policy(w.s, q)
                    finally:
                        RP.validate_policy = real
                else:
                    with self.assertRaises(RuntimeError) as cm:
                        PA.store(w.s, RECORDS[name][0], q, lambda p: [], RuntimeError, name)
                self.assertIn('already exists with different content', str(cm.exception))
                self.assertEqual(w.stored(name).revision, cur.revision)

    def test_the_same_content_stored_again_is_still_a_no_op(self):
        w = typed_world()
        for name in RECORDS:
            with self.subTest(record=name):
                cur = w.stored(name)
                again = dict(reversed(list(dict(cur.payload, approvals=[]).items())))
                if name == 'rec':
                    RP.store_policy(w.s, again)
                else:
                    PA.store(w.s, RECORDS[name][0], again, lambda p: [], RuntimeError, name)
                self.assertEqual(w.stored(name).revision, cur.revision)

    def test_same_unit(self):
        self.assertTrue(PA.same({'a': 1, 'b': [True]}, {'b': [True], 'a': 1}))
        for a, b in (({'a': 1}, {'a': True}), ({'a': 0}, {'a': False}), ({'a': 1}, {'a': '1'}), ([1], [True])):
            self.assertFalse(PA.same(a, b))
        self.assertEqual(PA.fingerprint({'a': 1}), canon.digest({'a': 1}))


class TestPinnedReplay(unittest.TestCase):
    def test_a_run_before_the_type_change_replays_as_approved(self):
        w = typed_world()
        for name in ('fin', 'det', 'mkt', 'spec'):
            with self.subTest(record=name):
                w.approve(name, w.olive)
                before = w.run(name)
                swap(w, name)
                reg = {'fin': w.m.reg, 'det': w.m.detreg, 'mkt': w.m.mreg, 'spec': w.m.mreg}[name]
                self.assertTrue(repro.replay(w.s, reg, before['run_key']).ok)
                self.assertTrue(w.approved_in_run(name, before))
                self.assertFalse(w.approved_in_run(name))


if __name__ == '__main__':
    unittest.main()
