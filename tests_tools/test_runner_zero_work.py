"""Stage 1 (APG-M11-S1), Workstream T, P1-F5, P2-B8, P3-B03, P4-B15, P5-B06, P7-B3 and T-0: no runner may report success after zero or
partial work.  Helper level: the pinned counts (R1_REQUIREMENTS.md §2.2) and the zero-work and selection rules of §2.7; the runner-level
cases are added with each successor runner (kind=cases: class CasesRunners, M10 against the successor).
Run from the package root:  python3 -I -S tests_tools/test_runner_zero_work.py      BUILDER-EXECUTED: NOT INDEPENDENT."""
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402


class PinnedCounts(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='s1_pins_')
        self.path = os.path.join(self.dir, 'expected_counts.json')
        shutil.copy(E.PINS_PATH, self.path)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def edit(self, fn):
        doc = json.load(open(self.path))
        fn(doc)
        with open(self.path, 'w') as f:
            json.dump(doc, f)

    def test_the_real_pins_load_and_match_m10s_whole_suite(self):
        doc, fsha = E.load_pins()
        self.assertEqual(sum(len(v['ids']) for k, v in doc['test_files'].items() if k.startswith('tests/')), 2583)
        self.assertEqual(len([k for k in doc['test_files'] if k.startswith('tests/')]), 117)

    def test_an_edit_without_a_change_record_fails_closed(self):
        def drop_a_test(doc):
            k = sorted(doc['test_files'])[0]
            doc['test_files'][k]['ids'] = doc['test_files'][k]['ids'][1:]
        self.edit(drop_a_test)
        with self.assertRaises(E.RunError) as c:
            E.load_pins(self.path)
        self.assertEqual(c.exception.code, 'EXPECTED_COUNT_UNRECORDED_CHANGE')

    def test_a_version_that_does_not_match_its_records_fails_closed(self):
        self.edit(lambda d: d.update(version=d['version'] + 1))
        with self.assertRaises(E.RunError) as c:
            E.load_pins(self.path)
        self.assertEqual(c.exception.code, 'EXPECTED_COUNT_UNRECORDED_CHANGE')

    def test_no_change_record_fails_closed(self):
        self.edit(lambda d: d.update(change_records=[]))
        with self.assertRaises(E.RunError) as c:
            E.load_pins(self.path)
        self.assertEqual(c.exception.code, 'EXPECTED_COUNT_UNRECORDED_CHANGE')

    def test_the_run_instructions_hash_must_match(self):
        with self.assertRaises(E.RunError) as c:
            E.load_pins(self.path, expected_file_sha256='0' * 64)
        self.assertEqual(c.exception.code, 'EXPECTED_COUNTS_HASH')

    def test_missing_or_malformed_pins(self):
        with self.assertRaises(E.RunError) as c:
            E.load_pins(os.path.join(self.dir, 'none.json'))
        self.assertEqual(c.exception.code, 'EXPECTED_COUNTS_MISSING')
        with open(self.path, 'w') as f:
            f.write('{not json')
        with self.assertRaises(E.RunError) as c:
            E.load_pins(self.path)
        self.assertEqual(c.exception.code, 'EXPECTED_COUNTS_MALFORMED')

    def test_a_recorded_change_loads(self):
        doc, _ = E.load_pins(self.path)
        k = sorted(doc['test_files'])[0]
        doc['test_files'][k] = dict(doc['test_files'][k], ids=doc['test_files'][k]['ids'][1:])
        new = E.write_pins(doc, 'test: remove one id', 'test case', [{'entry': 'test_files/' + k}], path=self.path)
        again, _ = E.load_pins(self.path)
        self.assertEqual(again['version'], new['version'])
        self.assertEqual(again['change_records'][-1]['reason'], 'test: remove one id')
        with self.assertRaises(ValueError):
            E.write_pins(again, '', 'cause', [], path=self.path)

    def test_runner_profiles(self):
        doc, _ = E.load_pins()
        self.assertEqual(E.runner_mode(doc, 'run_m2_tests_s1', 'mutation_tool'), 'failfast')
        self.assertEqual(E.runner_mode(doc, 'run_m2_tests_s1', 'standalone'), 'full')
        self.assertEqual(E.runner_mode(doc, 'mut_runner_s1', 'mutation_tool'), 'failfast')
        with self.assertRaises(E.RunError) as c:
            E.runner_mode(doc, 'run_m2_tests_s1', 'unknown_caller')
        self.assertEqual(c.exception.code, 'RUNNER_PROFILE_NOT_PINNED')

    def test_test_file_pins_omit_unpinned_names(self):
        doc, _ = E.load_pins()
        tp = E.test_file_pins(doc, ['tests/test_values.py', 'tests/test_not_a_file.py'])
        self.assertEqual(list(tp), ['test_values.py'])
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', ['test_values.py', 'test_not_a_file.py'], {}, tp)
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR TEST_FILE_NOT_IN_PINS test_not_a_file.py', lines)
        with self.assertRaises(E.RunError) as c:
            E.test_file_pins(doc, ['tests/test_values.py', 'tests_m8/test_values.py'])
        self.assertEqual(c.exception.code, 'SELECTION_INVALID')


class ZeroAndPartialWork(unittest.TestCase):
    def test_zero_selected_never_succeeds_in_any_kind(self):
        for kind in ('mutation', 'sabotage', 'cases'):
            lines, code = E.finish_items(kind, 't', 'r', [], {})
            self.assertEqual(code, 2, kind)
        lines, code = E.finish_tests('t', 'full', 'r', [], {}, {})
        self.assertEqual(code, 2)

    def test_partial_work_is_never_ok(self):
        lines, code = E.finish_items('mutation', 't', 'r', ['A', 'B', 'C'], {'A': ('KILLED', 'f')}, not_run_cause='stopped')
        self.assertEqual(code, 3)
        pins = {'a.py': {'sha256': 'a' * 64, 'ids': ['m.T.t1']}, 'b.py': {'sha256': 'b' * 64, 'ids': ['m.T.t2']}}
        lines, code = E.finish_tests('t', 'full', 'r', ['a.py', 'b.py'],
                                     {'a.py': E.FileResult('a.py', 'COMPLETED', [('m.T.t1', 'PASS')], 'a' * 64)}, pins)
        self.assertEqual(code, 3)

    def test_a_file_with_zero_tests_against_a_non_empty_pin(self):
        pins = {'a.py': {'sha256': 'a' * 64, 'ids': ['m.T.t1']}}
        lines, code = E.finish_tests('t', 'full', 'r', ['a.py'], {'a.py': E.FileResult('a.py', 'COMPLETED', [], 'a' * 64)}, pins)
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR TEST_INVENTORY_MISMATCH a.py ids', lines)


def run_tool(script, *args):
    tmp = tempfile.mkdtemp(prefix='s1_zw_')
    try:
        p = subprocess.run([sys.executable, '-I', '-S', os.path.join('tools', script)] + list(args), cwd=ROOT, capture_output=True, text=True,
                           timeout=600, env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC',
                                             'TMPDIR': tmp, 'PYTHONDONTWRITEBYTECODE': '1'})
        return p.returncode, p.stdout, p.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


