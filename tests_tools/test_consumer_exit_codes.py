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
        self.bad(self.lines[:-1] + [r.replace('v=2', 'v=3')])

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
        self.assertTrue(out[-1].startswith('RESULT v=2 '))
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


if __name__ == '__main__':
    unittest.main()
