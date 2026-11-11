"""M8-R1 (finding M8-F7, from the independent audit of APG-M8): an empty source is not current data.
A full read that brings back no record (AUIF reports NO_DATA, or the read ends with nothing delivered) is refused with SOURCE_EMPTY, whether the source was empty from the
start or became empty after a good import.  The gate then answers cannot_assess and the assessment returns no figure and no signal: records stored by an earlier import stay
stored, but are never treated as current because of it.  A clean import after the source is restored makes the assessment possible again.  An event poll that brings no new
event is not an empty source.  Five of the nine tests fail on APG-M8 as delivered; the other four are guards (an event poll with no new event, and reads that fail, are forbidden, are wholly invalid or ambiguous, or bring records, each keep their own outcome)."""
import json, os, shutil, tempfile, unittest
from types import SimpleNamespace
from ._auif import AS_OF, D, DD, DF, HERE_ROOT, R3, client, codes, copy_folder, records, single, status, world
from .synthetic_events import event
from .test_m8_events import IID as EV_IID, ev_world, st as ev_status
from apg_auif import assess, intake

IID, ENT, FILE = 'bz-accounting', 'ap_invoice', 'ap_invoices.csv'


def header_only(path):
    with open(path, encoding='utf-8', newline='') as f:
        head = f.readline()
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(head)


class TestASourceThatIsEmptyFromTheStart(unittest.TestCase):
    def test_the_import_is_refused_nothing_is_written_and_the_gate_refuses(self):
        d = copy_folder('zero_one', 'SRC-01_accounting')
        try:
            header_only(os.path.join(d, FILE))
            w = single(IID, base_dir=d)
            s = w['env'].import_entity('zero_one', IID, ENT)
            self.assertEqual(s['status'], 'blocked', s)
            self.assertEqual([c for c, _ in s['reasons']], ['SOURCE_EMPTY'])
            self.assertEqual(records(w['s'], ENT), {})
            st = status(w['s'], w['env'], expected=[(IID, ENT)])
            self.assertEqual((st['status'], codes(st)), ('cannot_assess', ['SOURCE_EMPTY']))
        finally:
            shutil.rmtree(d)


class TestASourceThatBecomesEmptyAfterAGoodImport(unittest.TestCase):
    def test_old_records_stay_stored_but_are_not_current_and_a_clean_import_recovers(self):
        d = copy_folder('zero_one', 'SRC-01_accounting')
        try:
            p = os.path.join(d, FILE); original = open(p, 'rb').read()
            w = single(IID, base_dir=d)
            self.assertEqual(w['env'].import_entity('zero_one', IID, ENT)['status'], 'applied')
            before = records(w['s'], ENT); self.assertEqual(len(before), 187)
            self.assertEqual(status(w['s'], w['env'], expected=[(IID, ENT)])['status'], 'can_assess')
            header_only(p)
            s = w['env'].import_entity('zero_one', IID, ENT)
            self.assertEqual((s['status'], [c for c, _ in s['reasons']]), ('blocked', ['SOURCE_EMPTY']))
            self.assertEqual(records(w['s'], ENT), before)                                   # nothing deleted, nothing changed ...
            st = status(w['s'], w['env'], expected=[(IID, ENT)])
            self.assertEqual((st['status'], codes(st)), ('cannot_assess', ['SOURCE_EMPTY']))  # ... and nothing assessable
            open(p, 'wb').write(original)                                                      # recovery: the source is restored
            self.assertIn(w['env'].import_entity('zero_one', IID, ENT)['status'], ('applied', 'replay'))      # the same content as before is a replay, applied again
            self.assertEqual(status(w['s'], w['env'], expected=[(IID, ENT)])['status'], 'can_assess')
        finally:
            shutil.rmtree(d)