CASE_TOOLS = ('run_contracts_s1', 'run_m3_contracts_s1', 'run_m5_contracts_s1', 'run_ingest_corpus_s1', 'run_fin_corpus_s1',
              'run_det_corpus_s1', 'run_mkt_corpus_s1')


class CasesRunners(unittest.TestCase):
    """P3-B03, P4-B15: the corpus and contract runners.  The M10 runners are byte-identical in this tree (DP-1.2 (B))."""

    def test_m10_det_corpus_with_an_unknown_only_reports_zero_cases_as_a_pass(self):
        code, out, err = run_tool('run_det_corpus.py', '--only', 'NO_SUCH_CASE')
        self.assertEqual(code, 0)
        self.assertIn('corpus cases 0  failed 0', out)
        self.assertIn('ALL CORPUS CASES PASS', out)

    def test_successor_unknown_only_or_suite_is_a_selection_error(self):
        code, out, err = run_tool('run_det_corpus_s1.py', '--only', 'NO_SUCH_CASE')
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID unknown cases NO_SUCH_CASE', out)
        self.assertNotIn('CASES PASS', out)
        code, out, err = run_tool('run_contracts_s1.py', '--suite', 'no_such_suite')
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID unknown suite no_such_suite', out)

    def test_every_successor_runs_its_whole_pinned_inventory_and_the_checker_accepts_it(self):
        doc, _ = E.load_pins()
        for tool in CASE_TOOLS:
            code, out, err = run_tool(tool + '.py')
            self.assertEqual(code, 0, tool + out[-2000:] + err[-2000:])
            inv = doc['case_inventories'][tool]
            want = ['%s/%s' % (s, c) for s in sorted(inv) for c in inv[s]['ids']]
            got = [l.split(' ')[1] for l in out.splitlines() if l.startswith('CASE ')]
            self.assertEqual(got, want, tool)
            lines = [l for l in out.splitlines() if l.strip()]
            self.assertTrue(lines[-1].startswith('RESULT v=2 kind=cases tool=%s ' % tool), tool)
            self.assertRegex(lines[-2], r'^ALL (CONTRACT|CORPUS) CASES PASS$', tool)  # the M10 marker, kept, just before RESULT
            self.assertEqual(E.check_output(out, code, selected=want), [], tool)

    def test_a_changed_case_inventory_fails_closed(self):
        doc, _ = E.load_pins()
        inv = doc['case_inventories']['run_m5_contracts_s1']['notification']
        changed = dict(doc['case_inventories'], run_m5_contracts_s1={'notification': dict(inv, ids=inv['ids'][:-1])})
        d = tempfile.mkdtemp(prefix='s1_ci_')
        try:
            shutil.copytree(ROOT, os.path.join(d, 't'), ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
            pp = os.path.join(d, 't', 'tools', 'expected_counts.json')
            E.write_pins(dict(doc, case_inventories=changed), 'test: drop one pinned case', 'test case', [{'entry': 'x'}], path=pp)
            p = subprocess.run([sys.executable, '-I', '-S', 'tools/run_m5_contracts_s1.py'], cwd=os.path.join(d, 't'), capture_output=True,
                               text=True, timeout=300, env={'PATH': '/usr/bin:/bin', 'TMPDIR': d, 'PYTHONDONTWRITEBYTECODE': '1'})
            self.assertEqual(p.returncode, 2, p.stdout[-2000:])
            self.assertIn('RUN_ERROR CASE_INVENTORY_MISMATCH notification found=12 pinned=11', p.stdout)
        finally:
            shutil.rmtree(d, ignore_errors=True)



def tree_copy(dest):
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
    return dest


def run_in(tree, script, *args, isolated_site=True):
    tmp = tempfile.mkdtemp(prefix='s1_zw_')
    try:
        cmd = [sys.executable, '-I'] + (['-S'] if isolated_site else []) + [os.path.join('tools', script)] + list(args)
        p = subprocess.run(cmd, cwd=tree, capture_output=True, text=True, timeout=1800,
                           env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp,
                                'PYTHONDONTWRITEBYTECODE': '1'})
        return p.returncode, p.stdout, p.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class SabotageAndFaultRunners(unittest.TestCase):
    """P2-B8, P5-B06, P7-B3 and decision K-1 (kind=sabotage): the fault runners and the sabotage tools, M10 against the successor.
    The M10 tools are byte-identical in this tree (DP-1.2 (B)) and none reads tests/_path.py, so they are run in plain copies."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_sab_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_an_empty_fault_list_m10_passes_the_successor_refuses(self):
        tree = tree_copy(os.path.join(self.tmp, 't'))
        p = os.path.join(tree, 'apg', 'det', 'faulty_m5.py')
        with open(p, 'a', encoding='utf-8') as f:
            f.write('\nFAULTS = {}\n')
        code, out, err = run_in(tree, 'run_m5_faults.py', isolated_site=False)
        self.assertEqual((code, 'ALL FAULTS CAUGHT' in out), (0, True))   # M10: zero work reported as every fault caught
        code, out, err = run_in(tree, 'run_m5_faults_s1.py')
        self.assertEqual(code, 2, out[-2000:])
        self.assertIn('RUN_ERROR EXPECTED_COUNT_MISMATCH run_m5_faults_s1 universe 0 pinned 15', out)
        self.assertNotIn('ALL FAULTS CAUGHT', out)

    def test_an_empty_m3_fault_list_and_an_empty_ingest_corpus(self):
        # P2-B8: the same for M3's faulty implementations and the M3 ingestion corpus, each emptied in a temporary copy
        for name, rel, plant, m10, marker, s1, err in (
                ('faults', 'apg/ingest/faulty_m3.py', '\nFAULTS = {}\n', 'run_m3_faults.py', 'ALL FAULTS CAUGHT', 'run_m3_faults_s1.py',
                 'RUN_ERROR EXPECTED_COUNT_MISMATCH run_m3_faults_s1 universe 0 pinned 28'),
                ('corpus', 'apg/ingest/corpus.py', '\ndef cases():\n    return []\n', 'run_ingest_corpus.py', 'ALL CORPUS CASES PASS',
                 'run_ingest_corpus_s1.py', 'RUN_ERROR CASE_INVENTORY_MISMATCH ingest_corpus found=0 pinned=44')):
            with self.subTest(case=name):
                tree = tree_copy(os.path.join(self.tmp, 'empty_' + name))
                with open(os.path.join(tree, rel), 'a', encoding='utf-8') as f:
                    f.write(plant)
                code, out, e = run_in(tree, m10, isolated_site=False)
                self.assertEqual((code, marker in out), (0, True), out[-1500:])     # M10: zero work reported as a pass
                code, out, e = run_in(tree, s1)
                self.assertEqual(code, 2, out[-2000:])
                self.assertIn(err, out)
                self.assertNotIn(marker, out)
                self.assertEqual(E.check_output(out, code), [])

    def test_a_broken_reference_m10_still_catches_everything_the_successor_stops(self):
        tree = tree_copy(os.path.join(self.tmp, 't'))
        p = os.path.join(tree, 'apg', 'reference_impl.py')
        with open(p, 'a', encoding='utf-8') as f:
            f.write('\n\ndef _broken(self, *a, **k):\n    raise RuntimeError("broken store")\n\n\nInMemoryRecordStore._atomic = _broken\n')
        code, out, err = run_in(tree, 'run_faults.py', isolated_site=False)
        self.assertEqual((code, 'ALL FAULTS CAUGHT' in out), (0, True))   # M10 has no control: a store that fails everything "catches" every fault
        code, out, err = run_in(tree, 'run_faults_s1.py')
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL cause=reference_failed_\d+ ')
        self.assertRegex(out.strip().splitlines()[-1], r' started=0 .* status=INDETERMINATE exit=3$')
        self.assertNotIn('ALL FAULTS CAUGHT', out)

    def test_every_fault_runner_reconciles_against_its_pins(self):
        doc, _ = E.load_pins()
        for tool in ('run_faults_s1', 'run_m3_faults_s1', 'run_m5_faults_s1', 'run_m6_faults_s1', 'run_history_contract_s1'):
            code, out, err = run_in(ROOT, tool + '.py')
            self.assertEqual(code, 0, tool + out[-2000:] + err[-2000:])
            want = doc['plant_lists'][tool]['ids']
            self.assertEqual([l.split(' ')[1] for l in out.splitlines() if l.startswith('PLANT ')], want, tool)
            self.assertEqual(E.check_output(out, code, selected=want), [], tool)

    def test_sabotage_unknown_id_m10_zero_work_successor_exit_2(self):
        code, out, err = run_in(ROOT, 'sabotage_m7.py', '--only', 'S99', isolated_site=False)
        self.assertEqual((code, 'sabotage cases 0  missed 0' in out), (0, True))
        code, out, err = run_in(ROOT, 'sabotage_m7_s1.py', '--only', 'S99')
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID unknown ids S99', out)
        self.assertEqual(E.check_output(out, code), [])

    def test_a_step_that_fails_on_the_clean_tree_is_no_catch(self):
        # S06's check, M7's R01, already fails on the unsabotaged M10 tree, so M10 reports CAUGHT whatever the plant does
        code, out, err = run_in(ROOT, 'run_regression_m7.py', '--step', 'R01', isolated_site=False)
        self.assertEqual(code, 1)
        self.assertIn('FAIL R01 ', out)
        code, out, err = run_in(ROOT, 'sabotage_m7.py', '--only', 'S06', isolated_site=False)
        self.assertIn('CAUGHT S06 ', out)
        code, out, err = run_in(ROOT, 'sabotage_m7_s1.py', '--only', 'S06')
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL cause=CHILD_FAILED R01=')
        self.assertIn('PLANT S06 NOT_RUN cause=control_start_FAIL', out)
        self.assertEqual(E.check_output(out, code, selected=['S06']), [])

    def test_a_target_that_is_not_there_exactly_once_fails_the_preflight(self):
        code, out, err = run_in(ROOT, 'sabotage_m7_s1.py', '--only', 'S07')
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR PREFLIGHT_INVALID_TARGET S07:occurrences=117,expected=1', out)
        self.assertEqual(E.check_output(out, code, selected=['S07']), [])

    def test_a_plant_on_a_test_step_is_caught_with_both_controls(self):
        code, out, err = run_in(ROOT, 'sabotage_m7_s1.py', '--only', 'S01')
        self.assertEqual(code, 0, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_PASS cause=ok R09=')
        self.assertRegex(out, r'(?m)^CONTROL end CONTROL_PASS cause=ok R09=')
        self.assertIn('PLANT S01 CAUGHT cause=R09', out)
        self.assertEqual(E.check_output(out, code, selected=['S01']), [])

    def test_the_history_contract_cases_mode_with_a_candidate(self):
        cand = os.path.join(self.tmp, 'cand')
        os.makedirs(os.path.join(cand, 'store_adapter'))
        with open(os.path.join(cand, 'store_adapter', '__init__.py'), 'w') as f:
            f.write('from apg.contracts.framework import ContractEnv\nfrom apg.reference_impl import FakeClock, StaticContextProvider, '
                    'InMemoryRecordStore, InMemoryAuditLog\n\ndef F():\n    c = FakeClock(); p = StaticContextProvider(c)\n'
                    '    return ContractEnv(p, InMemoryRecordStore(p), InMemoryAuditLog(p, c), c.advance)\n')
        code, out, err = run_in(ROOT, 'run_history_contract_s1.py', '--path', cand, '--factory', 'store_adapter:F')
        self.assertEqual(code, 0, out[-2000:] + err[-2000:])
        self.assertTrue(out.strip().splitlines()[-1].startswith('RESULT v=2 kind=cases tool=run_history_contract_s1 '))
        self.assertEqual(len([l for l in out.splitlines() if l.startswith('CASE record_store_history/RH-')]), 6)


class M8CallerModeAndTiers(unittest.TestCase):
    """Decisions M-1 and M8-T (owner, 2026-10-31 20:57).  M-1: run_m8_tests_s1 as sabotage_m8_s1's check is mode full, for that caller only,
    and a full run goes on after a failing test: plant S03 of M10's sabotage_m8 (applied to a copy) makes test_m8_dev01.py fail at its second
    test, and every one of the file's tests still has a result.  M8-T: m8_mutants_s1's tiers are M10's TIER1 without test_m8_boundary and
    M10's TIER2, pinned as the tool's oracle; a pinned oracle that differs stops the run (exit 2)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_m8mode_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_m1_profile_is_full_for_the_sabotage_caller_only(self):
        doc, _ = E.load_pins()
        self.assertEqual(E.runner_mode(doc, 'run_m8_tests_s1', 'sabotage_tool'), 'full')
        self.assertEqual(E.runner_mode(doc, 'run_m8_tests_s1', 'standalone'), 'full')
        self.assertEqual(E.runner_mode(doc, 'child_unittest_runner', 'm8_tier'), 'failfast')    # the mutation tiers are unchanged (F7)
        recs = [r for r in doc['change_records'] if any(c['entry'] == 'runner_profiles/run_m8_tests_s1@sabotage_tool' for c in r['changes'])]
        self.assertTrue(any('M-1' in r['cause'] for r in recs), 'no change record cites decision M-1')

    def test_m1_full_run_goes_on_after_a_failing_test(self):
        tree = os.path.join(self.tmp, 't')
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns(*E.FULL_TREE_IGNORE))
        plants = {c[0]: c for c in E.load_tool_module('sabotage_m8', ROOT).CASES}
        cid, what, fn, check = plants['S03']
        self.assertEqual(check, ['tools/run_m8_tests.py', '--file', 'test_m8_dev01.py'])
        fn(tree)
        code, out, err = run_in(tree, 'run_m8_tests_s1.py', '--caller', 'sabotage_tool', '--file', 'test_m8_dev01.py')
        self.assertEqual(code, 1, out[-2000:] + err[-2000:])
        self.assertEqual(E.check_output(out, code), [])
        res = [l for l in out.splitlines() if l.startswith('RESULT ')][-1]
        self.assertIn(' mode=full ', res)
        self.assertIn(' files_skipped_after_failure=0 ', res)
        doc, _ = E.load_pins()
        pinned = doc['test_files']['tests_m8/test_m8_dev01.py']['ids']
        st = [l.split()[-1] for l in out.splitlines() if l.startswith('TEST test_m8_dev01.py::')]
        self.assertEqual(len(st), len(pinned))
        self.assertNotIn('NOT_RUN_AFTER_FAILURE', st)
        first = next(i for i, x in enumerate(st) if x in ('FAIL', 'ERROR'))
        self.assertLess(first, len(st) - 1, 'the planted failure must not be the last test, or this proves nothing')
        self.assertTrue(any(x in ('PASS', 'FAIL', 'ERROR') for x in st[first + 1:]))
        self.assertRegex(out, r'(?m)^FILE test_m8_dev01\.py state=COMPLETED .* tests_not_run=0 ')

    def test_m8t_tiers_omit_only_the_boundary_test_and_are_pinned(self):
        M10 = E.load_tool_module('m8_mutants', ROOT)
        S1 = E.load_tool_module('m8_mutants_s1', ROOT)
        self.assertEqual(M10.TIER1.count('test_m8_boundary'), 1)
        self.assertEqual(S1.TIERS['tier1'], [t for t in M10.TIER1 if t != 'test_m8_boundary'])
        self.assertEqual(S1.TIERS['tier2'], M10.TIER2)
        cmds = S1.commands('/w', None)
        self.assertNotIn('tests_m8.test_m8_boundary', cmds[0][1])
        self.assertIn('tests_m8.test_m8_dependency', cmds[0][1])
        doc, _ = E.load_pins()
        self.assertEqual(doc['mutation_lists']['m8_mutants_s1']['oracle'], S1.TIERS)
        recs = [r for r in doc['change_records'] if any(c['entry'] == 'mutation_lists/m8_mutants_s1' and 'oracle' in (c.get('new') or {})
                                                         for c in r['changes'])]
        self.assertTrue(recs and 'M8-T' in recs[-1]['cause'])

    def test_m8t_a_different_pinned_oracle_stops_the_run(self):
        tree = tree_copy(os.path.join(self.tmp, 'o'))
        p = os.path.join(tree, 'tools', 'expected_counts.json')
        doc = json.load(open(p))
        doc['mutation_lists']['m8_mutants_s1']['oracle']['tier1'].append('test_m8_boundary')
        E.write_pins(doc, 'test: the boundary test put back in tier 1', 'tests_tools planted fault', [], path=p)
        code, out, err = run_in(tree, 'm8_mutants_s1.py', '--ids', 'MI-01')
        self.assertEqual(code, 2, out[-2000:] + err[-2000:])
        self.assertIn('RUN_ERROR EXPECTED_COUNT_MISMATCH m8_mutants_s1 oracle differs from the pinned oracle', out)
        self.assertIn('MUTANT MI-01 NOT_RUN', out)


