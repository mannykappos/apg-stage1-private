"""Stage 1 (APG-M11-S1), Workstream T, P1-F5, P2-B8, P4-B17 and T-0: the RESULT v=2 schema, its reconciliation, the derived status and
exit (precedence 2, then 3, then 1, then 0), and the checker that consumers use (R1_REQUIREMENTS.md §2.4, §2.7).
Helper level (tools/evkit.py); at tool level, a child's evidence error in every mutation tool (ConsumersOfAChildEvidenceError) and a child
in the wrong mode (AChildInTheWrongModeIsAnItemError); the wrapper-level cases are in test_runner_zero_work.py.
Run from the package root:  python3 -I -S tests_tools/test_consumer_exit_codes.py      BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys
import unittest

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

H = '0' * 64


def ids(n, prefix='M'):
    return ['%s%03d' % (prefix, i) for i in range(n)]


def text(lines):
    return '\n'.join(lines) + '\n'


def result(lines):
    return E.parse_result_line(lines[-1])[1]


class WorkedCasesMutation(unittest.TestCase):
    """The worked cases of §2.7, each a test."""

    def test_start_control_fails(self):
        sel = ids(100)
        lines, code = E.finish_items('mutation', 'm2_mutants_s1', 'r1', sel, {}, control_start='FAIL', not_run_cause='control_start_FAIL')
        f = result(lines)
        self.assertEqual((f['preflight'], f['control_start'], f['started'], f['not_run'], f['control_end']), ('PASS', 'FAIL', 0, 100, 'NOT_RUN'))
        self.assertEqual(sum(1 for l in lines if l.startswith('MUTANT ') and ' NOT_RUN ' in l), 100)
        self.assertEqual((f['status'], code), ('INDETERMINATE', 3))
        self.assertEqual(E.check_output(text(lines), 3, selected=sel), [])

    def test_preflight_fails_on_one(self):
        sel = ids(100)
        err = E.RunError('PREFLIGHT_INVALID_TARGET', 'M007:occurrences=0')
        lines, code = E.finish_items('mutation', 'm2_mutants_s1', 'r1', sel, {}, run_errors=[err], preflight='FAIL',
                                     control_start='NOT_RUN', not_run_cause='preflight_failed')
        f = result(lines)
        self.assertEqual((f['preflight'], f['control_start'], f['started'], f['not_run'], f['run_errors']), ('FAIL', 'NOT_RUN', 0, 100, 1))
        self.assertEqual((f['status'], code), ('EVIDENCE_ERROR', 2))
        self.assertIn('RUN_ERROR PREFLIGHT_INVALID_TARGET M007:occurrences=0', lines)
        self.assertEqual(E.check_output(text(lines), 2, selected=sel), [])

    def test_38_killed_1_survivor_1_timeout(self):
        sel = ids(40)
        out = {i: ('KILLED', 'test_values.py') for i in sel[:38]}
        out[sel[38]] = ('SURVIVED', 'none')
        out[sel[39]] = ('INDETERMINATE', 'timeout')
        lines, code = E.finish_items('mutation', 'm2_mutants_s1', 'r1', sel, out)
        f = result(lines)
        self.assertEqual((f['started'], f['completed'], f['killed'], f['survived'], f['indeterminate'], f['not_run']), (40, 39, 38, 1, 1, 0))
        self.assertEqual((f['status'], code), ('INDETERMINATE', 3))
        self.assertIn('MUTANT %s SURVIVED cause=none' % sel[38], lines)  # the survivor is listed whatever the exit
        self.assertEqual(E.check_output(text(lines), 3, selected=sel), [])

    def test_all_killed_is_ok(self):
        sel = ids(5)
        lines, code = E.finish_items('mutation', 't', 'r', sel, {i: ('KILLED', 'test_x.py') for i in sel})
        self.assertEqual(code, 0)
        self.assertEqual(result(lines)['status'], 'OK')

    def test_one_survivor_is_failed(self):
        sel = ids(5)
        out = {i: ('KILLED', 'f') for i in sel}
        out[sel[2]] = ('SURVIVED', 'none')
        lines, code = E.finish_items('mutation', 't', 'r', sel, out)
        self.assertEqual((result(lines)['status'], code), ('FAILED', 1))

    def test_end_control_fails_keeps_every_mutant_line(self):
        sel = ids(5)
        lines, code = E.finish_items('mutation', 't', 'r', sel, {i: ('KILLED', 'f') for i in sel}, control_end='FAIL')
        self.assertEqual((result(lines)['status'], code), ('INDETERMINATE', 3))
        self.assertEqual(sum(1 for l in lines if ' KILLED ' in l), 5)

    def test_end_control_cannot_rescue_a_failed_start_control(self):
        sel = ids(3)
        lines, code = E.finish_items('mutation', 't', 'r', sel, {i: ('KILLED', 'f') for i in sel}, control_start='FAIL', control_end='PASS')
        f = result(lines)
        self.assertEqual((f['started'], f['control_end'], code), (0, 'NOT_RUN', 2))  # items reported as started: also an evidence error
        self.assertIn('ITEM_STARTED_WITHOUT_PREFLIGHT_AND_CONTROL', '\n'.join(lines))

    def test_zero_selected_is_an_evidence_error(self):
        lines, code = E.finish_items('mutation', 't', 'r', [], {})
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID zero_selected', lines)

    def test_duplicate_selection_and_unselected_result(self):
        lines, code = E.finish_items('mutation', 't', 'r', ['A', 'A', 'B'], {'A': ('KILLED', 'f'), 'B': ('KILLED', 'f'), 'C': ('KILLED', 'f')})
        self.assertEqual(code, 2)
        joined = '\n'.join(lines)
        self.assertIn('SELECTION_INVALID duplicate A', joined)
        self.assertIn('RESULT_FOR_UNSELECTED_ITEM C', joined)

    def test_a_worker_cannot_create_not_run(self):
        lines, code = E.finish_items('mutation', 't', 'r', ['A'], {'A': ('NOT_RUN', 'x')})
        self.assertEqual(code, 2)
        self.assertIn('WORKER_OUTCOME_INVALID', '\n'.join(lines))

    def test_run_stopped_before_the_last_item(self):
        sel = ids(4)
        lines, code = E.finish_items('mutation', 't', 'r', sel, {sel[0]: ('KILLED', 'f')}, not_run_cause='stopped')
        f = result(lines)
        self.assertEqual((f['not_run'], f['control_end'], code), (3, 'NOT_RUN', 3))


class PrecedenceAndDerivation(unittest.TestCase):
    def test_precedence_two_then_three_then_one_then_zero(self):
        base = dict(selected=3, preflight='PASS', control_start='PASS', control_end='PASS', item_errors=0, indeterminate=0,
                    not_run=0, survived=0, run_errors=0)
        self.assertEqual(E.derive_status('mutation', dict(base, run_errors=1, indeterminate=1, survived=1)), 'EVIDENCE_ERROR')
        self.assertEqual(E.derive_status('mutation', dict(base, item_errors=1, survived=1)), 'EVIDENCE_ERROR')
        self.assertEqual(E.derive_status('mutation', dict(base, indeterminate=1, survived=1)), 'INDETERMINATE')
        self.assertEqual(E.derive_status('mutation', dict(base, not_run=1, survived=1)), 'INDETERMINATE')
        self.assertEqual(E.derive_status('mutation', dict(base, survived=1)), 'FAILED')
        self.assertEqual(E.derive_status('mutation', base), 'OK')
        self.assertEqual(E.derive_status('mutation', dict(base, reconciled=False)), 'EVIDENCE_ERROR')

    def test_sabotage_and_cases(self):
        lines, code = E.finish_items('sabotage', 'sabotage_m10_s1', 'r', ['P1', 'P2'], {'P1': ('CAUGHT', 'f'), 'P2': ('MISSED', 'none')})
        self.assertEqual((result(lines)['status'], code), ('FAILED', 1))
        self.assertEqual(E.check_output(text(lines), 1), [])
        lines, code = E.finish_items('cases', 'run_contracts_s1', 'r', ['RS/RS-01', 'RS/RS-02'], {'RS/RS-01': ('PASS', 'ok'),
                                     'RS/RS-02': ('PASS', 'ok')}, suites_selected=1)
        self.assertEqual(code, 0)
        self.assertEqual(E.check_output(text(lines), 0), [])
        with self.assertRaises(ValueError):
            E.finish_items('cases', 't', 'r', ['no_suite_part'], {})


def pins_for(files):
    return {n: {'sha256': h, 'ids': tids} for n, h, tids in files}


class WorkedCasesTests(unittest.TestCase):
    def setUp(self):
        self.files = [('test_%d.py' % i, ('%d' % i) * 64, ['tests.test_%d.T.test_%s' % (i, c) for c in 'abc']) for i in range(8)]
        self.pins = pins_for(self.files)
        self.sel = [n for n, _, _ in self.files]

    def completed(self, n, statuses=None):
        pin = self.pins[n]
        statuses = statuses or ['PASS'] * len(pin['ids'])
        return E.FileResult(n, 'COMPLETED', list(zip(pin['ids'], statuses)), pin['sha256'])

    def test_all_pass_full(self):
        res = {n: self.completed(n) for n in self.sel}
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', self.sel, res, self.pins)
        self.assertEqual(code, 0)
        self.assertEqual(E.check_output(text(lines), 0, pins=self.pins, selected=self.sel), [])

    def test_import_error_inside_code_under_test_is_failed(self):
        res = {n: self.completed(n) for n in self.sel}
        res['test_3.py'] = self.completed('test_3.py', ['PASS', 'ERROR', 'PASS'])
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', self.sel, res, self.pins)
        f = result(lines)
        self.assertEqual((f['files_completed'], f['errors'], f['status'], code), (8, 1, 'FAILED', 1))
        self.assertEqual(E.check_output(text(lines), 1, pins=self.pins, selected=self.sel), [])

    def test_a_file_not_in_the_pins_is_an_evidence_error(self):
        sel = self.sel + ['test_extra.py']
        res = {n: self.completed(n) for n in self.sel}
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', sel, res, self.pins)
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR TEST_FILE_NOT_IN_PINS test_extra.py', lines)

    def test_failfast_kill_is_failed_not_indeterminate(self):
        res = {n: self.completed(n) for n in self.sel[:2]}
        pin = self.pins['test_2.py']
        res['test_2.py'] = E.FileResult('test_2.py', 'COMPLETED', [(pin['ids'][0], 'PASS'), (pin['ids'][1], 'FAIL')], pin['sha256'],
                                        not_run_after_failure=[pin['ids'][2]])
        lines, code = E.finish_tests('mut_runner_s1', 'failfast', 'r', self.sel, res, self.pins)
        f = result(lines)
        self.assertEqual((f['files_skipped_after_failure'], f['files_not_run'], f['status'], code), (5, 0, 'FAILED', 1))
        self.assertIn('FILE test_2.py state=COMPLETED tests=2 passed=1 failed=1 errors=0 skipped=0 tests_not_run=1 file_sha256=%s ids_sha256=%s'
                      % (pin['sha256'], E.sha256_lines(pin['ids'][:2])), lines)
        self.assertEqual(E.check_output(text(lines), 1, pins=self.pins, selected=self.sel), [])

    def test_skipped_after_failure_is_refused_in_full_mode(self):
        res = {n: self.completed(n) for n in self.sel[:1]}
        res['test_1.py'] = self.completed('test_1.py', ['PASS', 'FAIL', 'PASS'])
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', self.sel, res, self.pins)
        f = result(lines)
        self.assertEqual(f['files_skipped_after_failure'], 0)
        self.assertEqual((f['files_not_run'], code), (6, 3))  # full mode: the files never started are NOT_RUN, so indeterminate

    def test_inventory_mismatch_is_an_evidence_error(self):
        res = {n: self.completed(n) for n in self.sel}
        pin = self.pins['test_4.py']
        res['test_4.py'] = E.FileResult('test_4.py', 'COMPLETED', [(pin['ids'][0], 'PASS'), (pin['ids'][1], 'PASS')], pin['sha256'])
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', self.sel, res, self.pins)
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR TEST_INVENTORY_MISMATCH test_4.py ids', lines)
        res['test_4.py'] = E.FileResult('test_4.py', 'COMPLETED', list(zip(pin['ids'], ['PASS'] * 3)), 'f' * 64)
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', self.sel, res, self.pins)
        self.assertIn('RUN_ERROR TEST_INVENTORY_MISMATCH test_4.py file_sha256', lines)

    def test_zero_files_selected_is_an_evidence_error(self):
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', [], {}, self.pins)
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID zero_selected', lines)

    def test_a_file_that_never_started_is_indeterminate(self):
        res = {n: self.completed(n) for n in self.sel[:7]}
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', self.sel, res, self.pins)
        self.assertEqual((result(lines)['files_not_run'], code), (1, 3))


class CheckerRejectsBadOutput(unittest.TestCase):
    """The checker re-derives everything and rejects malformed, missing, duplicated or contradictory records."""

    def setUp(self):
        self.sel = ids(4)
        self.lines, self.code = E.finish_items('mutation', 't', 'r', self.sel, {i: ('KILLED', 'f') for i in self.sel})
        self.assertEqual(E.check_output(text(self.lines), 0, selected=self.sel), [])

    def bad(self, lines, exit_code=0, **kw):
        probs = E.check_output(text(lines), exit_code, **kw)
        self.assertTrue(probs, 'the checker accepted tampered output:\n' + text(lines))
        return probs

    def test_no_result_line(self):
        self.bad(self.lines[:-1])

    def test_two_result_lines(self):
        self.assertEqual(self.bad(self.lines + [self.lines[-1]]), ['more than one RESULT line'])

    def test_result_not_last(self):
        self.bad(self.lines + ['trailing text'])

    def test_field_order_missing_extra_and_spacing(self):
        r = self.lines[-1]
        self.bad(self.lines[:-1] + [r.replace(' killed=4 survived=0', ' survived=0 killed=4')])
        self.bad(self.lines[:-1] + [r.replace(' equivalent=0', '')])
        self.bad(self.lines[:-1] + [r + ' extra=1'])
        self.bad(self.lines[:-1] + [r.replace(' ', '  ', 1)])
        self.bad(self.lines[:-1] + [r.replace(r.split(' ')[1], 'v=4')])

    def test_counts_contradict_the_item_lines(self):
        r = self.lines[-1]
        self.bad(self.lines[:-1] + [r.replace('killed=4', 'killed=3')])
        self.bad(self.lines[1:])  # a MUTANT line missing
        self.bad([self.lines[0]] + self.lines)  # a MUTANT line duplicated

    def test_status_or_exit_contradicting(self):
        r = self.lines[-1]
        self.bad(self.lines[:-1] + [r.replace('status=OK exit=0', 'status=OK exit=1')], exit_code=1)
        self.bad(self.lines, exit_code=1)  # the printed exit differs from the process's actual exit

    def test_a_survivor_hidden_behind_ok(self):
        lines = list(self.lines)
        lines[0] = lines[0].replace(' KILLED ', ' SURVIVED ')
        lines[-1] = lines[-1].replace('killed=4 survived=0', 'killed=3 survived=1')
        self.bad(lines)  # status OK with a survivor: the derivation gives FAILED

    def test_selection_differs(self):
        self.bad(self.lines, selected=self.sel[:3])

    def test_ids_hash_tampered(self):
        r = self.lines[-1]
        self.bad(self.lines[:-1] + [r.replace('ids_sha256=' + E.sha256_lines(self.sel), 'ids_sha256=' + H)])

    def test_tests_kind_tampering(self):
        pins = {'test_a.py': {'sha256': 'a' * 64, 'ids': ['m.T.test_1', 'm.T.test_2']}}
        good, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', ['test_a.py'], {'test_a.py': E.FileResult(
            'test_a.py', 'COMPLETED', [('m.T.test_1', 'PASS'), ('m.T.test_2', 'PASS')], 'a' * 64)}, pins)
        self.assertEqual(E.check_output(text(good), 0, pins=pins), [])
        self.bad([l for l in good if 'test_2' not in l], pins=pins)  # a TEST line dropped
        self.bad([good[0], good[0]] + good[1:], pins=pins)  # a TEST line duplicated
        self.bad([good[0].replace(' PASS', ' FAIL')] + good[1:], pins=pins)  # a TEST line changed without its FILE line
        changed_pins = {'test_a.py': {'sha256': 'a' * 64, 'ids': ['m.T.test_1', 'm.T.test_2', 'm.T.test_3']}}
        self.bad(good, pins=changed_pins)  # the inventory differs from the pins

    def test_classify_child(self):
        self.assertEqual(E.classify_child(text(self.lines), 0)[0], 'CHILD_OK')
        self.assertEqual(E.classify_child('no result here\n', 0)[0], 'CRASH_NO_RESULT')
        self.assertEqual(E.classify_child(text(self.lines), 1)[0], 'CHILD_EVIDENCE_ERROR')


class CheckerRejectsBadSabotageAndCases(unittest.TestCase):
    """Authorisation §4.4, 'The checker rejects ... Each case has a test', for kind=sabotage and kind=cases (the mutation, tests and wrapper
    kinds are above and in WrapperResultW1): a missing, duplicated or changed item line, contradicting counts, a forged status or exit,
    a missing or duplicated RESULT line, a changed field order, a tampered ids hash, and a selection that differs."""

    def setUp(self):
        self.psel = ['P1', 'P2', 'P3']
        self.sab, self.sab_code = E.finish_items('sabotage', 'sabotage_m10_s1', 'r', self.psel, {p: ('CAUGHT', 'f') for p in self.psel})
        self.csel = ['RS/RS-01', 'RS/RS-02', 'RT/RT-01']
        self.cas, self.cas_code = E.finish_items('cases', 'run_contracts_s1', 'r', self.csel, {c: ('PASS', 'ok') for c in self.csel},
                                                 suites_selected=2)
        self.assertEqual((self.sab_code, self.cas_code), (0, 0))
        self.assertEqual(E.check_output(text(self.sab), 0, selected=self.psel), [])
        self.assertEqual(E.check_output(text(self.cas), 0, selected=self.csel), [])

    def bad(self, lines, exit_code=0, **kw):
        probs = E.check_output(text(lines), exit_code, **kw)
        self.assertTrue(probs, 'the checker accepted tampered output:\n' + text(lines))
        return probs

    def both(self):
        return (('sabotage', self.sab, self.psel, 'PLANT ', ' CAUGHT ', ' MISSED ', 'caught=3', 'caught=2'),
                ('cases', self.cas, self.csel, 'CASE ', ' PASS ', ' FAIL ', 'passed=3', 'passed=2'))

    def test_item_lines_missing_duplicated_or_changed(self):
        for kind, lines, sel, tag, good, worse, cnt, cnt_less in self.both():
            with self.subTest(kind=kind):
                items = [i for i, l in enumerate(lines) if l.startswith(tag)]
                self.assertEqual(len(items), 3, lines)
                self.bad([l for i, l in enumerate(lines) if i != items[0]])                 # an item line missing
                self.bad(lines[:items[0]] + [lines[items[0]]] + lines[items[0]:])           # an item line duplicated
                changed = list(lines)
                changed[items[0]] = changed[items[0]].replace(good, worse)
                self.bad(changed)                                                            # an item changed without its counts

    def test_counts_contradict_the_item_lines(self):
        for kind, lines, sel, tag, good, worse, cnt, cnt_less in self.both():
            with self.subTest(kind=kind):
                self.assertIn(' %s ' % cnt, lines[-1])
                self.bad(lines[:-1] + [lines[-1].replace(' %s ' % cnt, ' %s ' % cnt_less)])

    def test_forged_status_or_exit(self):
        for kind, lines, sel, tag, good, worse, cnt, cnt_less in self.both():
            with self.subTest(kind=kind):
                r = lines[-1]
                self.assertTrue(r.endswith('status=OK exit=0'), r)
                self.bad(lines[:-1] + [r.replace('status=OK exit=0', 'status=FAILED exit=1')], exit_code=1)
                self.bad(lines[:-1] + [r.replace('status=OK exit=0', 'status=OK exit=1')], exit_code=1)
                self.bad(lines, exit_code=1)                                                # printed exit differs from the actual exit
                changed = list(lines)
                i = next(i for i, l in enumerate(lines) if l.startswith(tag))
                changed[i] = changed[i].replace(good, worse)
                changed[-1] = r.replace(' %s ' % cnt, ' %s ' % cnt_less).replace(' missed=0 ' if kind == 'sabotage' else ' failed=0 ',
                                                                                  ' missed=1 ' if kind == 'sabotage' else ' failed=1 ')
                self.bad(changed)                                                            # a miss or failure hidden behind OK

    def test_result_line_missing_duplicated_reordered_or_tampered(self):
        for kind, lines, sel, tag, good, worse, cnt, cnt_less in self.both():
            with self.subTest(kind=kind):
                r = lines[-1]
                self.bad(lines[:-1])
                self.assertEqual(self.bad(lines + [r]), ['more than one RESULT line'])
                self.bad(lines + ['trailing text'])
                self.bad(lines[:-1] + [r.replace(r.split(' ')[1], 'v=4')])
                self.bad(lines[:-1] + [r + ' extra=1'])
                self.bad(lines[:-1] + [r.replace(' ', '  ', 1)])
                if kind == 'sabotage':
                    self.bad(lines[:-1] + [r.replace('ids_sha256=' + E.sha256_lines(sel), 'ids_sha256=' + H)])
                # kind=cases: case_inventory_sha256 is checked against the pinned inventories (decision (a'), CaseInventoryHash below)
                self.bad(lines, selected=sel[:2])

    def test_no_mode_field_on_a_kind_without_one(self):
        # DP-2.3 F9: only kind=tests carries a mode; a RESULT line of another kind with a mode field is malformed
        for kind, lines, sel, tag, good, worse, cnt, cnt_less in self.both():
            with self.subTest(kind=kind):
                self.assertNotIn(' mode=', lines[-1])
                self.bad(lines[:-1] + [lines[-1].replace(' run=r ', ' mode=failfast run=r ')])
        # and modes are pinned for the test runners only: every pinned caller profile names one of them
        doc, _ = E.load_pins()
        runners = {k.split('@')[0] for k in doc['runner_profiles']}
        self.assertTrue(runners)
        self.assertLessEqual(runners, set(E.CHILD_TEST_RUNNERS))


class CaseInventoryHash(unittest.TestCase):
    """Decision (a') (owner, 2026-11-02 15:33), on real outputs of run_contracts_s1 (suites audit_log 14, record_store 18, tenant_context 6)
    and run_det_corpus_s1: given the pinned case inventories, the checker rejects a case_inventory_sha256 that is not the hash of the
    selected suites' pinned inventories, and accepts every valid form:
      - a full run (every suite, every case);
      - a partial --only run whose selected suite has more pinned cases than the CASE records it prints (14 pinned, 1 printed): the case
        that exposed the first, wrong rule (a), which hashed the printed CASE records;
      - two selected suites of which only one prints CASE records (--suite record_store --suite audit_log --only AL-01);
      - a refusal, which prints no CASE record, accepted as the evidence error it is (exit 2).
    Without the pins the checker cannot verify this field, and a tampered one is not caught: that limitation is stated, not hidden."""

    def run_tool(self, *args):
        import subprocess, tempfile
        tmp = tempfile.mkdtemp(prefix='s1_cih_')
        try:
            p = subprocess.run([sys.executable, '-I', '-S'] + list(args), cwd=ROOT, capture_output=True, text=True, timeout=600,
                               env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp,
                                    'PYTHONDONTWRITEBYTECODE': '1'})
            return p.returncode, p.stdout
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def tampered(self, out):
        lines = out.strip().splitlines()
        f = E.parse_result_line(lines[-1])[1]
        return '\n'.join(lines[:-1] + [lines[-1].replace('case_inventory_sha256=' + f['case_inventory_sha256'],
                                                          'case_inventory_sha256=' + H)]) + '\n'

    def test_each_form_with_and_without_the_pins(self):
        doc, _ = E.load_pins()
        for tool, args, want_exit in (('run_contracts_s1', [], 0),
                                      ('run_contracts_s1', ['--suite', 'audit_log', '--only', 'AL-01'], 0),
                                      ('run_contracts_s1', ['--suite', 'record_store', '--suite', 'audit_log', '--only', 'AL-01'], 0),
                                      ('run_det_corpus_s1', ['--only', 'B01,B02'], 0),
                                      ('run_det_corpus_s1', ['--only', 'NOPE'], 2),
                                      ('run_contracts_s1', ['--suite', 'nope'], 2)):
            with self.subTest(tool=tool, args=args):
                pins = doc['case_inventories'][tool]
                code, out = self.run_tool(os.path.join('tools', tool + '.py'), *args)
                self.assertEqual(code, want_exit, out[-1500:])
                printed = [l for l in out.splitlines() if l.startswith('CASE ')]
                if args[-2:] == ['--only', 'AL-01']:
                    self.assertEqual(len(printed), 1)                         # 1 printed, 14 (or 14 + 18) pinned
                    self.assertGreater(len(pins['audit_log']['ids']), len(printed))
                self.assertEqual(E.check_output(out, code, pins=pins), [], out[-1500:])           # valid: accepted
                bad = self.tampered(out)
                self.assertIn('case_inventory_sha256 does not match the pinned inventories of the selected suites',
                              E.check_output(bad, code, pins=pins))                              # tampered: rejected
                self.assertNotIn('case_inventory_sha256 does not match the pinned inventories of the selected suites',
                                 E.check_output(bad, code))                                      # without pins: not verifiable
                if want_exit == 2:
                    self.assertTrue(out.strip().splitlines()[-1].endswith(' status=EVIDENCE_ERROR exit=2'))

    def test_a_case_suite_that_is_not_pinned(self):
        doc, _ = E.load_pins()
        code, out = self.run_tool(os.path.join('tools', 'run_m5_contracts_s1.py'))
        self.assertEqual(code, 0)
        self.assertEqual(E.check_output(out, code, pins=doc['case_inventories']['run_m5_contracts_s1']), [])
        self.assertIn('CASE suite notification is not in the pinned case inventories',
                      E.check_output(out, code, pins=doc['case_inventories']['run_m6_contracts_s1']))


class SuccessMarkerPosition(unittest.TestCase):
    """§2.4 and §2.7: the M10 success marker is printed verbatim and only on exit 0, immediately before the RESULT line, so the RESULT
    line stays the last non-empty line."""

    def emitted(self, lines, code):
        import io
        buf = io.StringIO()
        E.emit(lines, code, success_marker='ALL CORPUS CASES PASS', stream=buf)
        return buf.getvalue().splitlines()

    def test_marker_before_result_on_exit_0_only(self):
        lines, code = E.finish_items('cases', 't', 'r', ['S/c1'], {'S/c1': ('PASS', 'ok')}, suites_selected=1)
        out = self.emitted(lines, code)
        self.assertEqual(out[-2], 'ALL CORPUS CASES PASS')
        self.assertTrue(out[-1].startswith(('RESULT v=2 ', 'RESULT v=3 ')))
        self.assertEqual(E.check_output('\n'.join(out), 0, selected=['S/c1']), [])
        lines, code = E.finish_items('cases', 't', 'r', ['S/c1'], {'S/c1': ('FAIL', 'x')}, suites_selected=1)
        self.assertNotIn('ALL CORPUS CASES PASS', self.emitted(lines, code))


class WrapperResultW1(unittest.TestCase):
    """Decision W-1 (owner, 2026-10-31 20:57; APG_D14_STAGE1_DECISION_W1_REV2.md draft 2): kind=wrapper, the CHECK and EXCLUDED records,
    OK_WITH_EXCLUSIONS (exit 0), zero work, the canonical hashing (§1.8) and the consumer rule (§1.9), on constructed records."""

    def s_group(self, gid='G03', fail=False):
        lines = ['TEST test_values.py::tests.test_values.T.test_a PASS',
                 'TEST test_values.py::tests.test_values.T.test_b %s' % ('FAIL' if fail else 'PASS')]
        out = '\n'.join(lines + ['FILE test_values.py state=COMPLETED tests=2 passed=%d failed=%d errors=0 skipped=0 tests_not_run=0 '
                                 'file_sha256=%s ids_sha256=%s' % (1 if fail else 2, 1 if fail else 0, H, H)])
        return ('file', E.wrapper_group_from_child(gid, E.group_inventory_sha256([('test_values.py', H)]), 'CHILD_FAILED' if fail else 'CHILD_OK',
                                                   out, 'tests'))

    def check(self, gid='G01', outcome='PASS', ex=0, marker='seen', source='child'):
        return ('check', (gid, outcome, source, ex, marker, E.command_sha256(['tools/probe_f67.py']), H, E.text_sha256('F-67 IS CORRECTED')))

    def excl(self, gid='G02'):
        return ('excluded', (gid, 'APG-M6.2', 'records_check_of_its_own_release', E.command_sha256(['tools/programme_check_m62.py', '.'])))

    def run_(self, records, errs=()):
        lines, code = E.finish_wrapper('run_x_all_s1', 'r', records, errs)
        return '\n'.join(lines), code

    def test_status_and_exit(self):
        t, c = self.run_([self.check(), self.excl(), self.s_group()])
        self.assertEqual((c, E.check_output(t, c), E.wrapper_verdict(t, c)), (0, [], 'OK_WITH_EXCLUSIONS'))
        self.assertTrue(t.splitlines()[-1].endswith(' excluded_historical=1 run_errors=0 inventory_sha256=%s checks_sha256=%s exclusions_sha256=%s '
                                                    'status=OK_WITH_EXCLUSIONS exit=0' % (
                                                        E.sha256_lines(['G03 ' + E.group_inventory_sha256([('test_values.py', H)])]),
                                                        E.sha256_lines([E.check_identity('G01', 'child', E.command_sha256(['tools/probe_f67.py']), H,
                                                                                         E.text_sha256('F-67 IS CORRECTED'))]),
                                                        E.sha256_lines([E.excluded_line('G02', 'APG-M6.2', 'records_check_of_its_own_release',
                                                                                        E.command_sha256(['tools/programme_check_m62.py', '.']))]))))
        t, c = self.run_([self.check(), self.s_group()])
        self.assertEqual((c, E.check_output(t, c), E.wrapper_verdict(t, c)), (0, [], 'OK'))
        for rec, code, status in ((self.check(outcome='FAIL', ex=1, marker='absent'), 1, 'FAILED'), (self.s_group('G04', fail=True), 1, 'FAILED'),
                                  (self.check(outcome='INDETERMINATE', ex=None, marker='-'), 3, 'INDETERMINATE'),
                                  (self.check(outcome='ITEM_ERROR', ex=0, marker='absent'), 2, 'EVIDENCE_ERROR')):
            t, c = self.run_([self.excl(), rec])
            self.assertEqual((c, E.check_output(t, c), E.wrapper_verdict(t, c)), (code, [], status), t)

    def test_zero_work_is_an_evidence_error(self):
        t, c = self.run_([self.excl('G01'), self.excl('G02')])
        self.assertEqual((c, E.check_output(t, c), E.wrapper_verdict(t, c)), (2, [], 'EVIDENCE_ERROR'))

    def test_forged_and_misplaced_statuses_are_rejected(self):
        t, c = self.run_([self.check(), self.excl()])
        forged = t.replace('status=OK_WITH_EXCLUSIONS', 'status=OK')
        self.assertIn('status OK but the counts give OK_WITH_EXCLUSIONS', E.check_output(forged, 0))
        self.assertEqual(E.wrapper_verdict(forged, 0), 'EVIDENCE_ERROR')
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', [], {}, {})   # a kind=tests line cannot carry OK_WITH_EXCLUSIONS
        tl = [l for l in lines if l.startswith('RESULT')][0].replace('status=EVIDENCE_ERROR exit=2', 'status=OK_WITH_EXCLUSIONS exit=0')
        self.assertTrue(E.check_output(tl, 0))
        dropped = '\n'.join(l for l in t.splitlines() if not l.startswith('EXCLUDED'))
        self.assertIn('excluded_historical=1 but the lines give 0', E.check_output(dropped, 0))

    def test_consumer_rule(self):
        t, c = self.run_([self.check(), self.excl()])
        outcome, kind, fields, problems = E.classify_child(t, 0)
        self.assertEqual((outcome, problems), ('CHILD_EVIDENCE_ERROR', ['wrapper child not accepted']))
        self.assertEqual(E.wrapper_verdict('PASS everything\nALL CHECKS PASS', 0), 'EVIDENCE_ERROR')   # exit 0, no valid RESULT line
        tests_line = '\n'.join(E.finish_tests('run_m2_tests_s1', 'full', 'r', [], {}, {})[0])
        self.assertEqual(E.wrapper_verdict(tests_line, 2), 'EVIDENCE_ERROR')                    # not kind=wrapper

    def test_check_outcome_table(self):
        self.assertEqual(E.check_outcome(0, True), ('PASS', 0, 'seen'))
        self.assertEqual(E.check_outcome(1, False), ('FAIL', 1, 'absent'))
        self.assertEqual(E.check_outcome(1, True), ('FAIL', 1, 'seen'))
        self.assertEqual(E.check_outcome(0, False), ('ITEM_ERROR', 0, 'absent'))
        self.assertEqual(E.check_outcome(2, True), ('ITEM_ERROR', 2, 'seen'))
        self.assertEqual(E.check_outcome(5, False), ('ITEM_ERROR', 5, 'absent'))
        self.assertEqual(E.check_outcome(-9, False), ('ITEM_ERROR', None, 'absent'))
        self.assertEqual(E.check_outcome(None, False, timed_out=True), ('INDETERMINATE', None, '-'))
        self.assertEqual(E.check_outcome(None, False, launch_error=True), ('ITEM_ERROR', None, '-'))
        self.assertEqual(E.check_outcome(0, True, pin_mismatch=True), ('ITEM_ERROR', None, '-'))

    def test_canonical_hashing(self):
        self.assertEqual(E.command_sha256(['tools/programme_check_m62.py', '.']),
                         '205f506a815191072c4057f33e885b6b1a5604060269236645d35131b619726c')   # the §1.8 example (30 bytes)
        self.assertEqual(E.text_sha256(''), E.EMPTY_SHA256)
        for bad in (['tools/x.py', 'a b'], ['tools/x.py', ''], ['tools/x.py', 'a\tb'], []):
            with self.assertRaises(E.RunError) as c:
                E.command_sha256(bad)
            self.assertEqual(c.exception.code, 'PIN_INVALID')
        items = [E.check_identity('G%02d' % i, 'child', H, H, H) for i in range(1, 5)]
        self.assertEqual(E.sha256_lines(items), E.sha256_lines(list(reversed(items))))            # order-independent
        self.assertEqual(E.sha256_lines(items), __import__('hashlib').sha256('\n'.join(sorted(items)).encode('utf-8')).hexdigest())  # LF, no final LF
        changed = items[:-1] + [items[-1][:-1] + '1']
        self.assertNotEqual(E.sha256_lines(items), E.sha256_lines(changed))                       # one byte

    def test_checker_rejects_bad_wrapper_lines(self):
        t, c = self.run_([self.check(), self.excl(), self.s_group()])
        bad = {
            'CHECK G01 PASS source=child exit=1 marker=seen': 'contradicts',
            'EXCLUDED G02 NOT_RUN_HISTORICAL release=APG-M6.2 reason=because': 'malformed EXCLUDED line',
        }
        for old_prefix, want in bad.items():
            lines = t.splitlines()
            i = next(k for k, l in enumerate(lines) if l.startswith(old_prefix.split(' ')[0] + ' ' + old_prefix.split(' ')[1]))
            lines[i] = old_prefix + (lines[i][len(' '.join(lines[i].split(' ')[:len(old_prefix.split(' '))])):] if 'reason' not in old_prefix else
                                     ' command_sha256=' + H)
            self.assertTrue(any(want in x for x in E.check_output('\n'.join(lines), c)), (want, E.check_output('\n'.join(lines), c)))
        dropped_test = '\n'.join(l for l in t.splitlines() if not l.endswith('test_b PASS'))
        self.assertIn('FILE G03 counts differ from its relayed lines', E.check_output(dropped_test, c))
        pins = {'files': {'G03': E.group_inventory_sha256([('test_values.py', H)])},
                'checks': {'G01': E.check_identity('G01', 'child', E.command_sha256(['tools/probe_f67.py']), H, E.text_sha256('F-67 IS CORRECTED'))},
                'exclusions': {'G02': [l for l in t.splitlines() if l.startswith('EXCLUDED')][0]}}
        self.assertEqual(E.check_output(t, c, pins=pins), [])
        pins['exclusions']['G02'] = pins['exclusions']['G02'].replace('APG-M6.2', 'APG-M6.3')
        self.assertIn('EXCLUDED G02 differs from the pin', E.check_output(t, c, pins=pins))



class ConsumersOfAChildEvidenceError(unittest.TestCase):
    """P1-F5 (R4): for each consumer (m2, m3, m4, m5, m6, m7, m73, m91, f67, f671, f672, f673, f674, mie, mie11), the child test runner
    (mut_runner or run_m2_tests, and run_contracts for m2) is replaced in the tool's temporary copy by a stub that exits 2 with a valid
    RESULT v=2 ... status=EVIDENCE_ERROR exit=2 line, for one mutant.  On M10 any non-zero exit of the child is a kill: the mutant is KILLED
    and the run exits 0.  On the successor the child's evidence error is that mutant's ITEM_ERROR and the run exits 2.  The harness (the
    stub, the copy, the one-mutant selection) is the one in test_mutation_timeout.py."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix='s1_consumers_')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


def _add_consumer_cases():
    import re
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import test_mutation_timeout as H

    for tool in H.MUT_TOOLS:
        def t(self, tool=tool):
            mid, code, out, err = H.run_m10_tool(self.tmp, tool, 'evidence')
            self.assertEqual(code, 0, (tool, out[-1500:], err[-1500:]))
            self.assertTrue(re.search(r'(?m)^KILLED +%s +\(by ' % re.escape(mid), out) or re.search(r'(?m)^mutants 1 +killed 1 ', out),
                            out[-1500:])
            mid, code, out, err = H.run_s1_tool(self.tmp, tool, 'evidence')
            self.assertEqual(code, 2, (tool, out[-2000:], err[-1500:]))
            self.assertRegex(out, r'(?m)^MUTANT %s ITEM_ERROR cause=\S+$' % re.escape(mid))
            self.assertTrue(out.strip().splitlines()[-1].endswith(' status=EVIDENCE_ERROR exit=2'))
            self.assertEqual(E.check_output(out, code, selected=[mid]), [])
        setattr(ConsumersOfAChildEvidenceError, 'test_child_error_' + tool, t)


_add_consumer_cases()



ROLE_STUB = """import sys
# planted by tests_tools/test_consumer_exit_codes.py: a child test runner that prints one text for the controls and another for the mutant
a = sys.argv[1:]
rid = a[a.index('--run-id') + 1] if '--run-id' in a else ''
print(%r if rid.startswith('control') else %r)
sys.exit(0)
"""


class AChildInTheWrongModeIsAnItemError(unittest.TestCase):
    """Authorisation §4.6 last point, T-0 (R5), DP-2.3 F10: a child that reports a mode other than the one pinned for its runner and caller
    is CHILD_EVIDENCE_ERROR, so ITEM_ERROR in its caller.  The pinned profile mut_runner_s1@mutation_tool is failfast; a child line that
    is valid and passing but says mode=full makes the mutant ITEM_ERROR (exit 2), never SURVIVED.  On M10 a mutation tool does not read
    the child's report at all: an exit 0 is a survival whatever the child ran.  In a wrapper (run_m2_tests_s1@wrapper is full), a child
    line saying mode=failfast makes the group ITEM_ERROR and the wrapper exit 2."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix='s1_mode_')
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import test_mutation_timeout as H
        self.H = H

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def line(self, mode):
        res = {'test_stub.py': E.FileResult('test_stub.py', 'COMPLETED', [('tests.test_stub.T.test_a', 'PASS')], '0' * 64)}
        return '\n'.join(E.finish_tests('stub_child', mode, 'stub', ['test_stub.py'], res, self.H.STUB_PIN)[0])

    def test_mutation_tool(self):
        H = self.H
        mid = H.first_mutant('m6')
        tree = H.stub_tree(os.path.join(self.tmp, 's1'), 'm6', 'ok', 's1')
        with open(os.path.join(tree, 'tools', 'mut_runner_s1.py'), 'w') as fh:
            fh.write(ROLE_STUB % (self.line('failfast'), self.line('full')))
        code, out, err = H.run_tool(tree, 'm6_mutants_s1.py', ['--ids', mid])
        self.assertEqual(code, 2, out[-2000:])
        self.assertIn('MUTANT %s ITEM_ERROR cause=child_evidence_error' % mid, out)
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_PASS ')
        self.assertEqual(E.check_output(out, code, selected=[mid]), [])
        # a control child in the wrong mode is not a passing control
        tree = H.stub_tree(os.path.join(self.tmp, 's1c'), 'm6', 'ok', 's1')
        with open(os.path.join(tree, 'tools', 'mut_runner_s1.py'), 'w') as fh:
            fh.write(ROLE_STUB % (self.line('full'), self.line('failfast')))
        code, out, err = H.run_tool(tree, 'm6_mutants_s1.py', ['--ids', mid])
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL cause=CHILD_EVIDENCE_ERROR ')
        # M10: the child's report is not read; exit 0 is a survival
        tree = H.stub_tree(os.path.join(self.tmp, 'm10'), 'm6', 'ok', 'm10')
        code, out, err = H.run_tool(tree, 'm6_mutants.py', ['--ids', mid], site=True)
        self.assertEqual(code, 1, out[-1500:])
        self.assertIn('SURVIVED   %s' % mid, out)

    def test_sabotage_tool(self):
        # the same for a sabotage caller: run_m2_tests_s1@sabotage_tool is failfast; a plant's child saying mode=full is ITEM_ERROR
        import shutil
        H = self.H
        tree = os.path.join(self.tmp, 'sab')
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        pid = H.sabotage_case('mie1')[0]
        with open(os.path.join(tree, 'tools', 'run_m2_tests_s1.py'), 'w') as fh:
            fh.write(ROLE_STUB % (self.line('failfast'), self.line('full').replace('PASS', 'FAIL', 1)))
        code, out, err = H.run_tool(tree, 'sabotage_mie1_s1.py', ['--ids', pid])
        self.assertEqual(code, 2, out[-2000:])
        self.assertIn('PLANT %s ITEM_ERROR cause=child_evidence_error' % pid, out)
        self.assertEqual(E.check_output(out, code, selected=[pid]), [])

    def test_wrapper_group(self):
        import shutil
        pins, _ = E.load_pins()
        rel = 'tests/test_mkt_policy.py'
        fp = E.test_file_pins(pins, [rel])
        name = os.path.basename(rel)
        res = {name: E.FileResult(name, 'COMPLETED', [(i, 'PASS') for i in fp[name]['ids']], fp[name]['sha256'])}
        text = '\n'.join(E.finish_tests('run_m2_tests_s1', 'failfast', 'r', [name], res, fp)[0])
        tree = os.path.join(self.tmp, 'w')
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        with open(os.path.join(tree, 'tools', 'run_m2_tests_s1.py'), 'w') as fh:
            fh.write('print(%r)\n' % text)
        code, out, err = self.H.run_tool(tree, 'run_m6_all_s1.py', ['--group', '1'])
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^FILE G01 state=ITEM_ERROR ')
        self.assertEqual(E.check_output(out, code), [])


# ---------------------------------------------------------------------------------------------------------------------------------------
# Corrective pass 2 (paper 23d2adb9...f0ea5, amendments 1 and 2): the checker's v=3 rules and the consumer rules, at helper level.
# A.2 and A.3 (kind=cases v=3, the suites field, the canonical hash, the v=2 reader kept); K.1 and B.4 (control_end and the CONTROL lines,
# kind=mutation and sabotage v=3); K.3 (dispatch by kind and version, tests and wrapper stay v=2); F.2's records; AM2-2 (d) (an
# interrupted no-kind child: check_outcome, CHILD_INTERRUPTED, map_mutant); P.3's /proc/<pid>/stat parsing; P.8's message validation.
# ---------------------------------------------------------------------------------------------------------------------------------------

P2_PINS = {'audit_log': {'ids': ['AL-01', 'AL-02']}, 'record_store': {'ids': ['RS-01']}}


def p2_cases_out(sel, outcomes, suites, errs=(), ci=None):
    if ci is None:
        ci = E.sha256_lines(['%s/%s' % (s, c) for s in sorted(suites or []) for c in P2_PINS[s]['ids']])
    out, code = E.finish_items('cases', 'probe', 'r', sel, outcomes, run_errors=list(errs), suites=suites, case_inventory_sha256=ci)
    return out, code


def p2_mut_out(outcomes, sel=('m1', 'm2'), cs='PASS', ce='PASS', errs=(), extra=(), not_run_cause='not_started'):
    out, code = E.finish_items('mutation', 'probe', 'r', list(sel), outcomes, run_errors=list(errs), control_start=cs, control_end=ce,
                               not_run_cause=not_run_cause)
    k = next(i for i, l in enumerate(out) if l.startswith('RUN_ERROR') or l.startswith('RESULT'))
    return out[:k] + list(extra) + out[k:], code


class Pass2CasesV3(unittest.TestCase):
    def test_full_and_partial_runs_are_accepted_and_the_hash_is_verified(self):
        sel = ['audit_log/AL-01', 'audit_log/AL-02', 'record_store/RS-01']
        out, code = p2_cases_out(sel, {s: ('PASS', 'ok') for s in sel}, ['audit_log', 'record_store'])
        self.assertIn(' suites_selected=2 suites=audit_log,record_store ', out[-1])
        self.assertTrue(out[-1].startswith('RESULT v=3 kind=cases '))
        self.assertEqual(E.check_output('\n'.join(out), actual_exit=code, pins=P2_PINS), [])
        # a partial run (one case of a suite with more pinned cases than printed), the hash still over the whole suite
        out, code = p2_cases_out(['audit_log/AL-01'], {'audit_log/AL-01': ('PASS', 'ok')}, ['audit_log'])
        self.assertEqual(E.check_output('\n'.join(out), actual_exit=code, pins=P2_PINS), [])
        bad = '\n'.join(out).replace(out[-1].split('case_inventory_sha256=')[1].split(' ')[0], '0' * 64)
        self.assertTrue(any('case_inventory_sha256' in p for p in E.check_output(bad, actual_exit=code, pins=P2_PINS)))

    def test_the_hash_is_canonical_whatever_order_the_suites_were_requested_in(self):
        # amendment 2 reading 11: finish_items sorts the resolved suites; the hash is over the sorted suites, case ids in pinned order
        a, _ = p2_cases_out([], {}, ['record_store', 'audit_log'])
        b, _ = p2_cases_out([], {}, ['audit_log', 'record_store'])
        self.assertEqual(a[-1], b[-1])
        self.assertIn('suites=audit_log,record_store', a[-1])

    def test_rejected_forms(self):
        sel = ['audit_log/AL-01']
        out, code = p2_cases_out(sel, {sel[0]: ('PASS', 'ok')}, ['audit_log'])
        line = out[-1]
        good = '\n'.join(out)
        for old, new, why in (
                ('suites=audit_log', 'suites=record_store,audit_log', 'unsorted'),
                ('suites=audit_log', 'suites=audit_log,audit_log', 'duplicate'),
                ('suites=audit_log', 'suites=audit_log,', 'malformed'),
                ('suites=audit_log', 'suites=nosuch', 'unpinned'),
                ('suites_selected=1', 'suites_selected=2', 'count'),
        ):
            with self.subTest(why=why):
                text = good.replace(line, line.replace(old, new, 1))
                self.assertNotEqual(E.check_output(text, actual_exit=code, pins=P2_PINS), [], why)
        # a CASE record's suite missing from suites
        text = good.replace(line, line.replace('suites=audit_log', 'suites=record_store', 1).replace(
            line.split('case_inventory_sha256=')[1].split(' ')[0], E.sha256_lines(['record_store/RS-01'])))
        self.assertTrue(any('not in suites' in p for p in E.check_output(text, actual_exit=code, pins=P2_PINS)))
        # a v=3 line without suites is rejected (A.2)
        text = good.replace(line, line.replace(' suites=audit_log', '', 1))
        self.assertNotEqual(E.check_output(text, actual_exit=code), [])

    def test_no_resolved_selection(self):
        out, code = p2_cases_out([], {}, None, errs=[E.RunError('SELECTION_INVALID', 'unknown suite x')], ci=E.sha256_lines([]))
        self.assertIn(' suites_selected=0 suites=- selected=0 ', out[-1])
        self.assertIn('case_inventory_sha256=' + E.EMPTY_SHA256, out[-1])
        self.assertEqual(E.check_output('\n'.join(out), actual_exit=code, pins=P2_PINS), [])
        text = '\n'.join(out).replace('case_inventory_sha256=' + E.EMPTY_SHA256, 'case_inventory_sha256=' + '1' * 64)
        self.assertTrue(any('empty selection' in p for p in E.check_output(text, actual_exit=code)))
        text = '\n'.join(out).replace('suites_selected=0 suites=-', 'suites_selected=1 suites=-')
        self.assertNotEqual(E.check_output(text, actual_exit=code), [])

    def test_the_v2_reader_is_kept_and_never_reads_v3_rules(self):
        line = ('RESULT v=2 kind=cases tool=probe run=r suites_selected=1 selected=1 started=1 completed=1 passed=1 failed=0 '
                'indeterminate=0 item_errors=0 not_run=0 run_errors=0 case_inventory_sha256=%s status=OK exit=0'
                % E.sha256_lines(['audit_log/AL-01', 'audit_log/AL-02']))
        text = 'CASE audit_log/AL-01 PASS cause=ok\n' + line
        self.assertEqual(E.check_output(text, actual_exit=0), [])
        k, f = E.parse_result_line(line)
        self.assertEqual((k, f['v']), ('cases', 2))
        self.assertNotIn('suites', f)

    def test_tests_and_wrapper_stay_v2(self):
        self.assertEqual(E.WRITE_VERSION, {'cases': 3, 'mutation': 3, 'sabotage': 3, 'tests': 2, 'wrapper': 2})
        for kind in ('tests', 'wrapper'):
            with self.assertRaises(ValueError):
                E.parse_result_line('RESULT v=3 kind=%s tool=x' % kind)


class Pass2ControlsV3(unittest.TestCase):
    def check(self, out, code):
        return E.check_output('\n'.join(out), actual_exit=code)

    def test_completed_runs(self):
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')},
                            extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_PASS cause=ok'])
        self.assertTrue(out[-1].startswith('RESULT v=3 kind=mutation '))
        self.assertEqual(self.check(out, code), [])
        # an end control that completed reports its own outcome: FAIL with a cause, TIMEOUT
        for v in ('FAIL', 'TIMEOUT'):
            out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')}, ce=v,
                                extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_%s cause=x' % v])
            self.assertEqual(self.check(out, code), [], v)

    def test_control_line_value_must_equal_its_field(self):
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')}, ce='FAIL',
                            extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_PASS cause=ok'])
        self.assertTrue(any('CONTROL end' in p for p in self.check(out, code)))

    def test_not_run_with_no_stop_record_is_rejected(self):
        # K.1: every item done and the start control passed: control_end=NOT_RUN needs the stop record for that moment
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')}, ce='NOT_RUN', extra=['CONTROL start CONTROL_PASS cause=ok'])
        self.assertTrue(any('K.1' in p for p in self.check(out, code)))

    def test_stopped_after_the_last_item(self):
        rec = 'INTERRUPTED signal=SIGINT at=control_end received=1'
        for extra in (['CONTROL start CONTROL_PASS cause=ok', rec],
                      ['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_NOT_RUN cause=interrupted', rec]):
            out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')}, ce='NOT_RUN', extra=extra)
            self.assertEqual(self.check(out, code), [], extra)
        # the disk floor at the end control's copy
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')}, ce='NOT_RUN',
                            errs=[E.RunError('ENV_DISK_BELOW_FLOOR', 'control_end free=1 floor=2')],
                            extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_NOT_RUN cause=disk_below_floor'])
        self.assertEqual(self.check(out, code), [])
        # the wrong cause, a stop record of another phase, and INTERRUPTED at=control_end beside a completed end control
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')}, ce='NOT_RUN',
                            extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_NOT_RUN cause=disk_below_floor', rec])
        self.assertNotEqual(self.check(out, code), [])
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')}, ce='NOT_RUN',
                            extra=['CONTROL start CONTROL_PASS cause=ok', 'INTERRUPTED signal=SIGINT at=m2 received=1'])
        self.assertNotEqual(self.check(out, code), [])
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')}, ce='PASS',
                            extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_PASS cause=ok', rec])
        self.assertNotEqual(self.check(out, code), [])

    def test_stopped_before_the_last_item(self):
        rec = 'INTERRUPTED signal=SIGTERM at=m1 received=2'
        out, code = p2_mut_out({'m1': ('INDETERMINATE', 'interrupted')}, ce='NOT_RUN', not_run_cause='run_stopped',
                            extra=['CONTROL start CONTROL_PASS cause=ok', rec])
        self.assertEqual(self.check(out, code), [])
        self.assertIn('status=INDETERMINATE exit=3', out[-1])
        # an item stopped in flight with no item NOT_RUN still counts as stopped before the last item (reading 6)
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('INDETERMINATE', 'interrupted')}, ce='NOT_RUN',
                            extra=['CONTROL start CONTROL_PASS cause=ok', 'INTERRUPTED signal=SIGTERM at=m2 received=1'])
        self.assertEqual(self.check(out, code), [])

    def test_start_control_interrupted(self):
        out, code = p2_mut_out({}, cs='FAIL', ce='NOT_RUN', not_run_cause='run_stopped',
                            extra=['CONTROL start CONTROL_INTERRUPTED cause=interrupted',
                                   'INTERRUPTED signal=SIGINT at=control_start received=1'])
        self.assertEqual(self.check(out, code), [])
        out, code = p2_mut_out({}, cs='FAIL', ce='NOT_RUN', extra=['CONTROL start CONTROL_INTERRUPTED cause=interrupted'])
        self.assertTrue(any('CONTROL_INTERRUPTED' in p for p in self.check(out, code)))

    def test_child_interrupted_is_a_completed_failure_not_a_stop(self):
        # amendment 2, AM2-2 (d): CHILD_INTERRUPTED is a completed child outcome; an end control that gives it is CONTROL_FAIL
        out, code = p2_mut_out({'m1': ('INDETERMINATE', 'child_interrupted'), 'm2': ('KILLED', 'c')}, ce='FAIL',
                            extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_FAIL cause=child_interrupted'])
        self.assertEqual(self.check(out, code), [])

    def test_interrupted_placement_and_counts(self):
        out, code = p2_mut_out({'m1': ('INDETERMINATE', 'interrupted')}, ce='NOT_RUN', not_run_cause='run_stopped',
                            extra=['INTERRUPTED signal=SIGTERM at=m1 received=1', 'CONTROL start CONTROL_PASS cause=ok'])
        self.assertTrue(any('immediately before' in p for p in self.check(out, code)))
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')},
                            extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_PASS cause=ok',
                                   'INTERRUPTED signal=SIGTERM at=control_end received=1'])
        self.assertNotEqual(self.check(out, code), [])

    def test_v2_mutation_line_keeps_the_frozen_rule(self):
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')})
        text = '\n'.join(out).replace('RESULT v=3 kind=mutation', 'RESULT v=2 kind=mutation')
        self.assertEqual(E.check_output(text, actual_exit=code), [])


class Pass2InterruptedNoKindChild(unittest.TestCase):
    def test_record_recognised_only_with_exit_3_and_as_the_last_line(self):
        rec = 'INTERRUPTED signal=SIGTERM at=R03 received=1'
        self.assertTrue(E.is_interrupted_child(3, 'PASS R01 x\n\nchecks 1  failed 0\n' + rec + '\n'))
        self.assertFalse(E.is_interrupted_child(1, 'checks 1  failed 0\n' + rec))
        self.assertFalse(E.is_interrupted_child(3, rec + '\nchecks 1  failed 0'))
        self.assertFalse(E.is_interrupted_child(3, 'checks 1  failed 0'))     # exit 3 without the record is not CHILD_INTERRUPTED

    def test_consumers(self):
        self.assertEqual(E.check_outcome(3, True, interrupted_child=True), ('INDETERMINATE', 3, 'seen'))
        self.assertEqual(E.check_outcome(3, False), ('ITEM_ERROR', 3, 'absent'))     # every other exit 3 keeps today's mapping
        cls = E.regression_step_classifier('R01')
        self.assertEqual(E.classify_exited(['x'], 3, 'checks 1  failed 1\nINTERRUPTED signal=SIGINT at=R01 received=1', classify=cls)[0],
                         'CHILD_INTERRUPTED')
        self.assertEqual(E.classify_exited(['x'], 3, 'checks 1  failed 1', classify=cls)[0], 'CRASH_NO_RESULT')
        self.assertEqual(E.map_mutant('CHILD_INTERRUPTED', None), ('INDETERMINATE', 'child_interrupted'))
        self.assertEqual(E.map_plant('CHILD_INTERRUPTED', None), ('INDETERMINATE', 'child_interrupted'))
        self.assertEqual(E.map_mutant('PROCESSES_LEFT', None), ('INDETERMINATE', 'processes_left'))
        self.assertEqual(E.map_mutant('INTERRUPTED', None), ('INDETERMINATE', 'interrupted'))
        self.assertEqual(E.map_mutant('STOPPED', None), ('INDETERMINATE', 'run_stopped'))


class Pass2ForkedMessage(unittest.TestCase):
    FORMS = {'failed': lambda v: isinstance(v, list), 'exception': lambda v: isinstance(v, str),
             'child_error': lambda v: isinstance(v, str)}

    def res(self, how='message', message=None, trailing=False, status=0):
        return {'how': how, 'message': message, 'trailing': trailing, 'status': status, 'leaked': False}

    def test_validation_steps(self):
        P = E.parse_forked_message
        self.assertEqual(P(self.res(message=b'{"failed": []}'), self.FORMS), ('ok', ('failed', [])))
        self.assertEqual(P(self.res(message=b'{"failed": []}', trailing=True), self.FORMS)[0], 'bad_result')
        self.assertEqual(P(self.res(message=b'not json'), self.FORMS)[0], 'bad_result')
        self.assertEqual(P(self.res(message=b'{"failed": [], "x": 1}'), self.FORMS)[0], 'bad_result')
        self.assertEqual(P(self.res(message=b'{"failed": 3}'), self.FORMS)[0], 'bad_result')
        self.assertEqual(P(self.res(message=b'\xff'), self.FORMS)[0], 'bad_result')
        self.assertEqual(P(self.res(how='too_long'), self.FORMS)[0], 'bad_result')
        self.assertEqual(P(self.res(how='eof', status=70 << 8), self.FORMS)[0], 'child_error')
        self.assertEqual(P(self.res(how='eof', status=1 << 8), self.FORMS)[0], 'crash')
        self.assertEqual(P(self.res(how='eof', status=9), self.FORMS)[0], 'crash')
        self.assertEqual(P(self.res(how='timeout'), self.FORMS)[0], 'timeout')
        self.assertEqual(P(self.res(how='interrupted'), self.FORMS)[0], 'interrupted')


class Pass2ProcStat(unittest.TestCase):
    def test_command_name_with_spaces_and_parentheses(self):
        # P.3: the fields are counted after the LAST ')' of the line
        import shutil
        import subprocess
        import tempfile
        d = tempfile.mkdtemp(prefix='s1_stat_')
        try:
            exe = os.path.join(d, 'a b) (c')
            shutil.copy('/bin/sleep', exe)
            p = subprocess.Popen([exe, '30'])
            try:
                st = E.proc_stat(p.pid)
                self.assertIsNotNone(st)
                state, ppid, start = st
                self.assertEqual(ppid, os.getpid())
                with open('/proc/%d/stat' % p.pid) as fh:
                    raw = fh.read()
                self.assertIn('(a b) (c)', raw)
                self.assertEqual(start, int(raw[raw.rindex(')') + 2:].split()[19]))
            finally:
                p.kill()
                p.wait()
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_limit_line(self):
        self.assertEqual(E.limit_line(300), 'LIMIT item=300s exit_after_result=2s grace=10s grace_cancelled=2s escalate=10s kill_verify=5s')
        self.assertEqual((E.T_EXIT_AFTER_RESULT, E.T_GRACE, E.T_GRACE_CANCELLED, E.T_ESCALATE, E.T_KILL_VERIFY), (2, 10, 2, 10, 5))
        self.assertEqual((E.FAULT_ITEM_TIMEOUT_S, E.CASE_ITEM_TIMEOUT_S), (300, 300))

    def test_supervisor_list(self):
        # AM-6 (c): 71 unique supervisors and 3 leaves
        self.assertEqual(len(set(E.SUPERVISOR_STEMS)), 71)
        self.assertEqual(len(E.SUPERVISOR_STEMS), 71)
        self.assertEqual(sorted(E.LEAF_STEMS), ['mut_runner_s1', 'run_m2_tests_s1', 'run_test_files_s1'])
        on_disk = {f[:-3] for f in os.listdir(os.path.join(ROOT, 'tools')) if f.endswith('_s1.py')} | {'child_unittest_runner'}
        self.assertEqual(set(E.SUPERVISOR_STEMS) | set(E.LEAF_STEMS), on_disk)


# ---------------------------------------------------------------------------------------------------------------------------------------
# Amendment 5 (owner, 2026-11-08 11:26, AM5-4 option A): Appendix A part 1, the checker rows 34, 57, 62 and 63.
# Rewritten after the workspace loss of 2026-11-11 from the amendment (recovery authorisation, rebuild rule).
# ---------------------------------------------------------------------------------------------------------------------------------------
class AM5Checker(unittest.TestCase):
    def test_row34_no_resolved_selection_with_a_non_zero_selected(self):
        # A.3: suites=- holds only with suites_selected=0, selected=0 and the empty-selection hash
        out, code = p2_cases_out([], {}, None, errs=[E.RunError('SELECTION_INVALID', 'unknown suite x')], ci=E.sha256_lines([]))
        good = '\n'.join(out)
        self.assertEqual(E.check_output(good, actual_exit=code, pins=P2_PINS), [])
        for bad in (good.replace(' suites=- selected=0 ', ' suites=- selected=1 '),
                    good.replace(' suites=- selected=0 ', ' suites=- selected=2 ')):
            self.assertIn(' suites=- selected=', bad)
            self.assertNotEqual(E.check_output(bad, actual_exit=code, pins=P2_PINS), [])
            self.assertNotEqual(E.check_output(bad, actual_exit=code), [])

    def test_row57_a_completed_end_control_beside_not_run(self):
        # K.1: a completed CONTROL end line beside control_end=NOT_RUN is refused, with both K.1 messages
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')}, ce='NOT_RUN',
                               extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_FAIL cause=x'])
        probs = E.check_output('\n'.join(out), actual_exit=code)
        self.assertIn('CONTROL end CONTROL_FAIL but control_end=NOT_RUN', probs)
        self.assertTrue(any('(K.1)' in p for p in probs), probs)

    def test_row57_a_completed_end_control_reported_as_not_run(self):
        # K.1: an end control whose outcome was fixed is never reported as CONTROL_NOT_RUN without the stop record
        out, code = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')}, ce='NOT_RUN',
                               extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_NOT_RUN cause=interrupted'])
        probs = E.check_output('\n'.join(out), actual_exit=code)
        self.assertIn('CONTROL end CONTROL_NOT_RUN needs control_end=NOT_RUN and the matching stop record', probs)

    def test_row62_cross_kind_v3_dispatch(self):
        # K.3: dispatch by kind and version: a v=3 mutation, sabotage or cases line is read by that kind's v=3 rules (K.1 for the two
        # control kinds, A.3 for cases); the same body as v=2 by the frozen rules; tests and wrapper have no v=3 form
        ctl = ['CONTROL start CONTROL_PASS cause=ok']
        for kind, outcome in (('mutation', ('KILLED', 'c')), ('sabotage', ('CAUGHT', 'c'))):
            with self.subTest(kind=kind):
                out, code = E.finish_items(kind, 'probe', 'r', ['m1'], {'m1': outcome}, control_start='PASS', control_end='NOT_RUN')
                k = next(i for i, l in enumerate(out) if l.startswith('RESULT'))
                text = '\n'.join(out[:k] + ctl + out[k:])
                self.assertTrue(out[-1].startswith('RESULT v=3 kind=%s ' % kind))
                self.assertTrue(any('(K.1)' in p for p in E.check_output(text, actual_exit=code)), kind)      # read by K.1
                v2 = text.replace('RESULT v=3 kind=%s' % kind, 'RESULT v=2 kind=%s' % kind)
                self.assertFalse(any('(K.1)' in p for p in E.check_output(v2, actual_exit=code)), kind)       # the frozen reader
        cases, ccode = p2_cases_out(['audit_log/AL-01'], {'audit_log/AL-01': ('PASS', 'ok')}, ['audit_log'])
        self.assertEqual(E.check_output('\n'.join(cases), actual_exit=ccode, pins=P2_PINS), [])
        no_suites = '\n'.join(cases).replace(' suites=audit_log', '', 1)
        self.assertNotEqual(E.check_output(no_suites, actual_exit=ccode), [])                        # A.3's field, v=3 only
        mut, mcode = p2_mut_out({'m1': ('KILLED', 'c'), 'm2': ('KILLED', 'c')},
                                extra=['CONTROL start CONTROL_PASS cause=ok', 'CONTROL end CONTROL_PASS cause=ok'])
        for kind in ('tests', 'wrapper'):
            self.assertNotEqual(E.check_output(mut[-1].replace('kind=mutation', 'kind=%s' % kind), actual_exit=mcode), [])

    def test_row63_tests_and_wrapper_outputs_twice_through_the_checker(self):
        # K.3: a tests or wrapper output is read the same way twice, with and without P's records before its RESULT line
        pins = {'test_a.py': {'sha256': '0' * 64, 'ids': ['tests.test_a.T.t1']}}
        res = {'test_a.py': E.FileResult('test_a.py', 'COMPLETED', [('tests.test_a.T.t1', 'PASS')], '0' * 64)}
        tl, tc = E.finish_tests('probe', 'full', 'r', ['test_a.py'], res, pins)
        recs = ['CLEANUP x by=probe:1 child=2:3 pgid=2 scan=1-2 left=4:5 exited_in_grace=4:5 killed=- sigterm=1 sigkill=0 scans=2 '
                'deadline=none escalated_after=- ambiguous=- remaining=-', 'CLEANUP_SUMMARY units=1 leaked=1 remaining=0']
        for lines, code, kw in ((tl, tc, {'pins': pins, 'selected': ['test_a.py']}),):
            plain = '\n'.join(lines)
            withp = '\n'.join(lines[:-1] + recs + lines[-1:])
            first = E.check_output(plain, actual_exit=code, **kw)
            self.assertEqual(first, [])
            self.assertEqual(E.check_output(plain, actual_exit=code, **kw), first)
            self.assertEqual(E.check_output(withp, actual_exit=code, **kw), [])
            self.assertEqual(E.check_output(withp, actual_exit=code, **kw), [])
        wl, wc = E.finish_wrapper('probe', 'r', [('check', ('G01', 'PASS', 'child', 0, 'seen', H, H, H))])
        plain = '\n'.join(wl)
        a = E.check_output(plain, actual_exit=wc)
        self.assertEqual(a, [], plain)
        self.assertEqual(E.check_output(plain, actual_exit=wc), a)
        withp = '\n'.join(wl[:-1] + recs + wl[-1:])
        self.assertEqual(E.check_output(withp, actual_exit=wc), a)
        self.assertEqual(E.check_output(withp, actual_exit=wc), a)


if __name__ == '__main__':
    unittest.main()