class TestTheAssessmentReturnsNoFigureForAnEmptySource(unittest.TestCase):
    def test_the_full_assessment_is_withdrawn_while_a_source_is_empty_and_resumes_after_a_clean_import(self):
        root = tempfile.mkdtemp(prefix='apg_m8r1_')
        try:
            for n in os.listdir(HERE_ROOT):                                      # a private package root: everything linked, only the Builder Zero data copied (it is altered below)
                if n == 'builder_zero': shutil.copytree(os.path.join(HERE_ROOT, n), os.path.join(root, n))
                else: os.symlink(os.path.join(HERE_ROOT, n), os.path.join(root, n))
            clock, prov, store, audit, who = world()
            s = who('t-zero_one', 'zero_one', 'ann'); owner = who('o-zero_one', 'zero_one', DD.DEMO_OWNER, DD.OWNER_ROLES)
            env, plan = client.builder_zero(root, 'zero_one', s, clock)
            for iid, ent, f in plan:
                self.assertEqual(env.import_entity('zero_one', iid, ent)['status'], 'applied', (iid, ent))
            R3.reconcile(s, D.demo_register(), AS_OF)
            fv, dv = DF.install(s, clock, owner)['version'], DD.install_det(s, clock, owner)['version']
            expected = env.bindings['zero_one'].expected()
            good = assess.run_assessment(s, clock, expected, 'PRJ-001', AS_OF, fv, dv, env.module)
            self.assertEqual(good['status'], 'assessed')
            p = os.path.join(root, 'builder_zero', 'zero_one', 'SRC-01_accounting', FILE); original = open(p, 'rb').read()
            header_only(p)
            self.assertEqual(env.import_entity('zero_one', IID, ENT)['status'], 'blocked')
            bad = assess.run_assessment(s, clock, expected, 'PRJ-001', AS_OF, fv, dv, env.module)
            self.assertEqual((bad['status'], bad['figures'], bad['signals'], bad['run_keys']), ('cannot_assess', None, None, []))
            self.assertEqual(sorted({r['code'] for r in bad['reasons']}), ['SOURCE_EMPTY'])
            self.assertNotIn(good['run_keys'][0], json.dumps(bad))                                # no earlier figure is shown as current
            open(p, 'wb').write(original)
            self.assertIn(env.import_entity('zero_one', IID, ENT)['status'], ('applied', 'replay'))
            self.assertEqual(assess.run_assessment(s, clock, expected, 'PRJ-001', AS_OF, fv, dv, env.module)['status'], 'assessed')
        finally:
            shutil.rmtree(root)


class TestAnEventPollWithNoNewEventIsNotAnEmptySource(unittest.TestCase):
    def test_no_new_event_leaves_the_assessment_as_it_was(self):
        env, s = ev_world()
        env.ingest_events('zero_one', EV_IID, 'payment', [event(1, 'PAY-9001')])
        self.assertEqual(ev_status(env, s)['status'], 'can_assess')
        out = env.ingest_events('zero_one', EV_IID, 'payment', [])
        self.assertNotIn('SOURCE_EMPTY', {c for c, _ in out.get('reasons', [])})
        self.assertEqual(ev_status(env, s)['status'], 'can_assess')
        self.assertEqual(sorted(records(s, 'payment')), ['PAY-9001'])


class TestTheBatchCheckItself(unittest.TestCase):
    """The sync-report rule on its own, including a read that ends with nothing delivered although AUIF did not say NO_DATA.  (APG-M8.1: the reports carry AUIF rev14's
    'complete' field, as rev14 sends it; a report without it is refused as incomplete: test_m8_findings.py.)"""
    REF = {'id': 'p', 'version': '1', 'hash': 'h'}

    def check(self, report, deliveries=()):
        bnd = SimpleNamespace(state=lambda iid: {'state': 'ACTIVE', 'manifest_ref': self.REF})
        batch = SimpleNamespace(mode='sync', deliveries=list(deliveries), errors=[], states=[], refusals=[], entity='ap_invoice', integration_id='i', expect={'max_pages': 5, 'manifest_ref': self.REF})
        bad, pending = intake.batch_checks(bnd, batch, report, None)
        return sorted({c for c, _ in bad})

    def test_no_data_is_refused(self):
        self.assertEqual(self.check({'pages': 0, 'delivered': 0, 'empty': True, 'complete': True}), ['SOURCE_EMPTY'])

    def test_a_read_that_delivered_nothing_is_refused(self):
        self.assertEqual(self.check({'pages': 1, 'delivered': 0, 'empty': False, 'complete': True}), ['SOURCE_EMPTY'])

    def test_a_read_whose_records_were_all_invalid_or_ambiguous_keeps_its_own_reason(self):
        self.assertEqual(self.check({'pages': 1, 'delivered': 0, 'invalid': 2, 'complete': True}), ['TRANSLATION_INVALID'])
        self.assertEqual(self.check({'pages': 1, 'delivered': 0, 'ambiguous': 1, 'complete': True}), ['AMBIGUOUS'])

    def test_a_read_whose_records_were_all_refused_keeps_its_own_reason(self):          # APG-M8.1: AUIF rev14 refuses a record before translation (e.g. a blank identity)
        self.assertEqual(self.check({'pages': 1, 'delivered': 0, 'refused': 2, 'complete': True}), ['RECORD_REFUSED'])

    def test_a_failed_or_forbidden_read_keeps_its_own_reason(self):
        self.assertEqual(self.check({'pages': 0, 'delivered': 0, 'failed': 'UNAVAILABLE'}), ['SYNC_FAILED'])
        self.assertEqual(self.check({'pages': 0, 'delivered': 0, 'not_allowed': True}), ['SYNC_NOT_ALLOWED'])

    def test_a_read_with_records_is_not_empty(self):
        self.assertEqual(self.check({'pages': 1, 'delivered': 1, 'complete': True}, deliveries=['one']), [])


if __name__ == '__main__':
    unittest.main()