W1A_COUNTS = {   # decision W-1A §1 (owner, 2026-11-01 06:22) as corrected by W-1B (11:32: G10 of run_f671/2/3_all W -> H): S-T, S-R, N, B, NW, P, H, W
    'run_m3_all': (1, 5, 1, 0, 0, 2, 4, 0), 'run_m4_all': (13, 1, 0, 0, 0, 1, 3, 0), 'run_m6_all': (20, 3, 0, 0, 0, 2, 5, 0),
    'run_m7_all': (12, 0, 0, 1, 0, 1, 1, 0), 'run_m71_all': (12, 0, 0, 1, 0, 2, 1, 0), 'run_m72_all': (13, 0, 0, 1, 0, 3, 1, 0),
    'run_m73_all': (14, 3, 0, 2, 0, 4, 1, 0), 'run_m8_all': (16, 0, 17, 0, 117, 0, 0, 0), 'run_m91_all': (4, 1, 0, 0, 0, 6, 12, 0),
    'run_m92_all': (5, 1, 0, 0, 0, 7, 14, 0), 'run_m93_all': (43, 7, 0, 0, 0, 11, 23, 0), 'run_m94_all': (44, 7, 0, 0, 0, 12, 25, 0),
    'run_f67_all': (13, 3, 0, 1, 0, 3, 1, 0), 'run_f671_all': (14, 3, 0, 1, 0, 3, 2, 0), 'run_f672_all': (14, 3, 0, 1, 0, 3, 2, 0),
    'run_f673_all': (14, 3, 0, 1, 0, 3, 2, 0), 'run_f674_all': (14, 3, 0, 1, 0, 3, 1, 1), 'run_mie1_all': (14, 0, 0, 1, 0, 3, 1, 0),
    'run_mie1_1_all': (14, 0, 0, 1, 0, 3, 1, 0)}
CLASSES = ('S-T', 'S-R', 'N', 'B', 'NW', 'P', 'H', 'W')


class WrappersW1A(unittest.TestCase):
    """Decision W-1 (owner, 2026-10-31 20:57) as corrected by W-1A (owner, 2026-11-01 06:22): the 19 successor wrappers.  Their plans
    against the adopted inventory; the 117 per-file groups of run_m8_all mapped one to one from M10's PER_FILE; the pins refusing a changed
    exclusion or check list; no historical command ever started; zero work; a CHECK whose tool differs from its pin; CHECK outcomes through
    a real wrapper; a W group; status OK with the M10 marker only when nothing is excluded."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_wrap_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_every_plan_matches_the_adopted_inventory(self):
        doc, _ = E.load_pins()
        tot = dict.fromkeys(CLASSES, 0)
        for m, want in W1A_COUNTS.items():
            winv = doc['wrapper_inventories'][m + '_s1']
            _, plan = E.wrapper_plan(m + '_s1', m, ROOT, doc, winv['m10_sha256'])
            got = tuple(sum(1 for g in plan if g['class'] == c) for c in CLASSES)
            self.assertEqual(got, want, m)
            self.assertEqual([g['id'] for g in plan], [E.group_id(i) for i in range(1, len(plan) + 1)])
            self.assertEqual(len(doc['exclusion_lists'][m + '_s1']), want[6], m)
            self.assertEqual(len(doc['check_lists'][m + '_s1']), want[2] + want[3] + want[5] + want[7], m)
            for c, n in zip(CLASSES, got):
                tot[c] += n
        self.assertEqual(tot, {'S-T': 294, 'S-R': 43, 'N': 18, 'B': 12, 'NW': 117, 'P': 72, 'H': 100, 'W': 1})     # W-1B: 454 / 103 / 100
        self.assertEqual(E.W1A_GROUPS_CSV_SHA256, '0fe5b28b00920610acd5348ec17c96740daf52434bc0c92224617053f27f899a')
        self.assertEqual(E.W1A_EXCLUSIONS_CSV_SHA256, 'e2f80c2299806c5db89296330c0f7471abfbf600a708c579ea33779398a9cfd3')

    def test_run_m8_all_per_file_groups_map_one_to_one(self):
        doc, _ = E.load_pins()
        winv = doc['wrapper_inventories']['run_m8_all_s1']
        m, plan = E.wrapper_plan('run_m8_all_s1', 'run_m8_all', ROOT, doc, winv['m10_sha256'])
        nw = [g for g in plan if g['class'] == 'NW']
        F = sys.modules['run_f674_all']
        self.assertEqual(len(nw), len(F.PER_FILE))
        self.assertEqual(len(nw), 117)
        for k, (g, (name, _n)) in enumerate(zip(nw, F.PER_FILE), 1):
            self.assertEqual(g['m10_cmd'], ['tools/run_f674_all.py', '--file', str(k)])     # M10's order
            self.assertEqual(g['files'], ['tests/' + name])
            self.assertEqual(g['run'], ['tools/run_test_files_s1.py', '--caller', 'wrapper', '-q', name])
        names = [g['files'][0] for g in nw]
        self.assertEqual(len(set(names)), 117)
        on_disk = sorted('tests/' + f for f in os.listdir(os.path.join(ROOT, 'tests')) if f.startswith('test_') and f.endswith('.py'))
        self.assertEqual(sorted(names), on_disk)
        self.assertFalse(any(g.get('run', [''])[0].endswith('_all_s1.py') for g in plan))      # no wrapper calls a wrapper

    def _copy(self, name):
        return tree_copy(os.path.join(self.tmp, name))

    def _repin(self, tree, fn):
        p = os.path.join(tree, 'tools', 'expected_counts.json')
        doc = json.load(open(p, encoding='utf-8'))
        fn(doc)
        E.write_pins(doc, 'test: planted change', 'tests_tools planted fault', [], path=p)

    def test_a_changed_exclusion_or_check_list_is_refused(self):
        tree = self._copy('excl')
        self._repin(tree, lambda d: d['exclusion_lists']['run_m4_all_s1'].pop('G18'))
        code, out, err = run_in(tree, 'run_m4_all_s1.py', '--group', '14')
        self.assertEqual(code, 2, out[-2000:] + err[-2000:])
        self.assertIn('RUN_ERROR EXCLUSION_LIST_MISMATCH run_m4_all_s1 pinned 2, table 3', out)
        self.assertRegex(out, r'(?m)^CHECK G14 NOT_RUN ')
        tree = self._copy('excl2')
        self._repin(tree, lambda d: d['exclusion_lists']['run_m4_all_s1'].__setitem__('G14', E.excluded_line('G14', 'APG-M4', 'records_check_of_its_own_release', '0' * 64)))
        code, out, err = run_in(tree, 'run_m4_all_s1.py', '--group', '14')
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR EXCLUSION_LIST_MISMATCH', out)
        tree = self._copy('chk')
        self._repin(tree, lambda d: d['check_lists']['run_m4_all_s1'].pop('G14'))
        code, out, err = run_in(tree, 'run_m4_all_s1.py', '--group', '15')
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR CHECK_LIST_MISMATCH run_m4_all_s1 pinned 0, table 1', out)

    def test_no_historical_command_is_ever_started_and_zero_work_is_refused(self):
        tree = self._copy('h')
        flag = os.path.join(self.tmp, 'H_STARTED')
        for t in ('programme_check_m4.py', 'programme_check_m3.py', 'run_regression_m4.py'):
            with open(os.path.join(tree, 'tools', t), 'w') as f:
                f.write('open(%r, "a").write("started\\n")\n' % flag)
        code, out, err = run_in(tree, 'run_m4_all_s1.py', '--range', '16-18')
        self.assertEqual(code, 2, out[-2000:] + err[-2000:])
        self.assertTrue(out.strip().splitlines()[-1].endswith(' status=EVIDENCE_ERROR exit=2'))
        self.assertEqual(len([l for l in out.splitlines() if l.startswith('EXCLUDED G1')]), 3)
        self.assertEqual(E.check_output(out, code), [])
        code, out, err = run_in(tree, 'run_m4_all_s1.py', '--range', '14-18')
        self.assertEqual(code, 0, out[-2000:] + err[-2000:])
        self.assertEqual(E.wrapper_verdict(out, code), 'OK_WITH_EXCLUSIONS')
        self.assertIn('PASSED WITH 3 HISTORICAL CHECKS NOT RUN (listed above as EXCLUDED)', out)
        self.assertNotIn('ALL M4 CHECKS PASS', out)
        self.assertFalse(os.path.exists(flag), 'a historical command was started')

    def test_a_check_whose_tool_differs_from_its_pin_is_an_item_error(self):
        tree = self._copy('pin')
        with open(os.path.join(tree, 'tools', 'run_golden_fin.py'), 'a') as f:
            f.write('\n# changed\n')
        code, out, err = run_in(tree, 'run_m4_all_s1.py', '--group', '14')
        self.assertEqual(code, 2, out[-2000:] + err[-2000:])
        self.assertRegex(out, r'(?m)^CHECK G14 ITEM_ERROR source=child exit=- marker=- ')
        self.assertIn('the tool, command or marker differs from the pin', out)

    def test_check_outcomes_through_a_real_wrapper(self):
        for name, body, code_want, outcome in (('fail', 'import sys\nprint("GOLDEN OK")\nsys.exit(1)\n', 1, 'FAIL source=child exit=1 marker=seen'),
                                               ('nomarker', 'print("something else")\n', 2, 'ITEM_ERROR source=child exit=0 marker=absent'),
                                               ('pass', 'print("GOLDEN OK")\n', 0, 'PASS source=child exit=0 marker=seen')):
            tree = self._copy('o_' + name)
            tp = os.path.join(tree, 'tools', 'run_golden_fin.py')
            with open(tp, 'w') as f:
                f.write(body)

            def fix(d, tp=tp):
                old = d['check_lists']['run_m4_all_s1']['G14'].split(' ')
                d['check_lists']['run_m4_all_s1']['G14'] = E.check_identity('G14', old[1], old[2], E.sha256_file(tp), old[4])
            self._repin(tree, fix)
            code, out, err = run_in(tree, 'run_m4_all_s1.py', '--group', '14')
            self.assertEqual(code, code_want, (name, out[-2000:] + err[-2000:]))
            self.assertRegex(out, r'(?m)^CHECK G14 %s ' % outcome)
            self.assertEqual(E.check_output(out, code), [])

    def test_a_wrapper_check_and_status_ok_with_the_m10_marker(self):
        code, out, err = run_in(ROOT, 'run_f674_all_s1.py', '--group', '10')
        self.assertEqual(code, 0, out[-2000:] + err[-2000:])
        self.assertRegex(out, r'(?m)^CHECK G10 PASS source=wrapper exit=- marker=- ')
        self.assertEqual(E.wrapper_verdict(out, code), 'OK')
        self.assertEqual(out.strip().splitlines()[-2], 'groups 1  failed 0')       # the M10 marker, only with status=OK



class WrappersW1B(unittest.TestCase):
    """Decision W-1B option (a) (owner, 2026-11-01 11:32): a built-in check that fails on clean M10 and is listed individually in the
    adopted exclusion list is class H, EXCLUDED and never evaluated (W-1B.1); it is NOT RUN, never a pass, and the wrapper reports at best
    OK_WITH_EXCLUSIONS without M10's marker (W-1B.2); a built-in check that passes on clean M10 stays W and runs; --pin accepts only the
    adopted v3 files."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_w1b_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _in_process(self, tool, m10, argv):
        import contextlib, io
        seen = []
        real = E._run_check

        def recorder(g, *a, **k):
            seen.append(g['id'])
            return real(g, *a, **k)
        buf = io.StringIO()
        with mock.patch.object(E, '_run_check', side_effect=recorder), contextlib.redirect_stdout(buf):
            code = E.wrapper_main(tool, m10, argv)
        return code, buf.getvalue(), seen

    def test_the_three_built_in_checks_are_h_and_the_fourth_stays_w(self):
        doc, _ = E.load_pins()
        empty = E.EMPTY_SHA256
        for m, rel in (('run_f671_all', 'APG-F67.1'), ('run_f672_all', 'APG-F67.2'), ('run_f673_all', 'APG-F67.3')):
            t = m + '_s1'
            _, plan = E.wrapper_plan(t, m, ROOT, doc, doc['wrapper_inventories'][t]['m10_sha256'])
            g10 = plan[9]
            self.assertEqual((g10['id'], g10['class'], g10['m10_cmd']), ('G10', 'H', None))
            self.assertEqual(doc['exclusion_lists'][t]['G10'], E.excluded_line('G10', rel, 'records_check_of_its_own_release', empty))
            self.assertNotIn('G10', doc['check_lists'][t])
        _, plan = E.wrapper_plan('run_f674_all_s1', 'run_f674_all', ROOT, doc, doc['wrapper_inventories']['run_f674_all_s1']['m10_sha256'])
        self.assertEqual((plan[9]['class'], plan[9]['m10_cmd']), ('W', None))
        self.assertIn('G10', doc['check_lists']['run_f674_all_s1'])
        self.assertEqual(E.W1B_GROUPS_CSV_SHA256, 'f559ec57a50a045c36e8faedb9d1574315fb45c023046287264568fbe2fbb7c9')
        self.assertEqual(E.W1B_EXCLUSIONS_CSV_SHA256, '266eea0dd870452921a19b52bff2c64eb9aa0b42a5f579ecffba33da9a28e479')

    def test_an_excluded_built_in_check_is_never_evaluated_and_never_a_pass(self):
        code, out, seen = self._in_process('run_f671_all_s1', 'run_f671_all', ['--range', '10-11'])
        self.assertEqual(code, 0, out[-3000:])
        self.assertEqual(seen, [], 'an excluded built-in check was evaluated')
        self.assertRegex(out, r'(?m)^EXCLUDED G10 NOT_RUN_HISTORICAL release=APG-F67\.1 reason=records_check_of_its_own_release command_sha256=%s$' % E.EMPTY_SHA256)
        self.assertNotRegex(out, r'(?m)^CHECK G10 ')
        self.assertIn('NOT RUN G10: The suite groups below cover every test file in tests/ exactly once (historical check of an earlier release, excluded)', out)
        self.assertEqual(E.check_output(out, code), [])
        self.assertEqual(E.wrapper_verdict(out, code), 'OK_WITH_EXCLUSIONS')
        f = E.parse_result_line(out.strip().splitlines()[-1])[1]
        self.assertEqual((f['excluded_historical'], f['checks_passed'], f['checks_selected']), (1, 0, 0))
        self.assertNotIn('groups 2  failed 0', out)                    # M10's marker never appears with an exclusion
        self.assertIn('PASSED WITH 1 HISTORICAL CHECK NOT RUN (listed above as EXCLUDED)', out)
        code, out, seen = self._in_process('run_f674_all_s1', 'run_f674_all', ['--group', '10'])
        self.assertEqual((code, seen), (0, ['G10']), out[-3000:])        # the built-in check that passes on clean M10 still runs
        self.assertRegex(out, r'(?m)^CHECK G10 PASS source=wrapper ')

    def test_a_built_in_h_group_missing_from_the_exclusion_list_is_refused(self):
        tree = tree_copy(os.path.join(self.tmp, 'x'))
        p = os.path.join(tree, 'tools', 'expected_counts.json')
        doc = json.load(open(p, encoding='utf-8'))
        doc['exclusion_lists']['run_f672_all_s1'].pop('G10')
        E.write_pins(doc, 'test: G10 taken out of the exclusion list', 'tests_tools planted fault', [], path=p)
        code, out, err = run_in(tree, 'run_f672_all_s1.py', '--group', '11')
        self.assertEqual(code, 2, out[-2000:] + err[-2000:])
        self.assertIn('RUN_ERROR EXCLUSION_LIST_MISMATCH run_f672_all_s1 pinned 1, table 2', out)
        self.assertRegex(out, r'(?m)^FILE G11 state=NOT_RUN ')

    def test_pin_accepts_only_the_adopted_v3_files(self):
        work = os.path.join(self.tmp, 'csv')
        os.makedirs(work)
        g, x = os.path.join(work, 'g.csv'), os.path.join(work, 'x.csv')
        with open(g, 'w') as f:
            f.write('wrapper,group_id,label,command,marker,class,on_clean_m10,exit,last_line\n')
        with open(x, 'w') as f:
            f.write('wrapper,group_id\n')
        lines, code = E.wrapper_pin('run_f671_all_s1', 'run_f671_all', g, x, 'test', 'test', ROOT)
        self.assertEqual(code, 2)
        self.assertTrue(lines[0].startswith('RUN_ERROR PIN_INVALID g.csv is not the adopted file (SHA-256 f559ec57'), lines)



# (block, M10 tool, arguments, M10 exit, a text M10 prints, stub tool for a mutation tool's copy or None)
SELECTOR_CASES = [
    ('P1-F5', 'run_m2_tests', ['-q', 'nomatch_*.py'], 0, 'tests 0  failures 0  errors 0', None),
    ('P1-F5', 'mut_runner', ['test_nope.py'], 1, 'test_nope', None),
    ('P1-F5', 'run_contracts', ['--suite', 'nope'], 0, 'ALL CONTRACT CASES PASS', None),
    ('P2-B8', 'run_fin_corpus', ['--only', 'NOPE'], 0, 'ALL CORPUS CASES PASS', None),
    ('P2-B8', 'run_m3_contracts', ['--suite', 'nope'], 0, 'ALL CONTRACT CASES PASS', None),
    ('P2-B8', 'm3_mutants', ['--only', 'ZZ'], 0, 'MUTATION RUN OK', 'm3'),
    ('P2-B8', 'm4_mutants', ['--ids', 'NOPE'], 0, 'MUTATION RUN OK', 'm4'),
    ('P3-B03', 'm5_mutants', ['--ids', 'DT-x-999'], 0, 'MUTATION RUN OK', 'm5'),
    ('P3-B03', 'm5_mutants', ['--ids', '<valid>,NOPE'], 0, 'MUTATION RUN OK', 'm5'),
    ('P3-B03', 'm5_mutants', ['--only', 'QQ'], 0, 'MUTATION RUN OK', 'm5'),
    ('P4-B15', 'm6_mutants', ['--ids', 'NOPE'], 0, 'MUTATION RUN OK', 'm6'),
    ('P4-B15', 'm6_mutants', ['--ids', '<valid>,NOPE'], 0, 'MUTATION RUN OK', 'm6'),
    ('P4-B15', 'run_mkt_corpus', ['--only', 'NOPE'], 0, 'ALL CORPUS CASES PASS', None),
    ('P3-B03', 'run_det_corpus', ['--only', 'NOPE'], 0, 'ALL CORPUS CASES PASS', None),
    ('P5-B06', 'run_m7_all', ['--group', '0'], 0, 'groups 1  failed 0', None),       # M10 runs the last group
    ('P5-B06', 'run_m7_all', ['--range', '5-3'], 0, 'groups 0  failed 0', None),
    ('P5-B06', 'm7_mutants', ['--ids', 'NOPE'], 0, 'MUTATION RUN OK', 'm7'),
    ('P7-B3', 'run_m8_tests', ['--file'], 0, 'M8 tests 0 in 0 files, failed files 0', None),
    ('P7-B3', 'sabotage_m8', ['--only', 'S99'], 0, 'sabotage cases 0: caught 0, missed 0, incomplete 0', None),
    ('P7-B3', 'sabotage_m10', ['--only', 'Z99'], 0, 'sabotage 0  caught 0', None),
    ('P7-B3', 'm8_mutants', ['--batch', '0/4'], 0, 'mutants 0: killed 0', 'm8'),
    ('P7-B3', 'run_m8_all', ['--range', '5-3'], 0, 'groups 0  failed 0  incomplete 0', None),
    ('P7-B3', 'run_m8_all', ['--group', '0'], 0, 'groups 1  failed 0  incomplete 0', None),     # M10 runs the last group
]


class SelectorsThatDoNoWorkExitTwo(unittest.TestCase):
    """P1-F5, P2-B8, P3-B03, P4-B15, P5-B06, P7-B3 (each with its (R4) addition): a selection that names nothing, names an unknown or
    partly unknown id, or is out of range.  On M10 each exits 0 (mut_runner with an unknown file exits 1; run_m7_all and run_m8_all with
    --group 0 run the LAST group), mostly after zero work; on the successor each exits 2 before any work, with its RUN_ERROR line and a
    RESULT v=2 line ending exit=2 that the §2.7 checker accepts.  For a mutation tool given a valid id beside an unknown one, M10 runs the
    valid one (its child replaced by a failing stub, so the run is short) and ignores the other.  M10's m8_mutants runs its control first;
    its tier modules are stubbed in the copy so that the control is short."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_sel_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def _add_selector_cases():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import test_mutation_timeout as H
    for n, (block, tool, args, m10_code, m10_text, stub) in enumerate(SELECTOR_CASES, 1):
        def t(self, tool=tool, args=args, m10_code=m10_code, m10_text=m10_text, stub=stub):
            if '<valid>,NOPE' in args:
                args = [a.replace('<valid>', H.first_mutant(stub)) for a in args]
            for side in ('m10', 's1'):
                tree = os.path.join(self.tmp, side)
                if stub and stub != 'm8':
                    H.stub_tree(tree, stub, 'failed', side)
                else:
                    tree_copy(tree)
                    if stub == 'm8' and side == 'm10':
                        M = E.load_tool_module('m8_mutants', ROOT)
                        for mod in M.TIER1 + M.TIER2:
                            with open(os.path.join(tree, 'tests_m8', mod + '.py'), 'w', encoding='utf-8') as fh:
                                fh.write(H.M8_M10_TIER_STUB % {'mode': 'ok', 'target': M.MUTANTS[0][1], 'old': M.MUTANTS[0][2], 'sleep': 1})
                code, out, err = H.run_tool(tree, tool + ('.py' if side == 'm10' else '_s1.py'), args, site=(side == 'm10'))
                shutil.rmtree(tree, ignore_errors=True)
                if side == 'm10':
                    self.assertEqual(code, m10_code, (tool, args, out[-1500:], err[-1500:]))
                    self.assertIn(m10_text, out)
                    self.assertNotRegex(out, r'(?m)^RESULT ')
                    if args == ['--group', '0']:      # M10 ran its LAST group
                        doc, _ = E.load_pins()
                        last = doc['wrapper_inventories'][tool + '_s1']['groups'][-1]['label']
                        self.assertIn(last, out)
                else:
                    self.assertEqual(code, 2, (tool, args, out[-2000:], err[-1500:]))
                    self.assertRegex(out, r'(?m)^RUN_ERROR (SELECTION_INVALID|TEST_FILE_NOT_IN_PINS) ')
                    last = out.strip().splitlines()[-1]
                    self.assertTrue(last.startswith('RESULT v=2 ') and last.endswith(' exit=2'), last)
                    self.assertEqual(E.check_output(out, code), [])
                    if m10_text in ('ALL CONTRACT CASES PASS', 'ALL CORPUS CASES PASS', 'MUTATION RUN OK'):
                        self.assertNotIn(m10_text, out)     # M10's success marker only on exit 0 (§2.4); its count lines are kept
        setattr(SelectorsThatDoNoWorkExitTwo, 'test_%02d_%s_%s' % (n, block.replace('-', '_'), tool), t)


_add_selector_cases()



RUNNER_STUB = """import sys
# planted by tests_tools/test_runner_zero_work.py: the test runner a wrapper starts, replaced in a temporary copy
print(%r)
sys.exit(%d)
"""


class WrapperWithAStubTestRunner(unittest.TestCase):
    """P4-B17 and P2-B8, each with its (R4) addition: a wrapper whose test runner is replaced in a temporary copy by a stub.
    On M10, run_m6_all and run_m4_all with a run_m2_tests.py stub that prints 'tests 0  failures 0  errors 0' and exits 0 report PASS for
    every one of their test-runner groups (20 and 13), which ran no test.  (run_m6_all's whole-run marker ALL M6 CHECKS PASS is not
    reachable in this tree, because its historical groups fail on clean M10, W-1A; the defect is the per-group PASS.)  On the successor,
    run_m6_all_s1 --group 1 and run_m4_all_s1 --group 1 with the same stub as run_m2_tests_s1.py: the child ended through its own exit
    with its RESULT line missing, so the group is ITEM_ERROR and the wrapper EVIDENCE_ERROR, exit 2 (T-0 (R4) expect_line, adopted for
    S groups by W-1 section 1.2 (a)).  A stub that dies by a signal with no result is a crash: INDETERMINATE, exit 3 (section 2.7).  The
    further successor stubs: a valid line with zero tests against the pinned file -> exit 2; a valid line with a file INDETERMINATE (child
    exit 3) -> exit 3; a valid FAILED line -> exit 1; a valid line saying exit=0 from a stub that exits 1 -> exit 2."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_wstub_')
        self.pins, _ = E.load_pins()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def tree(self, name, runner, text, code):
        t = tree_copy(os.path.join(self.tmp, name))
        with open(os.path.join(t, 'tools', runner), 'w', encoding='utf-8') as fh:
            fh.write(RUNNER_STUB % (text, code))
        return t

    def lines(self, rel, statuses=None, state='COMPLETED', zero=False):
        fp = E.test_file_pins(self.pins, [rel])
        name = os.path.basename(rel)
        pin = fp[name]
        if zero:
            res = {name: E.FileResult(name, 'COMPLETED', [], pin['sha256'])}
        else:
            st = statuses or ['PASS'] * len(pin['ids'])
            res = {name: E.FileResult(name, state, [] if state == 'INDETERMINATE' else list(zip(pin['ids'], st)), pin['sha256'],
                                      cause='timeout' if state == 'INDETERMINATE' else '')}
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', [name], res, fp)
        return '\n'.join(lines), code

    def test_m10_wrapper_passes_every_zero_work_group(self):
        for wrapper, prefix, n in (('run_m6_all.py', 'M6 unit tests: ', 20), ('run_m4_all.py', 'M4 unit tests: ', 13)):
            with self.subTest(wrapper=wrapper):
                t = self.tree('m10_' + wrapper, 'run_m2_tests.py', 'tests 0  failures 0  errors 0', 0)
                code, out, err = run_in(t, wrapper, isolated_site=False)
                groups = [l for l in out.splitlines() if l.startswith(('PASS ' + prefix, 'FAIL ' + prefix))]
                self.assertEqual(len(groups), n, out[-3000:])
                for l in groups:
                    self.assertTrue(l.startswith('PASS ') and l.endswith('[tests 0  failures 0  errors 0]'), l)   # PASS from zero tests

    def run_s1(self, name, wrapper, text, code):
        t = self.tree(name, 'run_m2_tests_s1.py', text, code)
        c, out, err = run_in(t, wrapper, '--group', '1')
        self.assertEqual(E.check_output(out, c), [], out[-2000:])
        return c, out

    def test_successor_wrapper_refuses_the_zero_work_stub(self):
        for wrapper in ('run_m6_all_s1.py', 'run_m4_all_s1.py'):
            with self.subTest(wrapper=wrapper):
                c, out = self.run_s1('zw_' + wrapper, wrapper, 'tests 0  failures 0  errors 0', 0)
                self.assertEqual(c, 2, out[-2000:])
                self.assertRegex(out, r'(?m)^FILE G01 state=ITEM_ERROR tests=0 ')
                self.assertTrue(out.strip().splitlines()[-1].endswith(' status=EVIDENCE_ERROR exit=2'))
                self.assertNotIn('ALL M4 CHECKS PASS', out)
                self.assertNotIn('ALL M6 CHECKS PASS', out)

    def test_successor_wrapper_a_child_killed_by_a_signal_is_indeterminate(self):
        t = tree_copy(os.path.join(self.tmp, 'sig'))
        with open(os.path.join(t, 'tools', 'run_m2_tests_s1.py'), 'w', encoding='utf-8') as fh:
            fh.write('import os, signal\nos.kill(os.getpid(), signal.SIGKILL)\n')
        c, out, err = run_in(t, 'run_m6_all_s1.py', '--group', '1')
        self.assertEqual(c, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^FILE G01 state=INDETERMINATE ')
        self.assertTrue(out.strip().splitlines()[-1].endswith(' status=INDETERMINATE exit=3'))
        self.assertEqual(E.check_output(out, c), [])

    def test_successor_wrapper_further_stubs(self):
        rel = 'tests/test_mkt_policy.py'
        n = len(self.pins['test_files'][rel]['ids'])
        text0, _ = self.lines(rel, zero=True)
        text3, code3 = self.lines(rel, state='INDETERMINATE')
        text1, code1 = self.lines(rel, ['FAIL'] + ['PASS'] * (n - 1))
        text_ok, code_ok = self.lines(rel)
        self.assertEqual((code3, code1, code_ok), (3, 1, 0))
        for name, text, code, want in (('zero_vs_pin', text0, 2, 2), ('indeterminate', text3, 3, 3), ('failed', text1, 1, 1),
                                       ('exit_contradicts', text_ok, 1, 2)):
            with self.subTest(case=name):
                c, out = self.run_s1(name, 'run_m6_all_s1.py', text, code)
                self.assertEqual(c, want, out[-2000:])
                self.assertTrue(out.strip().splitlines()[-1].endswith(' exit=%d' % want))



class RefusalsEndWithAResultLine(unittest.TestCase):
    """§2.7 and P7-B3 (R4): a run that a successor refuses before any work still ends with its RUN_ERROR line and one RESULT v=2 line
    (every item NOT_RUN cause=run_error, exit 2) that the checker accepts: --batch in the nine mutation tools that refuse it (M10's
    --batch K/N slices the list; the successors take exact --ids), and --timeout in sabotage_m8_s1 (fixed at M10's default)."""

    def test_each_refusal(self):
        cases = [('%s_mutants_s1.py' % t, ['--batch', '1/4'], '--batch is not supported')
                 for t in ('f67', 'f671', 'f672', 'f673', 'f674', 'm73_store', 'mie', 'mie11', 'm8')]
        cases.append(('sabotage_m8_s1.py', ['--timeout', '5'], '--timeout is fixed'))
        for script, args, text in cases:
            with self.subTest(script=script):
                code, out, err = run_in(ROOT, script, *args)
                self.assertEqual(code, 2, out[-1500:] + err[-1500:])
                self.assertRegex(out, r'(?m)^RUN_ERROR SELECTION_INVALID %s' % re.escape(text))
                last = out.strip().splitlines()[-1]
                self.assertTrue(last.startswith('RESULT v=2 ') and ' started=0 ' in last and last.endswith(' status=EVIDENCE_ERROR exit=2'), last)
                self.assertNotRegex(out, r'(?m)^(MUTANT|PLANT) \S+ (?!NOT_RUN)')
                self.assertEqual(E.check_output(out, code), [])

if __name__ == '__main__':
    unittest.main()
