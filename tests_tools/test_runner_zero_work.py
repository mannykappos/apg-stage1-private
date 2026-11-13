"""Stage 1 (APG-M11-S1), Workstream T, P1-F5, P2-B8, P3-B03, P4-B15, P5-B06, P7-B3 and T-0: no runner may report success after zero or
partial work.  Helper level: the pinned counts (R1_REQUIREMENTS.md §2.2) and the zero-work and selection rules of §2.7; the runner-level
cases are added with each successor runner (kind=cases: class CasesRunners, M10 against the successor).
Run from the package root:  python3 -I -S tests_tools/test_runner_zero_work.py      BUILDER-EXECUTED: NOT INDEPENDENT."""
import json
import json as _json
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
            self.assertTrue(lines[-1].startswith('RESULT v=3 kind=cases tool=%s ' % tool), tool)
            self.assertRegex(lines[-2], r'^ALL (CONTRACT|CORPUS) CASES PASS$', tool)  # the M10 marker, kept, just before RESULT
            self.assertEqual(E.check_output(out, code, pins=inv, selected=want), [], tool)

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
        self.assertTrue(out.strip().splitlines()[-1].startswith('RESULT v=3 kind=cases tool=run_history_contract_s1 '))
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
        S1.load()      # corrective pass 2, C.1
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
        self.assertEqual(E.check_output(out, code), [], out[-2000:])          # corrective pass 2, E point 25



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
        self.assertEqual(E.check_output(out, code), [], out[-2000:])          # corrective pass 2, E point 25

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




class E25StubbedChildGroups(unittest.TestCase):
    """Corrective pass 2, E point 25: one stubbed-child group run each of run_m7_all_s1 (G03, a test-file group) and run_m8_all_s1 (G03),
    their test runner replaced in a temporary copy by a stub that ran no test and exits 0: the group ITEM_ERROR, exit 2, and the output
    accepted by check_output.  (The --group 0 and --range 5-3 refusals of both wrappers go through check_output in
    SelectorsThatDoNoWorkExitTwo; run_f672_all_s1 --group 11 and run_f674_all_s1 --group 10 in WrappersW1B.)  BUILDER-EXECUTED: NOT INDEPENDENT."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_e25_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_stubbed_child_group_of_each(self):
        for wrapper, runners in (('run_m7_all_s1.py', ('run_m2_tests_s1.py', 'run_test_files_s1.py')), ('run_m8_all_s1.py', ('run_m8_tests_s1.py',))):
            with self.subTest(wrapper=wrapper):
                t = tree_copy(os.path.join(self.tmp, wrapper))
                for r in runners:
                    with open(os.path.join(t, 'tools', r), 'w', encoding='utf-8') as fh:
                        fh.write(RUNNER_STUB % ('tests 0  failures 0  errors 0', 0))
                code, out, err = run_in(t, wrapper, '--group', '3')
                self.assertEqual(code, 2, out[-2000:] + err[-2000:])
                self.assertRegex(out, r'(?m)^FILE G03 state=ITEM_ERROR ')
                self.assertTrue(out.strip().splitlines()[-1].endswith(' status=EVIDENCE_ERROR exit=2'))
                self.assertEqual(E.check_output(out, code), [], out[-2000:])


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
                    self.assertTrue(last.startswith(('RESULT v=2 ', 'RESULT v=3 ')) and last.endswith(' exit=2'), last)
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



TWELVE_WRAPPERS = ['run_m3_all', 'run_f67_all', 'run_f673_all', 'run_m71_all', 'run_m72_all', 'run_m73_all', 'run_m91_all', 'run_m92_all',
                   'run_m93_all', 'run_m94_all', 'run_mie1_all', 'run_mie1_1_all']

MAPPED_STUB = """import sys
# planted by tests_tools/test_runner_zero_work.py: run_m2_tests_s1 replaced in a temporary copy; it answers per selected file
TEXTS = %r
name = sys.argv[-1]
text, code = TEXTS.get(name, TEXTS['*'])
print(text)
sys.exit(code)
"""


def test_groups(m):
    doc, _ = E.load_pins()
    _, plan = E.wrapper_plan(m + '_s1', m, ROOT, doc, doc['wrapper_inventories'][m + '_s1']['m10_sha256'])
    return plan, [g for g in plan if g['class'] == 'S-T']


class TheTwelveWrappersWithAStubTestRunner(unittest.TestCase):
    """Authorisation §4.4 for the 12 successor wrappers that had no test of their own (deviation D10, closed by this class):
    run_m3_all_s1, run_f67_all_s1, run_f673_all_s1, run_m71/m72/m73_all_s1, run_m91/m92/m93/m94_all_s1, run_mie1_all_s1, run_mie1_1_all_s1.
    Each is run as the real wrapper on a temporary copy, on its first test-runner (S-T) group, with run_m2_tests_s1.py replaced by a stub:
      - zero work (prints M10's 'tests 0  failures 0  errors 0', exits 0, no RESULT line) -> the group ITEM_ERROR, exit 2;
      - killed by a signal with no result -> INDETERMINATE, exit 3;
      - a valid FAILED line for the group's pinned files -> the group COMPLETED with its failure counted, exit 1, no M10 marker;
      - a valid OK line from a stub that exits 1 (the line contradicts the exit) -> ITEM_ERROR, exit 2;
      - a valid OK line, exit 0 -> the group passes, exit 0 (the control case).
    The checker accepts every output.  P2-B8's M10 half for run_m3_all: with the same zero-work stub as tools/run_m2_tests.py, M10's
    run_m3_all reports PASS for its test group, which ran no test.  DP-2.3 F5 (wrappers run full): with a failing first group, the next
    group still runs and is reported."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_twelve_')
        self.pins, _ = E.load_pins()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def text(self, files, fail=False):
        fp = E.test_file_pins(self.pins, files)
        res = {}
        for k, rel in enumerate(files):
            n = os.path.basename(rel)
            st = ['PASS'] * len(fp[n]['ids'])
            if fail and k == 0:
                st[0] = 'FAIL'
            res[n] = E.FileResult(n, 'COMPLETED', list(zip(fp[n]['ids'], st)), fp[n]['sha256'])
        lines, code = E.finish_tests('run_m2_tests_s1', 'full', 'r', [os.path.basename(r) for r in files], res, fp)
        return '\n'.join(lines), code

    def run_group(self, m, name, stub_source, gid):
        t = tree_copy(os.path.join(self.tmp, '%s_%s' % (m, name)))
        with open(os.path.join(t, 'tools', 'run_m2_tests_s1.py'), 'w', encoding='utf-8') as fh:
            fh.write(stub_source)
        c, out, err = run_in(t, m + '_s1.py', '--group', str(int(gid[1:])))
        shutil.rmtree(t, ignore_errors=True)
        self.assertEqual(E.check_output(out, c), [], (m, name, out[-2000:], err[-1500:]))
        return c, out

    def test_m10_run_m3_all_passes_its_zero_work_test_group(self):
        t = tree_copy(os.path.join(self.tmp, 'm10_m3'))
        with open(os.path.join(t, 'tools', 'run_m2_tests.py'), 'w', encoding='utf-8') as fh:
            fh.write(RUNNER_STUB % ('tests 0  failures 0  errors 0', 0))
        code, out, err = run_in(t, 'run_m3_all.py', isolated_site=False)
        self.assertRegex(out, r'(?m)^PASS All unit, adversarial and golden tests .*\[tests 0  failures 0  errors 0\]$')

    def test_wrapper_full_mode_runs_the_next_group_after_a_failing_one(self):
        plan, st = test_groups('run_m71_all')
        k = next(i for i in range(len(plan) - 1) if plan[i]['class'] == plan[i + 1]['class'] == 'S-T'
                 and len(plan[i]['files']) == len(plan[i + 1]['files']) == 1)
        g1, g2 = plan[k], plan[k + 1]
        texts = {os.path.basename(g1['files'][0]): self.text(g1['files'], fail=True),
                 os.path.basename(g2['files'][0]): self.text(g2['files']), '*': ('unexpected', 2)}
        t = tree_copy(os.path.join(self.tmp, 'cont'))
        with open(os.path.join(t, 'tools', 'run_m2_tests_s1.py'), 'w', encoding='utf-8') as fh:
            fh.write(MAPPED_STUB % texts)
        c, out, err = run_in(t, 'run_m71_all_s1.py', '--range', '%d-%d' % (k + 1, k + 2))
        self.assertEqual(c, 1, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^FILE %s state=COMPLETED .* failed=[1-9]' % g1['id'])
        self.assertRegex(out, r'(?m)^FILE %s state=COMPLETED .* failed=0 ' % g2['id'])
        last = out.strip().splitlines()[-1]
        self.assertIn(' mode=full ', last)
        self.assertEqual(E.check_output(out, c), [])


def _add_twelve_cases():
    for m in TWELVE_WRAPPERS:
        def t(self, m=m):
            plan, st = test_groups(m)
            g = ([x for x in st if len(x['files']) == 1] or st)[0]
            gid = g['id']
            ok, okc = self.text(g['files'])
            bad, badc = self.text(g['files'], fail=True)
            self.assertEqual((okc, badc), (0, 1))
            for name, src, want, state in (
                    ('zero', RUNNER_STUB % ('tests 0  failures 0  errors 0', 0), 2, 'ITEM_ERROR'),
                    ('signal', 'import os, signal\nos.kill(os.getpid(), signal.SIGKILL)\n', 3, 'INDETERMINATE'),
                    ('failed', RUNNER_STUB % (bad, 1), 1, 'COMPLETED'),
                    ('contradicts', RUNNER_STUB % (ok, 1), 2, 'ITEM_ERROR'),
                    ('ok', RUNNER_STUB % (ok, 0), 0, 'COMPLETED')):
                with self.subTest(case=name):
                    c, out = self.run_group(m, name, src, gid)
                    self.assertEqual(c, want, (m, name, out[-2000:]))
                    self.assertRegex(out, r'(?m)^FILE %s state=%s ' % (gid, state))
                    self.assertTrue(out.strip().splitlines()[-1].endswith(' exit=%d' % want))
                    if want:
                        self.assertNotRegex(out, r'(?m)^ALL \S+ CHECKS PASS$')
        setattr(TheTwelveWrappersWithAStubTestRunner, 'test_' + m + '_s1', t)


_add_twelve_cases()


# fault runner: (the module whose reference environment is broken in the copy, the text appended to break it,
#                the module holding FAULTS or None, the successor-file text changed for a must-fail list that differs from the pin)
BROKEN_STORE = '\n\ndef _broken(self, *a, **k):\n    raise RuntimeError("broken store")\n\n\nInMemoryRecordStore._atomic = _broken\n'
FAULT_RUNNERS = {
    'run_faults_s1': ('apg/reference_impl.py', BROKEN_STORE, 'apg/faulty_impls.py', None),
    'run_m3_faults_s1': ('apg/ingest/reference_m3.py', '\n\n_orig_file_env = file_env\n\n\ndef file_env(files_cls=InMemoryFileStore, provider_cls=StaticContextProvider):\n    if files_cls is InMemoryFileStore:\n        raise RuntimeError("broken reference")\n    return _orig_file_env(files_cls, provider_cls)\n',
                         'apg/ingest/faulty_m3.py', None),
    'run_m5_faults_s1': ('apg/det/reference_m5.py', '\n\n_orig_notify_env = notify_env\n\n\ndef notify_env(notifier_cls=InMemoryNotifier, provider_cls=StaticContextProvider):\n    if notifier_cls is InMemoryNotifier:\n        raise RuntimeError("broken reference")\n    return _orig_notify_env(notifier_cls, provider_cls)\n',
                         'apg/det/faulty_m5.py', None),
    'run_m6_faults_s1': ('apg/mkt/reference_m6.py', '\n\n_orig_feed_env = feed_env\n\n\ndef feed_env(feed_cls=InMemoryMarketFeed, provider_cls=StaticContextProvider):\n    if feed_cls is InMemoryMarketFeed:\n        raise RuntimeError("broken reference")\n    return _orig_feed_env(feed_cls, provider_cls)\n',
                         'apg/mkt/faulty_m6.py', None),
    'run_history_contract_s1': ('apg/reference_impl.py', BROKEN_STORE, None, ('(H.OutOfRangeReadsLatest, "RH-03")',
                                                                              '(H.OutOfRangeReadsLatest, "RH-01")')),
}


class EveryFaultRunnerAtToolLevel(unittest.TestCase):
    """Authorisation §4.5 for each of the five fault runners (deviation D9, closed by this class), each run as the real tool on a temporary
    copy:
      - its own reference control fails (the reference environment it runs is broken in the copy): CONTROL start CONTROL_FAIL, every plant
        NOT_RUN cause=control_start_FAIL, no plant run, exit 3, and no M10 marker;
      - its preflight: the first fault's must-fail list emptied in the copy (no_must_fail_cases), or, for run_history_contract_s1, whose
        plants are defined in the successor file, a must-fail case that differs from the pin (must_fail_differs_from_pin): RUN_ERROR
        PREFLIGHT_INVALID_TARGET, the plant NOT_RUN cause=preflight_failed, no CONTROL line, exit 2.
    The checker accepts every output.  The fault runners run each plant in their own process and start no child, so the timeout and crash
    cases of the mutation and sabotage tools do not arise for them."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_faults_')
        self.pins, _ = E.load_pins()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def _add_fault_runner_cases():
    for tool, (ref, broken, faults, differs) in FAULT_RUNNERS.items():
        def t_control(self, tool=tool, ref=ref, broken=broken):
            tree = tree_copy(os.path.join(self.tmp, tool + '_ctl'))
            with open(os.path.join(tree, ref), 'a', encoding='utf-8') as fh:
                fh.write(broken)
            code, out, err = run_in(tree, tool + '.py')
            want = self.pins['plant_lists'][tool]['ids']
            self.assertEqual(code, 3, out[-2000:] + err[-1500:])
            self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL cause=\S+ ')
            self.assertEqual([l for l in out.splitlines() if l.startswith('PLANT ')], ['PLANT %s NOT_RUN cause=control_start_FAIL' % p for p in want])
            self.assertNotRegex(out, r'(?m)^(CAUGHT|MISSED) ')
            self.assertIn(' control_start=FAIL started=0 ', out.strip().splitlines()[-1])
            self.assertNotIn('ALL FAULTS CAUGHT', out)
            self.assertNotIn('EVERY FAULTY STORE IS CAUGHT', out)
            self.assertEqual(E.check_output(out, code, selected=want), [])

        def t_preflight(self, tool=tool, faults=faults, differs=differs):
            tree = tree_copy(os.path.join(self.tmp, tool + '_pre'))
            first = self.pins['plant_lists'][tool]['ids'][0]
            if faults:
                with open(os.path.join(tree, faults), 'a', encoding='utf-8') as fh:
                    fh.write('\n_k = %r\nFAULTS[_k] = FAULTS[_k][:-1] + ([],)     # planted by tests_tools: an empty must-fail list\n' % first)
                why = 'no_must_fail_cases'
            else:
                p = os.path.join(tree, 'tools', tool + '.py')
                with open(p, encoding='utf-8') as fh:
                    src = fh.read()
                self.assertEqual(src.count(differs[0]), 1)
                with open(p, 'w', encoding='utf-8') as fh:
                    fh.write(src.replace(differs[0], differs[1]))
                why = 'must_fail_differs_from_pin'
            code, out, err = run_in(tree, tool + '.py', '--ids', first)
            self.assertEqual(code, 2, out[-2000:] + err[-1500:])
            self.assertIn('RUN_ERROR PREFLIGHT_INVALID_TARGET %s:%s' % (first, why), out)
            self.assertIn('PLANT %s NOT_RUN cause=preflight_failed' % first, out)
            self.assertNotRegex(out, r'(?m)^CONTROL ')
            self.assertIn(' preflight=FAIL control_start=NOT_RUN started=0 ', out.strip().splitlines()[-1])
            self.assertEqual(E.check_output(out, code, selected=[first]), [])
        setattr(EveryFaultRunnerAtToolLevel, 'test_failed_reference_control_' + tool, t_control)
        setattr(EveryFaultRunnerAtToolLevel, 'test_preflight_' + tool, t_preflight)


_add_fault_runner_cases()


class SelectionDetails(unittest.TestCase):
    """Authorisation §4.3 (a partial selection; unknown and duplicate selection ids) and the literal selection details: the selection
    helper itself (evkit._parse_selection) for a partial, an unknown and a duplicate selection; a duplicate id through a real mutation tool
    and a real sabotage tool (refused, exit 2, nothing started); P1-F5's 'no_file_matches' detail for run_m2_tests_s1; and selected=0 on
    the RESULT line of a selection that names nothing."""

    def test_the_selection_helper(self):
        u = ['A1', 'A2', 'B1', 'B2']
        sel, errs, opts = E._parse_selection(['--ids', 'B1,A1'], u)
        self.assertEqual((sel, errs), (['A1', 'B1'], []))           # a partial selection, in the universe's order
        sel, errs, opts = E._parse_selection(['--only', 'B'], u)
        self.assertEqual((sel, errs), (['B1', 'B2'], []))
        sel, errs, opts = E._parse_selection(['--ids', 'A1,A1'], u)
        self.assertEqual([e.line() for e in errs], ['RUN_ERROR SELECTION_INVALID duplicate ids'])
        sel, errs, opts = E._parse_selection(['--ids', 'A1,Z9'], u)
        self.assertEqual([e.line() for e in errs], ['RUN_ERROR SELECTION_INVALID unknown ids Z9'])
        sel, errs, opts = E._parse_selection(['--only', 'Q'], u)
        self.assertEqual([e.line() for e in errs], ['RUN_ERROR SELECTION_INVALID only Q selects nothing'])

    def test_a_duplicate_id_through_a_real_tool(self):
        mid = self_pins()['mutation_lists']['m5_mutants_s1']['ids'][0]
        for script, item, tag in (('m5_mutants_s1.py', mid, 'MUTANT'), ('sabotage_m7_s1.py', 'S01', 'PLANT')):
            with self.subTest(tool=script):
                code, out, err = run_in(ROOT, script, '--ids', '%s,%s' % (item, item))
                self.assertEqual(code, 2, out[-2000:])
                self.assertIn('RUN_ERROR SELECTION_INVALID duplicate ids', out)
                self.assertNotRegex(out, r'(?m)^CONTROL ')
                self.assertEqual([l for l in out.splitlines() if l.startswith(tag + ' ')], ['%s %s NOT_RUN cause=run_error' % (tag, item)])
                self.assertIn(' started=0 ', out.strip().splitlines()[-1])
                self.assertEqual(E.check_output(out, code), [])

    def test_no_file_matches_and_selected_zero(self):
        code, out, err = run_in(ROOT, 'run_m2_tests_s1.py', '-q', 'nomatch_*.py')
        self.assertEqual(code, 2)
        self.assertRegex(out, r'(?m)^RUN_ERROR SELECTION_INVALID no_file_matches$')
        self.assertIn(' files_selected=0 ', out.strip().splitlines()[-1])
        code, out, err = run_in(ROOT, 'run_det_corpus_s1.py', '--only', 'NOPE')          # kind=cases: selected=0, no item line
        self.assertEqual(code, 2)
        self.assertIn(' selected=0 ', out.strip().splitlines()[-1])
        self.assertNotRegex(out, r'(?m)^CASE ')
        self.assertEqual(E.check_output(out, code), [])
        # kind=mutation (decision (g), owner, 2026-11-02 14:24; this comment corrected in corrective pass 2, mistake 18): every pinned item NOT_RUN cause=run_error, started=0, exit 2
        code, out, err = run_in(ROOT, 'm5_mutants_s1.py', '--only', 'QQ')
        self.assertEqual(code, 2)
        last = out.strip().splitlines()[-1]
        self.assertIn(' started=0 ', last)
        self.assertEqual({l.split(' ', 2)[2] for l in out.splitlines() if l.startswith('MUTANT ')}, {'NOT_RUN cause=run_error'})
        self.assertEqual(E.check_output(out, code), [])


def self_pins():
    return E.load_pins()[0]


class TheOtherCaseRunners(unittest.TestCase):
    """Authorisation §4.4 for the kind=cases tools that CasesRunners does not run: run_guard_contract_s1, run_m6_contracts_s1 and
    run_m91_contracts_s1, each run in full against its pinned inventory, and run_history_contract_s1 in its candidate mode
    (--path, --factory) against the reference store; the checker accepts each output with the pinned case list as the selection."""

    def test_each_runs_its_whole_pinned_inventory(self):
        doc = self_pins()
        for tool in ('run_guard_contract_s1', 'run_m6_contracts_s1', 'run_m91_contracts_s1'):
            with self.subTest(tool=tool):
                code, out, err = run_in(ROOT, tool + '.py')
                self.assertEqual(code, 0, out[-2000:] + err[-1500:])
                inv = doc['case_inventories'][tool]
                want = ['%s/%s' % (s, c) for s in sorted(inv) for c in inv[s]['ids']]
                self.assertEqual([l.split(' ')[1] for l in out.splitlines() if l.startswith('CASE ')], want)
                self.assertTrue(out.strip().splitlines()[-1].startswith('RESULT v=3 kind=cases tool=%s ' % tool))
                self.assertEqual(E.check_output(out, code, pins=inv, selected=want), [])

    def test_the_history_contract_candidate_mode_is_reconciled(self):
        d = tempfile.mkdtemp(prefix='s1_hist_')
        try:
            os.makedirs(os.path.join(d, 'store_adapter'))
            with open(os.path.join(d, 'store_adapter', '__init__.py'), 'w') as f:
                f.write('from apg.contracts.framework import ContractEnv\nfrom apg.reference_impl import FakeClock, StaticContextProvider, '
                        'InMemoryRecordStore, InMemoryAuditLog\n\ndef F():\n    c = FakeClock(); p = StaticContextProvider(c)\n'
                        '    return ContractEnv(p, InMemoryRecordStore(p), InMemoryAuditLog(p, c), c.advance)\n')
            code, out, err = run_in(ROOT, 'run_history_contract_s1.py', '--path', d, '--factory', 'store_adapter:F')
            self.assertEqual(code, 0, out[-2000:] + err[-1500:])
            got = [l.split(' ')[1] for l in out.splitlines() if l.startswith('CASE ')]
            self.assertEqual(len(got), 6)
            self.assertEqual(E.check_output(out, code, selected=got), [])
            self.assertIn('ALL HISTORY CASES PASS', out)
        finally:
            shutil.rmtree(d, ignore_errors=True)


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
                self.assertTrue(last.startswith(('RESULT v=2 ', 'RESULT v=3 ')) and ' started=0 ' in last and last.endswith(' status=EVIDENCE_ERROR exit=2'), last)
                self.assertNotRegex(out, r'(?m)^(MUTANT|PLANT) \S+ (?!NOT_RUN)')
                self.assertEqual(E.check_output(out, code), [])


# ---------------------------------------------------------------------------------------------------------------------------------------
# Corrective pass 2 (paper 23d2adb9...f0ea5, amendments 1 and 2), at tool level, in temporary copies: B.5 (the fault runners' forked plants
# and controls), K.2 (the corpus runners' forked cases), AM2-1 (the batch case runners' one harness unit), A.4 (the v=3 cases contract on
# the real runners), C.2 and C.3 (the guarded imports and their wrapper consumers), F.2 on the other families, and AM2-2 (the 6
# supervisors with no RESULT line and their consumers).  P's time constants and the two item limits are shortened in each copy.
# ---------------------------------------------------------------------------------------------------------------------------------------
import re as _p2re
import signal as _p2sig
import subprocess as _p2sp
import time as _p2t

P2_FAST = [('T_GRACE = 10 ', 'T_GRACE = 1 '), ('T_GRACE_CANCELLED = 2 ', 'T_GRACE_CANCELLED = 1 '), ('T_ESCALATE = 10 ', 'T_ESCALATE = 2 '),
           ('T_KILL_VERIFY = 5 ', 'T_KILL_VERIFY = 2 '), ('T_EXIT_AFTER_RESULT = 2 ', 'T_EXIT_AFTER_RESULT = 1 '),
           ('FAULT_ITEM_TIMEOUT_S = 300 ', 'FAULT_ITEM_TIMEOUT_S = 3 '), ('CASE_ITEM_TIMEOUT_S = 300 ', 'CASE_ITEM_TIMEOUT_S = 3 ')]


def p2b_copy(dest, edits=()):
    """A copy of this tree with P's constants shortened; edits: [(relpath, old, new)], each old present exactly once."""
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
    for rel, old, new in [('tools/evkit.py', o, n) for o, n in P2_FAST] + list(edits):
        p = os.path.join(dest, rel)
        with open(p, encoding='utf-8') as fh:
            src = fh.read()
        assert src.count(old) == 1, (rel, old)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(src.replace(old, new))
    return dest


def p2b_descendants(pid):
    tab = E.proc_table()
    kids = {}
    for p, (st, pp, s) in tab.items():
        kids.setdefault(pp, []).append(p)
    out, todo = [], [pid]
    while todo:
        x = todo.pop()
        for c in kids.get(x, ()):
            if tab[c][0] != 'Z':
                out.append((c, tab[c][2]))
            todo.append(c)
    return out


P2B_PGIDS = {}


def p2b_note_pgids(d):
    """Fix 6 (D6-7, rows 42 and 121): note each descendant's process group while it lives, during the run, for the identity record."""
    for x in d:
        if (x[0], x[1]) not in P2B_PGIDS:
            try:
                P2B_PGIDS[(x[0], x[1])] = os.getpgid(x[0])
            except OSError:
                pass


def p2b_run(tree, args, when=None, sig=_p2sig.SIGINT, delay=0.0, timeout=600):
    """Run python3 -I -S <args> in the tree; optionally send sig once when(tree, descendants) holds.  Returns (code, output, seen)."""
    tmp = tempfile.mkdtemp(prefix='s1_p2b_')
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp,
           'PYTHONDONTWRITEBYTECODE': '1'}
    p = _p2sp.Popen([sys.executable, '-I', '-S'] + list(args), cwd=tree, env=env, stdin=_p2sp.DEVNULL, stdout=_p2sp.PIPE,
                    stderr=_p2sp.STDOUT, text=True, start_new_session=True)
    seen, sent = set(), False
    t_end = _p2t.monotonic() + timeout
    try:
        while p.poll() is None and _p2t.monotonic() < t_end:
            d = p2b_descendants(p.pid)
            seen |= set(d)
            p2b_note_pgids(d)
            if when is not None and not sent and when(tree, d):
                _p2t.sleep(delay)
                seen |= set(p2b_descendants(p.pid))
                p.send_signal(sig)
                sent = True
            _p2t.sleep(0.05)
        out, _ = p.communicate(timeout=max(1, t_end - _p2t.monotonic()))
    finally:
        if p.poll() is None:
            os.killpg(p.pid, 9)
            p.wait()
        shutil.rmtree(tmp, ignore_errors=True)
    return p.returncode, out, seen


def p2b_gone(test, seen):
    for i in seen:
        st = E.proc_stat(i[0])
        test.assertFalse(st is not None and st[2] == i[1], 'a descendant is still present: %r %r' % (i, st))


def p2b_mark(name):
    return lambda tree, d: os.path.exists(os.path.join(tree, '_p2', name))


# a behaviour planted into a forked unit's callable: MODE read from the copy's _p2/mode file; the child's own pipe write end is the
# highest descriptor above 2 (P.2: it keeps only 0, 1, 2 and that one)
P2_PLANT = r'''
def _p2_behaviour(where, normal):
    import os as _o, sys as _s, json as _j, subprocess as _sp, time as _tm
    d = _o.path.join(%(root)r, '_p2')
    mode = open(_o.path.join(d, 'mode')).read().strip() if _o.path.exists(_o.path.join(d, 'mode')) else ''
    if not mode.startswith(where + ':'):
        return normal()
    mode = mode.split(':', 1)[1]
    open(_o.path.join(d, 'started'), 'w').close()
    def w():
        return max(int(x) for x in _o.listdir('/proc/self/fd') if int(x) > 2 and _o.path.exists('/proc/self/fd/' + x))
    def frame(obj, extra=b''):
        data = _j.dumps(obj).encode()
        _o.write(w(), len(data).to_bytes(4, 'big') + data + extra)
    if mode == 'hang':
        _tm.sleep(60)
    if mode == 'spawn_hang':
        _sp.Popen([_s.executable, '-c', 'import time; time.sleep(60)']); _tm.sleep(60)
    if mode == 'leak_ignoring':          # fix 6: a leftover that ignores SIGTERM (it marks 'leaked' once it does), so the cleanup lasts
        _sp.Popen([_s.executable, '-c', 'import signal, sys, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); '
                   'open(sys.argv[1], "w").close(); time.sleep(30)', _o.path.join(d, 'leaked')])
        for _k in range(200):          # the unit returns only once the leftover ignores SIGTERM (no race with the cleanup's SIGTERM)
            if _o.path.exists(_o.path.join(d, 'leaked')):
                break
            _tm.sleep(0.025)
        return normal()
    if mode in ('leak', 'child_error_leak', 'malformed_leak'):
        _sp.Popen([_s.executable, '-c', 'import time; time.sleep(30)'])
        if mode == 'child_error_leak':
            frame({'child_error': 'X'}); _o._exit(0)
        if mode == 'malformed_leak':
            _o.write(w(), b'\x00\x00\x00\x02{]'); _o._exit(0)
        return normal()
    if mode == 'valid_then_hang':
        frame(normal_message(normal)); _o.close(w()); _tm.sleep(60)
    if mode == 'crash':
        _o._exit(1)
    if mode == 'status70':
        _o._exit(70)
    if mode == 'incomplete':
        _o.write(w(), b'\x00\x00\x01\x00{"fa'); _o._exit(0)
    if mode == 'malformed':
        _o.write(w(), b'\x00\x00\x00\x02{]'); _o._exit(0)
    if mode == 'trailing':
        frame(normal_message(normal), b'x'); _o._exit(0)
    if mode == 'kill_writing':
        _o.write(w(), b'\x00\x00\x01\x00{"'); _o.kill(_o.getpid(), 9)
    if mode == 'child_error':
        frame({'child_error': 'X'}); _o._exit(0)
    if mode == 'raise':
        raise RuntimeError('planted')
    if mode == 'too_big':
        frame({'results': 'x' * (1024 * 1024)}); _o._exit(0)
    return normal()
'''


class P2FaultRunners(unittest.TestCase):
    """B.5 on run_faults_s1 (every case) and the hang on each of the other four runners; P.10's valid_result_then_hangs for a plant."""
    TOOL = 'run_faults_s1'      # amendment 5, row 42: the subclasses below run the same set on the other four fault runners

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_p2f_')
        doc, _ = E.load_pins()
        self.pid0 = doc['plant_lists']['run_faults_s1']['ids'][0]
        self.case0 = doc['case_inventories']['run_contracts_s1']['record_store']['ids'][0]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def tree(self, mode):
        root = os.path.join(self.tmp, mode.replace(':', '_'))
        plant = P2_PLANT % {'root': root}
        edits = [('tools/run_faults_s1.py', 'def failed(factory):\n    return {r[1] for r in R.run(factory) if not r[3]}\n',
                  plant + '\n\ndef normal_message(normal):\n    return {"failed": sorted(normal())}\n\n\n'
                  'def failed(factory):\n    where = "control" if factory is reference else "plant"\n'
                  '    if where == "control":\n        import os\n        cf = os.path.join(%r, "_p2", "controls")\n'
                  '        open(cf, "a").write("x")\n        where = "control_start" if len(open(cf).read()) == 1 else "control_end"\n'
                  '    return _p2_behaviour(where, lambda: {r[1] for r in R.run(factory) if not r[3]})\n' % root)]
        p2b_copy(root, edits)
        os.makedirs(os.path.join(root, '_p2'))
        with open(os.path.join(root, '_p2', 'mode'), 'w') as fh:
            fh.write(mode)
        return root

    def run_f(self, mode, when=None, sig=_p2sig.SIGINT):
        root = self.tree(mode)
        code, out, seen = p2b_run(root, ['tools/run_faults_s1.py', '--ids', self.pid0], when=when, sig=sig)
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.assertEqual(E.check_output(out, code, selected=[self.pid0]), [], out[-3000:])
        p2b_gone(self, seen)
        return code, out

    def plant_is(self, out, state, cause):
        self.assertRegex(out, r'(?m)^PLANT %s %s cause=%s$' % (_p2re.escape(self.pid0), state, cause))

    def test_plants(self):
        for mode, state, cause, code in (('plant:hang', 'INDETERMINATE', 'timeout', 3),
                                         ('plant:spawn_hang', 'INDETERMINATE', 'timeout', 3),
                                         ('plant:leak', 'INDETERMINATE', 'processes_left', 3),
                                         ('plant:valid_then_hang', 'INDETERMINATE', 'processes_left', 3),
                                         ('plant:crash', 'INDETERMINATE', 'crash', 3),
                                         ('plant:incomplete', 'INDETERMINATE', 'crash', 3),
                                         ('plant:malformed', 'INDETERMINATE', 'bad_result', 3),
                                         ('plant:trailing', 'INDETERMINATE', 'bad_result', 3),
                                         ('plant:kill_writing', 'INDETERMINATE', 'crash', 3),
                                         ('plant:child_error', 'ITEM_ERROR', 'child_error', 2),
                                         ('plant:status70', 'ITEM_ERROR', 'child_error', 2),
                                         ('plant:raise', 'ITEM_ERROR', 'exception_RuntimeError', 2)):
            with self.subTest(mode=mode):
                c, out = self.run_f(mode)
                self.assertEqual(c, code, out[-2000:])
                self.plant_is(out, state, cause)
                if cause == 'timeout':
                    self.assertRegex(out, r'(?m)^TIMEOUT %s cmd=reference limit=3s control_start=\d+\.\d{3}s control_end=\d+\.\d{3}s$'
                                     % _p2re.escape(self.pid0))
                if cause == 'processes_left':
                    self.assertRegex(out, r'(?m)^CLEANUP %s by=%s:\d+ ' % (_p2re.escape(self.pid0), self.TOOL))

    def test_controls(self):
        for where in ('control_start', 'control_end'):
            ph = where.split('_')[1]
            for mode, value, cause in (('hang', 'TIMEOUT', 'timeout'), ('crash', 'FAIL', 'crash'), ('malformed', 'FAIL', 'bad_result'),
                                       ('leak', 'FAIL', 'processes_left'), ('raise', 'FAIL', 'exception_RuntimeError')):
                with self.subTest(where=where, mode=mode):
                    c, out = self.run_f('%s:%s' % (where, mode))
                    self.assertRegex(out, r'(?m)^CONTROL %s CONTROL_%s cause=%s ' % (ph, value, cause))
                    self.assertIn(' %s=%s ' % (where, value), out.strip().splitlines()[-1])
                    self.assertEqual(c, 3, out[-2000:])
            # an interrupt before the outcome
            with self.subTest(where=where, mode='interrupt'):
                c, out = self.run_f('%s:hang' % where, when=p2b_mark('started'))
                self.assertEqual(c, 3, out[-2000:])
                if ph == 'start':
                    self.assertRegex(out, r'(?m)^CONTROL start CONTROL_INTERRUPTED cause=interrupted$')
                    self.assertIn(' control_start=FAIL ', out.strip().splitlines()[-1])
                else:
                    self.assertRegex(out, r'(?m)^CONTROL end CONTROL_NOT_RUN cause=interrupted$')
                    self.assertIn(' control_end=NOT_RUN ', out.strip().splitlines()[-1])
                self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=SIGINT at=%s received=1' % where)

    def test_f2_sigterm_while_a_plant_runs(self):
        c, out = self.run_f('plant:hang', when=p2b_mark('started'), sig=_p2sig.SIGTERM)
        self.assertEqual(c, 3, out[-2000:])
        self.plant_is(out, 'INDETERMINATE', 'interrupted')
        self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=SIGTERM at=%s received=1' % self.pid0)

    def test_the_hang_on_each_of_the_other_four_runners(self):
        doc, _ = E.load_pins()
        for tool, old in (('run_m3_faults_s1', 'def failed_for(kind, factory):\n'), ('run_m5_faults_s1', 'def failed(factory):\n'),
                          ('run_m6_faults_s1', 'def failed_for(suite, factory):\n'), ('run_history_contract_s1', 'def failed(cls):\n')):
            with self.subTest(tool=tool):
                root = os.path.join(self.tmp, tool)
                p2b_copy(root, [('tools/%s.py' % tool, old, 'def _p2_hang():\n    import time\n    time.sleep(60)\n\n\n' + old +
                                 '    _p2_hang()\n')])
                first = doc['plant_lists'][tool]['ids'][0]
                code, out, seen = p2b_run(root, ['tools/%s.py' % tool, '--ids', first])
                p2_identity_record(self, seen, out)          # fix 6, row 121
                # the reference control calls the same function in some runners: the start control then times out instead
                self.assertEqual(code, 3, out[-2000:])
                self.assertTrue(_p2re.search(r'(?m)^PLANT %s INDETERMINATE cause=timeout$' % _p2re.escape(first), out) or
                                _p2re.search(r'(?m)^CONTROL start CONTROL_TIMEOUT cause=timeout ', out), out[-2000:])
                self.assertEqual(E.check_output(out, code, selected=[first]), [], out[-3000:])
                p2b_gone(self, seen)


class P2CaseRunners(unittest.TestCase):
    """AM2-1 on run_contracts_s1 (every case) and the hang on the other six batch runners; K.2 on run_fin_corpus_s1 and the hang on the
    other three corpus runners; A.4 on the real runners."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_p2c_')
        self.doc, _ = E.load_pins()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def batch_tree(self, mode):
        root = os.path.join(self.tmp, 'b_' + mode.replace(':', '_'))
        plant = P2_PLANT % {'root': root}
        old = ('def batch(cand):\n    return [[s, cid, bool(ok), str(d)] for s, cid, text, ok, d in R.run(cand.get("--factory") or reference)]\n')
        new = (plant + '\n\ndef normal_message(normal):\n    return {"results": normal()}\n\n\n' + old.replace('def batch(', 'def _batch(') +
               '\n\ndef batch(cand):\n    rows = _batch(cand)\n    m = open(%r).read().strip()\n'
               '    if m == "batch:false_row":\n        rows[0][2] = False\n'
               '    if m == "batch:wrong_type":\n        rows[0][2] = "yes"\n'
               '    if m == "batch:duplicate":\n        rows.append(list(rows[0]))\n'
               '    if m == "batch:drop_pinned":\n        rows = [r for r in rows if r[1] != "AL-02"]\n'
               '    return _p2_behaviour("batch", lambda: rows)\n' % os.path.join(root, '_p2', 'mode'))
        p2b_copy(root, [('tools/run_contracts_s1.py', old, new)])
        os.makedirs(os.path.join(root, '_p2'))
        with open(os.path.join(root, '_p2', 'mode'), 'w') as fh:
            fh.write(mode)
        return root

    def run_b(self, mode, args=(), when=None):
        root = self.batch_tree(mode)
        code, out, seen = p2b_run(root, ['tools/run_contracts_s1.py'] + list(args), when=when)
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.assertEqual(E.check_output(out, code, pins=self.doc['case_inventories']['run_contracts_s1']), [], out[-3000:])
        p2b_gone(self, seen)
        return code, out

    def all_cases(self, out, state, cause, n=38):
        got = _p2re.findall(r'(?m)^CASE \S+ %s cause=%s$' % (state, cause), out)
        self.assertEqual(len(got), n, out[-2000:])

    def test_am2_1_the_batch_unit(self):
        for mode, state, cause, code in (('batch:hang', 'INDETERMINATE', 'timeout', 3),
                                         ('batch:spawn_hang', 'INDETERMINATE', 'timeout', 3),
                                         ('batch:leak', 'INDETERMINATE', 'processes_left', 3),
                                         ('batch:valid_then_hang', 'INDETERMINATE', 'processes_left', 3),
                                         ('batch:crash', 'INDETERMINATE', 'crash', 3),
                                         ('batch:incomplete', 'INDETERMINATE', 'crash', 3),
                                         ('batch:kill_writing', 'INDETERMINATE', 'crash', 3),
                                         ('batch:malformed', 'INDETERMINATE', 'bad_result', 3),
                                         ('batch:trailing', 'INDETERMINATE', 'bad_result', 3),
                                         ('batch:wrong_type', 'INDETERMINATE', 'bad_result', 3),
                                         ('batch:duplicate', 'INDETERMINATE', 'bad_result', 3),
                                         ('batch:too_big', 'INDETERMINATE', 'bad_result', 3),
                                         ('batch:child_error', 'ITEM_ERROR', 'child_error', 2),
                                         ('batch:status70', 'ITEM_ERROR', 'child_error', 2),
                                         ('batch:child_error_leak', 'ITEM_ERROR', 'child_error', 2),
                                         ('batch:malformed_leak', 'INDETERMINATE', 'bad_result', 3)):
            with self.subTest(mode=mode):
                c, out = self.run_b(mode)
                self.assertEqual(c, code, out[-2000:])
                self.all_cases(out, state, cause)
                if mode.endswith('_leak'):
                    self.assertRegex(out, r'(?m)^CLEANUP run_contracts_s1:batch by=run_contracts_s1:\d+ ')
                if cause == 'timeout':
                    self.assertRegex(out, r'(?m)^TIMEOUT run_contracts_s1:batch cmd=batch limit=3s ')
        c, out = self.run_b('batch:false_row')
        self.assertEqual(c, 1)
        self.assertEqual(len(_p2re.findall(r'(?m)^CASE \S+ FAIL cause=expected_outcome_differs$', out)), 1)
        c, out = self.run_b('batch:raise')
        self.assertEqual(c, 2)
        self.assertRegex(out, r'(?m)^RUN_ERROR CASES_ENUMERATION_FAILED RuntimeError$')
        self.assertIn(' suites_selected=3 suites=audit_log,record_store,tenant_context ', out.strip().splitlines()[-1])
        self.all_cases(out, 'NOT_RUN', 'run_error')
        c, out = self.run_b('batch:hang', when=p2b_mark('started'))
        self.assertEqual(c, 3)
        self.all_cases(out, 'INDETERMINATE', 'interrupted')
        self.assertTrue(out.strip().splitlines()[-2].startswith('INTERRUPTED signal=SIGINT at=audit_log/'))
        # --only one case: the full inventory is compared all the same (a pinned case missing from the harness's rows is refused)
        c, out = self.run_b('batch:drop_pinned', args=['--suite', 'record_store', '--only', 'RS-01'])
        self.assertEqual(c, 2)
        self.assertRegex(out, r'(?m)^RUN_ERROR CASE_INVENTORY_MISMATCH audit_log ')
        # the largest real message, unchanged
        c, out = self.run_b('none:x')
        self.assertEqual(c, 0, out[-2000:])
        self.all_cases(out, 'PASS', 'ok')
        self.assertIn('CLEANUP_SUMMARY units=1 leaked=0 remaining=0', out)

    def test_the_hang_on_the_other_six_batch_runners(self):
        for tool, old in (('run_guard_contract_s1', 'def batch(cand):\n'), ('run_m3_contracts_s1', 'def batch(cand):\n'),
                          ('run_m5_contracts_s1', 'def batch(cand):\n'), ('run_m6_contracts_s1', 'def batch(cand):\n'),
                          ('run_m91_contracts_s1', 'def batch(cand):\n')):
            with self.subTest(tool=tool):
                root = os.path.join(self.tmp, tool)
                p2b_copy(root, [('tools/%s.py' % tool, old, old + '    import time\n    time.sleep(60)\n')])
                code, out, seen = p2b_run(root, ['tools/%s.py' % tool])
                p2_identity_record(self, seen, out)          # fix 6, row 121
                self.assertEqual(code, 3, out[-2000:])
                n = sum(len(v['ids']) for v in self.doc['case_inventories'][tool].values())
                self.all_cases(out, 'INDETERMINATE', 'timeout', n)
                self.assertEqual(E.check_output(out, code, pins=self.doc['case_inventories'][tool]), [], out[-3000:])
                p2b_gone(self, seen)
        # run_history_contract_s1's case mode: the hang in its batch
        root = os.path.join(self.tmp, 'hist')
        p2b_copy(root, [('tools/run_history_contract_s1.py', 'def batch(cand):\n', 'def batch(cand):\n    import time\n    time.sleep(60)\n')])
        os.makedirs(os.path.join(root, '_cand', 'p2cand'))
        with open(os.path.join(root, '_cand', 'p2cand', '__init__.py'), 'w') as fh:
            fh.write('from apg.reference_impl import InMemoryRecordStore as Store\n')
        code, out, seen = p2b_run(root, ['tools/run_history_contract_s1.py', '--path', '_cand', '--factory', 'p2cand:Store'])
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.assertEqual(code, 3, out[-2000:])
        self.all_cases(out, 'INDETERMINATE', 'timeout', 6)

    def corpus_tree(self, tool, edit):
        root = os.path.join(self.tmp, 'k_%s_%d' % (tool, len(os.listdir(self.tmp))))
        p2b_copy(root, [('tools/%s.py' % tool,) + edit])
        return root

    def test_k2_per_case_on_run_fin_corpus_s1(self):
        doc = self.doc['case_inventories']['run_fin_corpus_s1']['fin_corpus']['ids']
        c0 = doc[0]
        old = "def run_case(cand, suite, cid):\n"
        for body, state, cause, code in (('    import time\n    time.sleep(60) if cid == %r else None\n', 'INDETERMINATE', 'timeout', 3),
                                         ('    import os\n    os._exit(1) if cid == %r else None\n', 'INDETERMINATE', 'crash', 3),
                                         ('    import os\n    os._exit(70) if cid == %r else None\n', 'ITEM_ERROR', 'child_error', 2),
                                         ('    if cid == %r:\n        raise KeyError("planted")\n', 'FAIL', 'exception_KeyError', 1),
                                         ('    import subprocess, sys\n    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"]) '
                                          'if cid == %r else None\n', 'INDETERMINATE', 'processes_left', 3)):
            with self.subTest(cause=cause):
                root = self.corpus_tree('run_fin_corpus_s1', (old, old + body % c0))
                code_, out, seen = p2b_run(root, ['tools/run_fin_corpus_s1.py'])
                self.assertEqual(code_, code, out[-2000:])
                self.assertRegex(out, r'(?m)^CASE fin_corpus/%s %s cause=%s$' % (_p2re.escape(c0), state, cause))
                self.assertEqual(len(_p2re.findall(r'(?m)^CASE fin_corpus/\S+ PASS cause=ok$', out)), len(doc) - 1)
                self.assertEqual(E.check_output(out, code_, pins=self.doc['case_inventories']['run_fin_corpus_s1']), [], out[-3000:])
                p2b_gone(self, seen)
                shutil.rmtree(root, ignore_errors=True)
        # an interrupt during a case: that case interrupted, the rest NOT_RUN run_stopped
        root = self.corpus_tree('run_fin_corpus_s1', (old, old + '    import time\n    if cid == %r:\n        open(%r, "w").close()\n'
                                                      '        time.sleep(60)\n' % (doc[1], '/tmp/.p2_fin_started_%d' % os.getpid())))
        flag = '/tmp/.p2_fin_started_%d' % os.getpid()
        code_, out, seen = p2b_run(root, ['tools/run_fin_corpus_s1.py'], when=lambda t, d: os.path.exists(flag))
        os.path.exists(flag) and os.remove(flag)
        self.assertEqual(code_, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CASE fin_corpus/%s INDETERMINATE cause=interrupted$' % _p2re.escape(doc[1]))
        self.assertRegex(out, r'(?m)^CASE fin_corpus/%s NOT_RUN cause=run_stopped$' % _p2re.escape(doc[2]))
        self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=SIGINT at=fin_corpus/%s received=1' % doc[1])
        p2b_gone(self, seen)

    def test_k2_the_hang_on_the_other_three_corpus_runners(self):
        for tool, old in (('run_det_corpus_s1', 'def run_case(cand, suite, cid):\n'), ('run_ingest_corpus_s1', 'def run_case(cand, suite, cid):\n')):
            with self.subTest(tool=tool):
                inv = self.doc['case_inventories'][tool]
                s, ids = next(iter(inv.items()))
                ids = ids['ids']
                root = self.corpus_tree(tool, (old, old + '    import time\n    time.sleep(60) if cid == %r else None\n' % ids[0]))
                code, out, seen = p2b_run(root, ['tools/%s.py' % tool, '--only', ','.join(ids[:2])])
                p2_identity_record(self, seen, out)          # fix 6, row 121
                self.assertEqual(code, 3, out[-2000:])
                self.assertRegex(out, r'(?m)^CASE %s/%s INDETERMINATE cause=timeout$' % (s, _p2re.escape(ids[0])))
                self.assertEqual(E.check_output(out, code, pins=inv), [], out[-3000:])
                p2b_gone(self, seen)
        inv = self.doc['case_inventories']['run_mkt_corpus_s1']
        s, ids = next(iter(inv.items()))
        ids = ids['ids']
        root = self.corpus_tree('run_mkt_corpus_s1', ("'run_case': lambda cand, s, c: K.check_case(CASES[c])}",
                                                      "'run_case': lambda cand, s, c: __import__('time').sleep(60) if c == %r else "
                                                      "K.check_case(CASES[c])}" % ids[0]))
        code, out, seen = p2b_run(root, ['tools/run_mkt_corpus_s1.py', '--only', ','.join(ids[:2])])
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CASE %s/%s INDETERMINATE cause=timeout$' % (s, _p2re.escape(ids[0])))
        p2b_gone(self, seen)

    def test_a4_the_v3_contract_on_the_real_runners(self):
        pins = self.doc['case_inventories']['run_contracts_s1']

        def run(*args):
            p = _p2sp.run([sys.executable, '-I', '-S', 'tools/run_contracts_s1.py'] + list(args), cwd=ROOT, capture_output=True,
                          text=True, timeout=600, stdin=_p2sp.DEVNULL)
            return p.returncode, p.stdout

        def last(out):
            return E.parse_result_line(out.strip().splitlines()[-1])[1]
        code, out = run()
        f = last(out)
        self.assertEqual((code, f['suites'], f['suites_selected'], f['selected']), (0, 'audit_log,record_store,tenant_context', 3, 38))
        self.assertEqual(E.check_output(out, code, pins=pins), [])
        code, out = run('--suite', 'record_store')
        self.assertEqual((code, last(out)['suites']), (0, 'record_store'))
        self.assertEqual(E.check_output(out, code, pins=pins), [])
        code, out = run('--suite', 'record_store', '--only', 'RS-01')     # more pinned cases than printed
        self.assertEqual(len([l for l in out.splitlines() if l.startswith('CASE ')]), 1)
        self.assertEqual(E.check_output(out, code, pins=pins), [])
        code, out = run('--suite', 'record_store', '--suite', 'audit_log', '--only', 'AL-01')
        f = last(out)
        self.assertEqual((f['suites'], f['suites_selected'], f['selected']), ('audit_log,record_store', 2, 1))
        self.assertEqual(f['case_inventory_sha256'], E.sha256_lines(['%s/%s' % (s, c) for s in ('audit_log', 'record_store')
                                                                     for c in pins[s]['ids']]))
        self.assertEqual(E.check_output(out, code, pins=pins), [])
        for args in (('--suite', 'nope'), ('--only', 'NOPE-99'), ('--suite', 'record_store', '--suite', 'nope'), ('--bogus',)):
            with self.subTest(args=args):
                code, out = run(*args)
                f = last(out)
                self.assertEqual((code, f['suites'], f['suites_selected'], f['selected']), (2, '-', 0, 0))
                self.assertEqual(f['case_inventory_sha256'], E.EMPTY_SHA256)
                self.assertNotRegex(out, r'(?m)^CASE ')
                self.assertEqual(E.check_output(out, code, pins=pins), [])
        # step 1 (an early environment refusal: run with site) and step 2 (an unreadable pins file, in a copy): no resolved selection
        p = _p2sp.run([sys.executable, '-I', 'tools/run_contracts_s1.py'], cwd=ROOT, capture_output=True, text=True, timeout=600)
        f = last(p.stdout)
        self.assertEqual((p.returncode, f['suites'], f['selected']), (2, '-', 0))
        root = os.path.join(self.tmp, 'nopins')
        p2b_copy(root)
        with open(os.path.join(root, 'tools', 'expected_counts.json'), 'w') as fh:
            fh.write('{not json')
        code, out, seen = p2b_run(root, ['tools/run_contracts_s1.py'])
        p2_identity_record(self, seen, out)          # fix 6, row 121
        f = last(out)
        self.assertEqual((code, f['suites'], f['selected']), (2, '-', 0))
        # a refusal after the selection keeps it: an import failure (C.2)
        root = os.path.join(self.tmp, 'imp')
        p2b_copy(root)
        rp = os.path.join(root, 'apg', 'contracts', 'run.py')
        with open(rp, encoding='utf-8') as fh:
            src = fh.read()
        with open(rp, 'w', encoding='utf-8') as fh:
            fh.write('raise ImportError("planted")\n' + src)
        code, out, seen = p2b_run(root, ['tools/run_contracts_s1.py', '--suite', 'audit_log'])
        p2_identity_record(self, seen, out)          # fix 6, row 121
        f = last(out)
        self.assertEqual((code, f['suites'], f['suites_selected']), (2, 'audit_log', 1))
        self.assertRegex(out, r'(?m)^RUN_ERROR IMPORT_FAILED apg.contracts.run ImportError planted$')
        self.assertEqual(E.check_output(out, code, pins=pins), [])


class P2NoResultSupervisors(unittest.TestCase):
    """Amendment 2, AM2-2: the 5 regression successors and run_cr02_reference_s1, interrupted (the record the last line, exit 3), R03's,
    R06's and R04's blocked in-process waits stopped by the watcher, a signal after the last step, and the consumers of an interrupted
    no-kind child (a wrapper's class N CHECK, sabotage_m8_s1, a redirected regression successor)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_p2n_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def copy(self, name, edits=(), prepend=()):
        root = p2b_copy(os.path.join(self.tmp, name), edits)
        for rel, text in prepend:
            p = os.path.join(root, rel)
            with open(p, encoding='utf-8') as fh:
                src = fh.read()
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write(text + src)
        return root

    def cmd_running(self, needle):
        def f(tree, d):
            for pid, _ in d:
                try:
                    if needle in open('/proc/%d/cmdline' % pid, 'rb').read().decode('utf-8', 'replace'):
                        return True
                except OSError:
                    pass
            return False
        return f

    def interrupted(self, out, code, step_text=None):
        lines = [l for l in out.splitlines() if l.strip()]
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(lines[-1], r'^INTERRUPTED signal=(SIGINT|SIGTERM) at=\S+ received=[1-9][0-9]*$')
        self.assertTrue(E.is_interrupted_child(code, out))
        self.assertTrue(any(l.startswith('CLEANUP_SUMMARY ') for l in lines[:-2]))
        if step_text:
            self.assertRegex(out, step_text)

    def test_a_child_step_interrupted_by_sigint(self):
        root = self.copy('r07', prepend=[('tools/make_m8_config.py', 'import time\ntime.sleep(60)\n')])
        code, out, seen = p2b_run(root, ['tools/run_regression_m8_s1.py', '--step', 'R07'], when=self.cmd_running('make_m8_config.py'))
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.interrupted(out, code, r'(?m)^FAIL R07 .*\(INCOMPLETE: interrupted\)')
        p2b_gone(self, seen)

    def test_r03_blocked_in_process_is_stopped_by_the_watcher(self):
        root = self.copy('r03', prepend=[('tools/make_m8_registers.py', 'import time\ntime.sleep(60)\n')])
        t0 = _p2t.monotonic()
        code, out, seen = p2b_run(root, ['tools/run_regression_m8_s1.py', '--step', 'R03'], when=self.cmd_running('make_m8_registers.py'),
                                  sig=_p2sig.SIGTERM)
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.assertLess(_p2t.monotonic() - t0, 40)
        self.interrupted(out, code, r'(?m)^FAIL R03 .*\(INCOMPLETE: interrupted\)')
        p2b_gone(self, seen)

    def r_auif(self, tool, step):
        old = "[sys.executable, '-I', '-B', os.path.join(root, 'tools', 'verify_package.py'), root]"
        root = self.copy('auif_' + step, edits=[('apg_auif/dependency.py', old, "[sys.executable, '-c', 'import time; time.sleep(60)']")])
        code, out, seen = p2b_run(root, ['tools/%s.py' % tool, '--step', step], when=self.cmd_running('time.sleep(60)'),
                                  sig=_p2sig.SIGTERM)
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.interrupted(out, code, r'(?m)^FAIL %s .*\(INCOMPLETE: interrupted\)' % step)
        p2b_gone(self, seen)

    def test_r06_of_run_regression_m8_blocked_in_the_auif_verification(self):
        self.r_auif('run_regression_m8_s1', 'R06')

    def test_r04_of_run_regression_m81_blocked_in_the_auif_verification(self):
        self.r_auif('run_regression_m81_s1', 'R04')

    def selfsig(self, needle_tool, needle_cwd='', when_step=None):
        """an evkit edit in the copy: the named regression successor sends itself SIGTERM at the start of its first step (its own
        interrupt, as if signalled from outside), when its working directory contains needle_cwd"""
        old = '        def step():\n            if CANCEL.set:'
        new = ('        def step():\n            if tool_self == %r and %r in os.getcwd() and not CANCEL.set:\n'
               '                os.kill(os.getpid(), _signal.SIGTERM)\n                _time.sleep(0.5)\n            if CANCEL.set:'
               % (needle_tool, needle_cwd))
        return [('tools/evkit.py', old, new)]

    def test_between_steps_and_after_the_last_step(self):
        hold = ('            fixed = CANCEL.fix(last=(k == last_step))\n',
                '            fixed = CANCEL.fix(last=(k == last_step))\n            if k == "R01":\n'
                '                open(os.path.join(root, "_p2_after_R01"), "w").close()\n                _time.sleep(3)\n')
        root = self.copy('between', edits=[('tools/evkit.py',) + hold])
        code, out, seen = p2b_run(root, ['tools/run_regression_m8_s1.py', '--all'],
                                  when=lambda t, d: os.path.exists(os.path.join(t, '_p2_after_R01')), sig=_p2sig.SIGTERM)
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.interrupted(out, code, r'(?m)^FAIL R02 R02 \(INCOMPLETE: interrupted\)')
        self.assertNotRegex(out, r'(?m)^\S+ R01 .*INCOMPLETE')        # R01's outcome was fixed before the signal
        root = self.copy('after', edits=[('tools/evkit.py',) + hold])
        code, out, seen = p2b_run(root, ['tools/run_regression_m8_s1.py', '--step', 'R01'],
                                  when=lambda t, d: os.path.exists(os.path.join(t, '_p2_after_R01')), sig=_p2sig.SIGTERM)
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.assertNotEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^SIGNAL_AFTER_COMPLETION signal=SIGTERM$')
        self.assertFalse(out.strip().splitlines()[-1].startswith('INTERRUPTED'))

    def test_cr02_sigterm_during_its_first_child(self):
        root = self.copy('cr02', prepend=[('reference/cr02/cr02_materiality_tests.py', 'import time\ntime.sleep(60)\n')])
        code, out, seen = p2b_run(root, ['tools/run_cr02_reference_s1.py'], when=self.cmd_running('cr02_materiality_tests.py'),
                                  sig=_p2sig.SIGTERM)
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.interrupted(out, code)
        self.assertIn('CR-02 REFERENCE RERUN FAILED', out)       # M10's script read the CompletedProcess(returncode=-15, '' , '')
        p2b_gone(self, seen)

    def test_consumer_a_wrappers_class_n_check(self):
        root = self.copy('wrap', edits=self.selfsig('run_regression_m8_s1'))
        code, out, seen = p2b_run(root, ['tools/run_m8_all_s1.py', '--group', '1'])
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.assertRegex(out, r'(?m)^CHECK G01 INDETERMINATE source=child exit=3 ')
        pins = E.wrapper_check_pins('run_m8_all_s1')          # amendment 3, AM3-4: the class comes with the pins
        self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])
        # the checker accepts INDETERMINATE with a child exit only for exit 3 with a marker field (AM2-2 (d)); any other is refused
        for bad in ('exit=2 marker=absent', 'exit=3 marker=-', 'exit=0 marker=seen'):
            t = _p2re.sub(r'(?m)^(CHECK G01 INDETERMINATE source=child) exit=3 marker=\S+', r'\1 ' + bad, out)
            self.assertIn('CHECK G01 outcome INDETERMINATE contradicts %s' % bad, E.check_output(t, code, pins=pins), bad)

    def test_consumer_sabotage_m8_s1_at_a_plant_and_at_each_control(self):
        M = E.load_tool_module('sabotage_m8', ROOT)
        pid = next(c[0] for c in M.CASES if c[3][0] == 'tools/run_regression_m8.py' and c[3][1] == '--step')
        for needle, want in (('/m_', r'(?m)^PLANT %s INDETERMINATE cause=child_interrupted$' % _p2re.escape(pid)),
                             ('control_start', r'(?m)^CONTROL start CONTROL_FAIL cause=child_interrupted '),
                             ('control_end', r'(?m)^CONTROL end CONTROL_FAIL cause=child_interrupted ')):
            with self.subTest(at=needle):
                root = self.copy('sab_' + needle.strip('/'), edits=self.selfsig('run_regression_m8_s1', needle))
                code, out, seen = p2b_run(root, ['tools/sabotage_m8_s1.py', '--ids', pid])
                p2_identity_record(self, seen, out)          # fix 6, row 121
                self.assertRegex(out, want, out[-3000:])
                self.assertEqual(E.check_output(out, code, selected=[pid]), [], out[-3000:])
                self.assertNotIn('INTERRUPTED signal', out)          # the tool itself was not interrupted

    def test_consumer_a_redirected_regression_successor(self):
        root = self.copy('redir', edits=self.selfsig('run_regression_m8_s1'))
        code, out, seen = p2b_run(root, ['tools/run_regression_m81_s1.py', '--step', 'R08'])
        p2_identity_record(self, seen, out)          # fix 6, row 121
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^FAIL R08 .*\(INCOMPLETE: interrupted\)')
        self.assertFalse(out.strip().splitlines()[-1].startswith('INTERRUPTED'))     # the caller was not signalled
        self.assertFalse(E.is_interrupted_child(code, out))



class P2Amendment3(unittest.TestCase):
    """Corrective pass 2, amendment 3 (posted 14:38 on 2026-11-06): AM3-1 (a) the post-load identity check, (b) no load after a failed
    start check, (c) a case runner's --pin guarded; AM3-2 E point 3 as rewritten; AM3-4 the exit-3 INDETERMINATE CHECK form by pinned
    class (N and B accepted; another class, a missing class map entry or no class pins refused), with S11's class B form on a real
    baseline that exits 3.  Each in a temporary copy where it plants anything.  BUILDER-EXECUTED: NOT INDEPENDENT."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am3_')
        self.doc = E.load_pins()[0]
        self.decoy = os.path.join(self.tmp, 'decoy')
        self.marker = os.path.join(self.tmp, 'DECOY_APG_IMPORTED')
        shutil.copytree(os.path.join(ROOT, 'apg'), os.path.join(self.decoy, 'apg'), ignore=shutil.ignore_patterns('__pycache__'))
        with open(os.path.join(self.decoy, 'apg', '__init__.py'), 'a') as fh:
            fh.write('\nopen(%r, "a").write("x")\n' % self.marker)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def plant_load(self, tool, body):
        root = os.path.join(self.tmp, tool + '_' + str(len(os.listdir(self.tmp))))
        p2b_copy(root, [('tools/%s.py' % tool, 'def load():\n', 'def load():\n' + body)])
        return root

    def go(self, root, args, cwd=None):
        tmp = tempfile.mkdtemp(prefix='s1_am3r_')
        p = _p2sp.run([sys.executable, '-I', '-S', os.path.join(root, 'tools', args[0])] + list(args[1:]), cwd=cwd or root, capture_output=True,
                      text=True, timeout=1800, env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC',
                                                    'TMPDIR': tmp, 'PYTHONDONTWRITEBYTECODE': '1'})
        shutil.rmtree(tmp, ignore_errors=True)
        return p.returncode, p.stdout + p.stderr

    def no_work(self, out):
        self.assertNotRegex(out, r'(?m)^(CASE|PLANT|MUTANT) \S+ (?!NOT_RUN )')
        self.assertNotRegex(out, r'(?m)^CONTROL (start|end) CONTROL_(PASS|FAIL|TIMEOUT) ')

    # AM3-1 (a): the decoy harness, refused before any item, on four execution families
    def test_am3_1_a_a_decoy_harness_is_refused_before_any_item(self):
        for tool, extra, kw in (('run_contracts_s1', '', {'pins': self.doc['case_inventories']['run_contracts_s1']}),
                                ('run_fin_corpus_s1', '', {'pins': self.doc['case_inventories']['run_fin_corpus_s1']}),
                                ('run_faults_s1', '', {}), ('m2_mutants_s1', '    import apg  # planted: an M10 module importing apg\n', {})):
            with self.subTest(tool=tool):
                root = self.plant_load(tool, '    import sys as _s; _s.path.insert(0, %r)\n' % self.decoy + extra)
                code, out = self.go(root, [tool + '.py'])
                self.assertEqual(code, 2, out[-3000:])
                self.assertIn('RUN_ERROR IMPORT_OUTSIDE_EXTRACTION apg %s' % os.path.join(self.decoy, 'apg', '__init__.py'), out)
                self.no_work(out)
                self.assertTrue(out.strip().splitlines()[-1].endswith(' status=EVIDENCE_ERROR exit=2'))
                self.assertEqual(E.check_output(out, code, **kw), [], out[-3000:])
                self.assertTrue(os.path.exists(self.marker))          # AM3-1 (d): the decoy's import-time code did run
                os.remove(self.marker)

    # AM3-1 (b): a failed start check (a working directory other than the root): load() is never called
    def test_am3_1_b_no_load_after_a_failed_start_check(self):
        flag = os.path.join(self.tmp, 'LOAD_CALLED')
        for tool in ('run_faults_s1', 'm2_mutants_s1'):
            with self.subTest(tool=tool):
                root = self.plant_load(tool, '    open(%r, "w").close()\n' % flag)
                code, out = self.go(root, [tool + '.py'], cwd=self.tmp)
                self.assertEqual(code, 2, out[-3000:])
                self.assertRegex(out, r'(?m)^RUN_ERROR ENV_CWD ')
                self.assertFalse(os.path.exists(flag), 'load() ran after a failed start check')
                self.no_work(out)
                last = out.strip().splitlines()[-1]
                self.assertIn(' preflight=NOT_RUN control_start=NOT_RUN ', last)      # C.1's refusal form: every pinned item NOT_RUN
                kind = 'mutation' if tool.endswith('_mutants_s1') else 'sabotage'
                ids = self.doc['mutation_lists' if kind == 'mutation' else 'plant_lists'][tool]['ids']
                self.assertIn(' selected=%d ' % len(ids), last)
                self.assertEqual(E.check_output(out, code), [], out[-3000:])

    # AM3-1 (c): a case runner's --pin: the start checks and the post-load check before the harness, and no pin written after a refusal
    def test_am3_1_c_a_case_runners_pin_is_guarded(self):
        flag = os.path.join(self.tmp, 'BATCH_RAN')
        for name, body, cwd, want in (('decoy', '    import sys as _s; _s.path.insert(0, %r)\n' % self.decoy, None,
                                       'RUN_ERROR IMPORT_OUTSIDE_EXTRACTION apg '),
                                      ('cwd', '', self.tmp, 'RUN_ERROR ENV_CWD ')):
            with self.subTest(case=name):
                root = os.path.join(self.tmp, 'pin_' + name)
                p2b_copy(root, [('tools/run_contracts_s1.py', 'def load():\n', 'def load():\n' + body),
                                ('tools/run_contracts_s1.py', 'def batch(cand):\n', 'def batch(cand):\n    open(%r, "w").close()\n' % flag)])
                pins = os.path.join(root, 'tools', 'expected_counts.json')
                before = E.sha256_file(pins)
                code, out = self.go(root, ['run_contracts_s1.py', '--pin', '--reason', 'test', '--cause', 'test'], cwd=cwd)
                self.assertEqual(code, 2, out[-3000:])
                self.assertIn(want, out)
                self.assertFalse(os.path.exists(flag), 'the harness ran')
                self.assertEqual(E.sha256_file(pins), before, 'the pins were changed')
                self.assertNotIn('PINS ', out)

    # AM3-2: E point 3 as rewritten, on a real case runner and a real fault runner (on the final candidate)
    def test_am3_2_e_point_3(self):
        for args, kw in ((['run_contracts_s1.py'], {'pins': self.doc['case_inventories']['run_contracts_s1']}),
                         (['run_faults_s1.py', '--ids', self.doc['plant_lists']['run_faults_s1']['ids'][0]],
                          {'selected': [self.doc['plant_lists']['run_faults_s1']['ids'][0]]})):
            with self.subTest(tool=args[0]):
                code, out = self.go(ROOT, args)
                self.assertEqual(code, 0, out[-3000:])
                lines = out.splitlines()
                start = lines[:next(i for i, l in enumerate(lines) if l.startswith('LIMIT '))]
                self.assertFalse([l for l in start if re.match(r'^IMPORT apg(\.| )', l)], start)
                self.assertNotRegex(out, r'(?m)^RUN_ERROR ')
                self.assertIn('IMPORT_END apg %s' % os.path.join(ROOT, 'apg', '__init__.py'), lines)
                self.assertEqual(E.check_output(out, code, **kw), [], out[-3000:])

    # AM3-4 and S11: class B's W-1A.3 (a) form on a real baseline that exits 3 (run_m7_all_s1 G15), and the class rule
    def test_am3_4_class_b_a_real_baseline_that_exits_3(self):
        root = os.path.join(self.tmp, 'b')
        p2b_copy(root, [('tools/m7_mutants_s1.py', 'timeout=300,', 'timeout=4,')])
        with open(os.path.join(root, 'tools', 'mut_runner_s1.py'), 'w', encoding='utf-8') as fh:
            fh.write('import time\ntime.sleep(60)\n')
        p = os.path.join(root, 'tools', 'expected_counts.json')
        doc = json.load(open(p, encoding='utf-8'))
        old = doc['check_lists']['run_m7_all_s1']['G15'].split(' ')
        doc['check_lists']['run_m7_all_s1']['G15'] = E.check_identity('G15', old[1], old[2], E.sha256_file(os.path.join(root, 'tools', 'm7_mutants_s1.py')), old[4])
        E.write_pins(doc, 'test: G15 re-pinned in a copy whose baseline times out', 'tests_tools planted fault', [], path=p)
        code, out = self.go(root, ['run_m7_all_s1.py', '--group', '15'])
        self.assertEqual(code, 3, out[-3000:])
        self.assertRegex(out, r'(?m)^CHECK G15 INDETERMINATE source=child exit=3 marker=absent ')
        pins = E.wrapper_check_pins('run_m7_all_s1', doc)
        self.assertEqual(pins['classes']['G15'], 'B')
        self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])
        self.class_rule(out, code, pins, 'G15')

    def class_rule(self, out, code, pins, gid):
        need = 'CHECK %s outcome INDETERMINATE exit=3 needs a pinned class N or B' % gid
        for name, p in (('no pins', None), ('no class map', dict(pins, classes={})),
                        ('map without the group', dict(pins, classes={k: v for k, v in pins['classes'].items() if k != gid})),
                        ('class P', dict(pins, classes=dict(pins['classes'], **{gid: 'P'})))):
            with self.subTest(case=name):
                self.assertTrue(any(x.startswith(need) for x in E.check_output(out, code, pins=p)), (name, E.check_output(out, code, pins=p)))

    def test_am3_4_class_n_an_interrupted_regression_child(self):
        t = P2NoResultSupervisors('test_consumer_a_wrappers_class_n_check')
        t.setUp()
        try:
            root = t.copy('wrap_am3', edits=t.selfsig('run_regression_m8_s1'))
            code, out, seen = p2b_run(root, ['tools/run_m8_all_s1.py', '--group', '1'])
        finally:
            t.tearDown()
        self.assertRegex(out, r'(?m)^CHECK G01 INDETERMINATE source=child exit=3 ')
        pins = E.wrapper_check_pins('run_m8_all_s1')
        self.assertEqual(pins['classes']['G01'], 'N')
        self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])
        self.class_rule(out, code, pins, 'G01')


class P2GuardedImports(unittest.TestCase):
    """C.2 for each of the 33 runners (its first guarded load made to fail in a temporary copy) and C.3's wrapper consumer paths."""

    BREAK = {   # runner -> the file whose import is made to fail (the first load of its C table)
        'run_faults_s1': 'apg/contracts/run.py', 'run_history_contract_s1': 'apg/contracts/record_store_history_contract.py',
        'run_m3_faults_s1': 'apg/ingest/contracts_m3.py', 'run_m5_faults_s1': 'apg/det/contracts_m5.py',
        'run_m6_faults_s1': 'apg/mkt/contracts_m6.py', 'run_contracts_s1': 'apg/contracts/run.py', 'run_det_corpus_s1': 'apg/det/corpus_det.py',
        'run_fin_corpus_s1': 'apg/fin/corpus_fin.py', 'run_guard_contract_s1': 'apg/contracts/record_store_guard_contract.py',
        'run_ingest_corpus_s1': 'apg/ingest/corpus.py', 'run_m3_contracts_s1': 'apg/ingest/contracts_m3.py',
        'run_m5_contracts_s1': 'apg/det/contracts_m5.py', 'run_m6_contracts_s1': 'apg/mkt/contracts_m6.py',
        'run_m91_contracts_s1': 'apg/api/contracts_m9.py', 'run_mkt_corpus_s1': 'tests/corpus_mkt.py'}
    MUTATION = ('f67', 'f671', 'f672', 'f673', 'f674', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm73_store', 'm8', 'm91', 'mie', 'mie11')

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_p2g_')
        self.doc, _ = E.load_pins()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def broken(self, rel):
        root = os.path.join(self.tmp, rel.replace('/', '_'))
        if not os.path.exists(root):
            p2b_copy(root)
            p = os.path.join(root, rel)
            with open(p, encoding='utf-8') as fh:
                src = fh.read()
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write('raise ImportError("planted by test_runner_zero_work (C.2)")\n' + src)
        return root

    def refused(self, root, tool, kind, args=()):
        code, out, seen = p2b_run(root, ['tools/%s.py' % tool] + list(args))
        lines = [l for l in out.splitlines() if l.strip()]
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^RUN_ERROR IMPORT_FAILED \S+ ImportError planted by test_runner_zero_work \(C.2\)$')
        self.assertNotIn('Traceback', out)
        self.assertRegex(out, r'(?m)^ENV interpreter ')            # the start checks ran first
        self.assertTrue(lines[-1].startswith('RESULT v=3 kind=%s ' % kind) and lines[-1].endswith(' status=EVIDENCE_ERROR exit=2'))
        f = E.parse_result_line(lines[-1])[1]
        self.assertEqual(f['started'], 0)
        self.assertEqual(f['not_run'], f['selected'])
        self.assertEqual(E.check_output(out, code), [], out[-3000:])
        # amendment 5, row 46 (C.2 per runner): nothing the guard covers was imported before it (the start check's IMPORT lines name
        # only the tool and evkit), and every item is NOT_RUN cause=run_error, one line per selected item
        mods = [l.split()[1] for l in lines if l.startswith('IMPORT ')]
        self.assertTrue(all(m in ('__main__', 'tools') or m.startswith('tools.') for m in mods), mods)
        items = [l for l in lines if l.split(' ', 1)[0] in ('CASE', 'PLANT', 'MUTANT')]
        self.assertTrue(all(l.endswith(' NOT_RUN cause=run_error') for l in items), items)
        self.assertEqual(len(items), f['selected'])          # fix 6, row 46: always one line per selected item (never skipped)
        return f

    def test_c2_the_15_runners(self):
        for tool, rel in sorted(self.BREAK.items()):
            with self.subTest(tool=tool):
                root = self.broken(rel)
                if tool in self.doc['case_inventories'] and tool != 'run_history_contract_s1':
                    f = self.refused(root, tool, 'cases')
                    pins = self.doc['case_inventories'][tool]
                    self.assertEqual((f['suites'], f['selected']), (','.join(sorted(pins)), sum(len(v['ids']) for v in pins.values())))
                    # fix 6, row 46: the case hash of the selection, for every case runner
                    self.assertEqual(f['case_inventory_sha256'],
                                     E.sha256_lines(['%s/%s' % (su, c) for su in sorted(pins) for c in pins[su]['ids']]))
                else:
                    f = self.refused(root, tool, 'sabotage')
                    self.assertEqual(f['selected'], len(self.doc['plant_lists'][tool]['ids']))
                    self.assertEqual((f['preflight'], f['control_start']), ('NOT_RUN', 'NOT_RUN'))

    def test_c2_the_18_mutation_and_sabotage_successors(self):
        for t in self.MUTATION + ('sabotage_m10', 'sabotage_m8'):
            m10 = t if t.startswith('sabotage_') else t + '_mutants'
            tool = m10 + '_s1'
            with self.subTest(tool=tool):
                root = self.broken('tools/%s.py' % m10)
                kind = 'sabotage' if t.startswith('sabotage_') else 'mutation'
                f = self.refused(root, tool, kind)
                key = 'plant_lists' if kind == 'sabotage' else 'mutation_lists'
                self.assertEqual(f['selected'], len(set(self.doc[key][tool]['ids'])))
                self.assertEqual((f['preflight'], f['control_start']), ('NOT_RUN', 'NOT_RUN'))

    def test_c3_the_wrapper_consumer_paths(self):
        for wrapper, group, rel in (('run_m3_all_s1', '3', 'apg/contracts/run.py'), ('run_m3_all_s1', '4', 'apg/contracts/run.py'),
                                    ('run_m7_all_s1', '15', 'tools/m7_mutants.py')):
            with self.subTest(wrapper=wrapper, group=group):
                root = self.broken(rel)
                code, out, seen = p2b_run(root, ['tools/%s.py' % wrapper, '--group', group])
                self.assertEqual(code, 2, out[-2000:])
                self.assertRegex(out, r'(?m)^(FILE G%02d state=ITEM_ERROR |CHECK G%02d ITEM_ERROR )' % (int(group), int(group)))
                self.assertEqual(E.check_output(out, code), [], out[-3000:])


# ---------------------------------------------------------------------------------------------------------------------------------------
# Amendment 5 (owner, 2026-11-08 11:26, AM5-4 option A; S15 to S17 at 12:47; option A of 2026-11-09): Appendix A part 1 at tool level.
# Rewritten after the workspace loss of 2026-11-11 from the amendment and the rulings (recovery authorisation, rebuild rule).
# ---------------------------------------------------------------------------------------------------------------------------------------
def p2_identity_record(test, seen, out, run='tool'):
    """Amendment 5, row 121 (I.3, B.5; discrepancy 1): the per-test evidence record, kept with the T log (stderr): each descendant seen
    while the tool ran (pid:start:pgid, the pgid noted while it lived, during the run) and the CLEANUP lines of the cleaning supervisor."""
    ds = []
    for pid, start in sorted(seen):
        pg = P2B_PGIDS.get((pid, start), '-')        # fix 6 (D6-7): read while it lived, during the run (p2b_note_pgids)
        ds.append('%d:%d:%s' % (pid, start, pg))
    lines = ['P_IDENTITY test=%s run=%s descendants=%s' % (test.id(), run, ','.join(ds) or '-')]
    lines += ['P_IDENTITY test=%s %s' % (test.id(), l) for l in out.splitlines() if l.startswith('CLEANUP')]
    sys.stderr.write('\n'.join(lines) + '\n')


AM5_WRAP = r'''

def normal_message(normal):
    return {"failed": sorted(normal())}


def _p2_wrap(plants, run_reference):
    """amendment 5, row 42 (test only, in a copy): every plant and the reference control through _p2_behaviour; the control counts
    its own calls in _p2/controls, so its first call is control_start and its second control_end."""
    import os as _o
    def ctl():
        cf = _o.path.join(%(root)r, "_p2", "controls")
        open(cf, "a").write("x")
        return _p2_behaviour("control_start" if len(open(cf).read()) == 1 else "control_end", run_reference)
    return [(p[0], p[1], (lambda run=p[2]: _p2_behaviour("plant", run)), p[3]) for p in plants], ctl


def _am5_unkillable(pid):
    import os as _o
    f = _o.path.join(%(root)r, "_p2", "unkillable")
    return _o.path.exists(f) and str(pid) in open(f).read().split()
'''


class AM5FaultRunnerFullSet(P2FaultRunners):
    """Row 42 (B.5): the full set of P2FaultRunners on each of the other four fault runners.  The plants and the reference control are
    wrapped inside faults_main (in a copy), so the hang is each plant's own and never a start-control timeout."""
    TOOL = 'run_faults_s1'
    WRAP = ('    import time\n    by_id = {p[0]: p for p in plants}\n',
            '    import time\n    plants, run_reference = _p2_wrap(plants, run_reference)\n    by_id = {p[0]: p for p in plants}\n')

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am5f_')
        doc, _ = E.load_pins()
        self.pid0 = doc['plant_lists'][self.TOOL]['ids'][0]

    def tree(self, mode):
        root = os.path.join(self.tmp, mode.replace(':', '_'))
        p2b_copy(root, [('tools/evkit.py',) + self.WRAP])
        with open(os.path.join(root, 'tools', 'evkit.py'), 'a', encoding='utf-8') as fh:
            fh.write(P2_PLANT % {'root': root} + AM5_WRAP % {'root': root})
        os.makedirs(os.path.join(root, '_p2'))
        with open(os.path.join(root, '_p2', 'mode'), 'w') as fh:
            fh.write(mode)
        return root

    def run_f(self, mode, when=None, sig=_p2sig.SIGINT):
        root = self.tree(mode)
        code, out, seen = p2b_run(root, ['tools/%s.py' % self.TOOL, '--ids', self.pid0], when=when, sig=sig)
        p2_identity_record(self, seen, out)
        self.assertEqual(E.check_output(out, code, selected=[self.pid0]), [], out[-3000:])
        p2b_gone(self, seen)
        return code, out

    def plant_is(self, out, state, cause):
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_PASS cause=ok ')
        self.assertNotRegex(out, r'(?m)^CONTROL start CONTROL_TIMEOUT ')
        self.assertRegex(out, r'(?m)^PLANT %s %s cause=%s$' % (_p2re.escape(self.pid0), state, cause))

    test_the_hang_on_each_of_the_other_four_runners = None


class AM5FaultRunnerM3(AM5FaultRunnerFullSet):
    TOOL = 'run_m3_faults_s1'


class AM5FaultRunnerM5(AM5FaultRunnerFullSet):
    TOOL = 'run_m5_faults_s1'


class AM5FaultRunnerM6(AM5FaultRunnerFullSet):
    TOOL = 'run_m6_faults_s1'


class AM5FaultRunnerHistory(AM5FaultRunnerFullSet):
    TOOL = 'run_history_contract_s1'


del AM5FaultRunnerFullSet


class AM5PlantAndCaseHangs(unittest.TestCase):
    """Row 30 (P.10 valid_result_then_hangs) and row 25 (P.8 step 5) at tool level."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am5h_')
        self.doc, _ = E.load_pins()

    def tearDown(self):
        for f in getattr(self, 'unkill', ()):
            try:
                os.kill(f, 9)
            except OSError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def faults_tree(self, tool, mode, unkillable=False):
        root = os.path.join(self.tmp, '%s_%s' % (tool, mode.replace(':', '_')))
        edits = [('tools/evkit.py',) + AM5FaultRunnerFullSet_WRAP]
        if unkillable:     # simulated: SIGKILL does not take for a process whose pid the plant listed in _p2/unkillable
            edits.append(('tools/evkit.py', '        _pidfd_send_signal(fd, sig)\n        return True\n',
                          '        if sig == _signal.SIGKILL and _am5_unkillable(pid):\n            return False\n'
                          '        _pidfd_send_signal(fd, sig)\n        return True\n'))
        p2b_copy(root, edits)
        extra = r'''

def _am5_valid_then_hang(where, normal):
    import os as _o, signal as _sg, json as _j, time as _tm
    d = _o.path.join(%(root)r, '_p2')
    mode = open(_o.path.join(d, 'mode')).read().strip()
    if not mode.startswith(where + ':'):
        return normal()
    _sg.signal(_sg.SIGTERM, _sg.SIG_IGN)
    if mode.endswith('vunkillable'):
        open(_o.path.join(d, 'unkillable'), 'a').write('%%d\n' %% _o.getpid())
        # it outlives the tool: it lets go of the tool's output pipe, so the test's read of that pipe can end when the tool exits
        _nul = _o.open(_o.devnull, _o.O_WRONLY)
        _o.dup2(_nul, 1)
        _o.dup2(_nul, 2)
    open(_o.path.join(d, 'started'), 'w').close()
    w = max(int(x) for x in _o.listdir('/proc/self/fd') if int(x) > 2 and _o.path.exists('/proc/self/fd/' + x))
    data = _j.dumps(normal_message(normal)).encode()
    _o.write(w, len(data).to_bytes(4, 'big') + data)
    _o.close(w)
    while True:
        _tm.sleep(1)
''' % {'root': root}
        with open(os.path.join(root, 'tools', 'evkit.py'), 'a', encoding='utf-8') as fh:
            fh.write(P2_PLANT % {'root': root} + AM5_WRAP % {'root': root} + extra +
                     '\n\n_p2_behaviour_real = _p2_behaviour\n\n\ndef _p2_behaviour(where, normal):\n'
                     '    return _am5_valid_then_hang(where, normal) if open(%r).read().startswith(where + ":v") else '
                     '_p2_behaviour_real(where, normal)\n' % os.path.join(root, '_p2', 'mode'))
        os.makedirs(os.path.join(root, '_p2'))
        with open(os.path.join(root, '_p2', 'mode'), 'w') as fh:
            fh.write(mode)
        return root

    def test_row30_a_forked_plant_that_ignores_sigterm_after_its_valid_result(self):
        pid0 = self.doc['plant_lists']['run_faults_s1']['ids'][0]
        root = self.faults_tree('run_faults_s1', 'plant:vignore')
        code, out, seen = p2b_run(root, ['tools/run_faults_s1.py', '--ids', pid0])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^PLANT %s INDETERMINATE cause=processes_left$' % _p2re.escape(pid0))
        rec = [l for l in out.splitlines() if l.startswith('CLEANUP %s ' % pid0)]
        self.assertEqual(len(rec), 1, out[-2000:])
        self.assertRegex(rec[0], r' sigkill=1 .* deadline=grace .* remaining=-$')
        self.assertRegex(out, r'(?m)^CLEANUP_SUMMARY units=\d+ leaked=1 remaining=0$')
        self.assertEqual(E.check_output(out, code, selected=[pid0]), [], out[-3000:])
        p2b_gone(self, seen)

    def test_row30_a_forked_plant_that_cannot_be_killed_after_its_valid_result(self):
        pid0 = self.doc['plant_lists']['run_faults_s1']['ids'][0]
        root = self.faults_tree('run_faults_s1', 'plant:vunkillable', unkillable=True)
        code, out, seen = p2b_run(root, ['tools/run_faults_s1.py', '--ids', pid0])
        p2_identity_record(self, seen, out)
        self.unkill = [int(x) for x in open(os.path.join(root, '_p2', 'unkillable')).read().split()]
        alive = [p for p in self.unkill if E.proc_stat(p) is not None and E.proc_stat(p)[0] != 'Z']
        self.assertEqual(len(alive), 1)                     # still there when the tool printed its RESULT line and exited
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^PLANT %s INDETERMINATE cause=processes_left$' % _p2re.escape(pid0))
        self.assertRegex(out, r'(?m)^RUN_ERROR CLEANUP_INCOMPLETE %s %d:\d+$' % (_p2re.escape(pid0), alive[0]))
        self.assertRegex(out, r'(?m)^CLEANUP %s .* deadline=kill_verify .* remaining=%d:\d+$' % (_p2re.escape(pid0), alive[0]))
        self.assertRegex(out, r'(?m)^CLEANUP_SUMMARY units=\d+ leaked=1 remaining=1$')
        self.assertEqual(E.check_output(out, code, selected=[pid0]), [], out[-3000:])

    def test_row30_a_forked_case_that_ignores_sigterm_after_its_valid_result(self):
        ids = self.doc['case_inventories']['run_fin_corpus_s1']['fin_corpus']['ids']
        root = os.path.join(self.tmp, 'fin')
        old = "def run_case(cand, suite, cid):\n"
        body = ('    if cid == %r:\n        import os, signal, json, time\n        signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                '        w = max(int(x) for x in os.listdir("/proc/self/fd") if int(x) > 2 and os.path.exists("/proc/self/fd/" + x))\n'
                '        data = json.dumps({"ok": True, "detail": ""}).encode()\n'
                '        os.write(w, len(data).to_bytes(4, "big") + data)\n        os.close(w)\n        while True:\n'
                '            time.sleep(1)\n' % ids[0])
        p2b_copy(root, [('tools/run_fin_corpus_s1.py', old, old + body)])
        code, out, seen = p2b_run(root, ['tools/run_fin_corpus_s1.py', '--only', ','.join(ids[:2])])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CASE fin_corpus/%s INDETERMINATE cause=processes_left$' % _p2re.escape(ids[0]))
        self.assertRegex(out, r'(?m)^CASE fin_corpus/%s PASS cause=ok$' % _p2re.escape(ids[1]))
        self.assertRegex(out, r'(?m)^CLEANUP fin_corpus/%s .* sigkill=1 ' % _p2re.escape(ids[0]))
        self.assertEqual(E.check_output(out, code, pins=self.doc['case_inventories']['run_fin_corpus_s1']), [], out[-3000:])
        p2b_gone(self, seen)

    def test_row25_a_failed_id_outside_the_paired_inventory_is_rejected_on_all_five_pairs(self):
        # P.8 step 5 (amendment 2 reading 12): a plant whose message names a case id the paired case runner's pinned inventory does
        # not hold is bad_result, never CAUGHT
        pairs = getattr(E, 'FAULT_CASE_PAIRS', {})
        self.assertEqual(len(pairs), 5, pairs)
        for tool in sorted(pairs):
            with self.subTest(tool=tool):
                pid0 = self.doc['plant_lists'][tool]['ids'][0]
                root = os.path.join(self.tmp, 'p8_' + tool)
                p2b_copy(root, [('tools/evkit.py',) + AM5FaultRunnerFullSet_WRAP])
                with open(os.path.join(root, 'tools', 'evkit.py'), 'a', encoding='utf-8') as fh:
                    fh.write(P2_PLANT % {'root': root} + AM5_WRAP % {'root': root} +
                             '\n\n_p2_behaviour_real = _p2_behaviour\n\n\ndef _p2_behaviour(where, normal):\n'
                             '    if where == "plant":\n        return set(normal()) | {"NOT-A-PINNED-CASE-ID"}\n'
                             '    return _p2_behaviour_real(where, normal)\n')
                os.makedirs(os.path.join(root, '_p2'))
                open(os.path.join(root, '_p2', 'mode'), 'w').close()
                code, out, seen = p2b_run(root, ['tools/%s.py' % tool, '--ids', pid0])
                p2_identity_record(self, seen, out)
                self.assertRegex(out, r'(?m)^PLANT %s INDETERMINATE cause=bad_result$' % _p2re.escape(pid0), out[-2000:])
                self.assertNotRegex(out, r'(?m)^PLANT %s CAUGHT' % _p2re.escape(pid0))
                self.assertEqual(code, 3, out[-2000:])
                self.assertEqual(E.check_output(out, code, selected=[pid0]), [], out[-3000:])
                p2b_gone(self, seen)
                shutil.rmtree(root, ignore_errors=True)


AM5FaultRunnerFullSet_WRAP = ('    import time\n    by_id = {p[0]: p for p in plants}\n',
                              '    import time\n    plants, run_reference = _p2_wrap(plants, run_reference)\n    by_id = {p[0]: p for p in plants}\n')


class AM5Wrappers(unittest.TestCase):
    """Rows 22 (a wrapper FILE and CHECK leak), 51 to 53 and 55 to 56 (F.2 in wrapper_main), and S16 (owner 12:47, option A) on
    run_m4_all_s1, in temporary copies."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am5w_')
        self.doc, _ = E.load_pins()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def m4(self, name, edits=(), prepend=(), append=()):
        root = p2b_copy(os.path.join(self.tmp, name), edits)
        for rel, text in append:
            with open(os.path.join(root, rel), 'a', encoding='utf-8') as fh:
                fh.write('\n' + text)
        for rel, text in prepend:
            p = os.path.join(root, rel)
            src = open(p, encoding='utf-8').read()
            head, rest = src.split('\n', 1)
            open(p, 'w', encoding='utf-8').write(head + '\n' + text + rest)
        os.makedirs(os.path.join(root, '_p2'), exist_ok=True)
        return root

    def wpins(self):
        return E.wrapper_check_pins('run_m4_all_s1', self.doc)

    def test_row51_to_53_run_m4_all_s1_between_groups(self):
        for sig in (_p2sig.SIGINT, _p2sig.SIGTERM):
            with self.subTest(sig=sig.name):
                hold = ("            stop_now = CANCEL.set and cls != 'H'",
                        "            if gid == 'G02':\n                open(os.path.join(root, '_p2', 'between'), 'w').close()\n"
                        "                _time.sleep(3)\n            stop_now = CANCEL.set and cls != 'H'")
                root = self.m4('between_' + sig.name, [('tools/evkit.py',) + hold])
                code, out, seen = p2b_run(root, ['tools/run_m4_all_s1.py'], when=p2b_mark('between'), sig=sig)
                p2_identity_record(self, seen, out)
                self.assertEqual(code, 3, out[-2000:])
                self.assertRegex(out, r'(?m)^FILE G01 state=COMPLETED ')
                for g in ('G02', 'G13'):
                    self.assertRegex(out, r'(?m)^FILE %s state=NOT_RUN ' % g)
                self.assertRegex(out, r'(?m)^CHECK G14 NOT_RUN ')
                for g in ('G16', 'G17', 'G18'):          # row 56, reading 16: the H groups after the interrupt keep their line
                    self.assertRegex(out, r'(?m)^EXCLUDED %s NOT_RUN_HISTORICAL ' % g)
                self.assertRegex(out.strip().splitlines()[-2], r'^INTERRUPTED signal=%s at=\S+ received=1$' % sig.name)
                self.assertEqual(E.check_output(out, code, pins=self.wpins()), [], out[-3000:])
                p2b_gone(self, seen)

    def test_row55_an_interrupted_wrapper_group(self):
        # F.2 (b): the group running at the signal is INDETERMINATE, the groups after it NOT_RUN, the H groups EXCLUDED; RESULT exit 3.
        # G01's child is held in the copy (a marker, then a sleep), so the signal lands while it runs, never between groups
        hold = ('import os as _am5o, sys as _am5y, time as _am5t\n'
                'if "test_fin_arith.py" in _am5y.argv:\n'
                '    open(_am5o.path.join(%r, "_p2", "in_g01"), "w").close()\n    _am5t.sleep(30)\n')
        root = os.path.join(self.tmp, 'in_group')
        root = self.m4('in_group', prepend=[('tools/run_m2_tests_s1.py', hold % root)])
        code, out, seen = p2b_run(root, ['tools/run_m4_all_s1.py'], when=p2b_mark('in_g01'))
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^FILE G01 state=INDETERMINATE ')
        for g in ('G02', 'G13'):
            self.assertRegex(out, r'(?m)^FILE %s state=NOT_RUN ' % g)
        self.assertRegex(out, r'(?m)^CHECK G14 NOT_RUN ')
        self.assertRegex(out, r'(?m)^EXCLUDED G18 NOT_RUN_HISTORICAL ')
        self.assertTrue(out.strip().splitlines()[-1].endswith(' exit=3'))
        self.assertEqual(E.check_output(out, code, pins=self.wpins()), [], out[-3000:])
        p2b_gone(self, seen)

    def test_row22_a_wrapper_file_group_that_leaks(self):
        leak = ('import subprocess as _am5s, sys as _am5y\n'
                '_am5s.Popen([_am5y.executable, "-c", "import time; time.sleep(30)"])\n')
        root = self.m4('file_leak', prepend=[('tools/run_m2_tests_s1.py', leak)])
        code, out, seen = p2b_run(root, ['tools/run_m4_all_s1.py', '--group', '1'])
        p2_identity_record(self, seen, out)
        self.assertRegex(out, r'(?m)^FILE G01 state=INDETERMINATE ')
        self.assertRegex(out, r'(?m)^CLEANUP G01 by=run_m4_all_s1:\d+ ')
        self.assertEqual(code, 3, out[-2000:])
        self.assertEqual(E.check_output(out, code, pins=self.wpins()), [], out[-3000:])
        p2b_gone(self, seen)

    def test_row22_s16_a_wrapper_check_group_that_leaks(self):
        # a class P check whose child leaks is INDETERMINATE whatever its exit (P.6); S16: the checker accepts that line because the
        # group's CLEANUP record is in the output, and refuses it without the record
        leak = ('import subprocess as _am5s, sys as _am5y\n'
                '_am5s.Popen([_am5y.executable, "-c", "import time; time.sleep(30)"])\n')
        # the check's own tool file is pinned by its CHECK identity, so the leak is planted in the module it imports
        root = self.m4('check_leak', append=[('apg/fin/golden_fin.py', leak)])
        code, out, seen = p2b_run(root, ['tools/run_m4_all_s1.py', '--group', '14'])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 3, out[-2000:])
        m = _p2re.search(r'(?m)^CHECK G14 INDETERMINATE source=child exit=(\S+) marker=(\S+) ', out)
        self.assertTrue(m, out[-2000:])
        self.assertRegex(out, r'(?m)^CLEANUP G14 by=run_m4_all_s1:\d+ ')
        pins = self.wpins()
        self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])
        without = '\n'.join(l for l in out.splitlines() if not l.startswith('CLEANUP G14 '))
        self.assertIn('CHECK G14 outcome INDETERMINATE contradicts exit=%s marker=%s' % (m.group(1), m.group(2)),
                      E.check_output(without, code, pins=pins))
        p2b_gone(self, seen)

    def test_s16_an_exit_3_check_of_a_class_that_is_not_n_or_b(self):
        # S16 with AM3-4: an exit=3 INDETERMINATE CHECK of a class P group is accepted when the group's CLEANUP record is present, and
        # refused without it, with AM3-4's message
        leak = ('import subprocess as _am5s, sys as _am5y\n'
                '_am5s.Popen([_am5y.executable, "-c", "import time; time.sleep(30)"])\n')
        root = self.m4('check_exit3', append=[('apg/fin/golden_fin.py', leak)])
        code, out, seen = p2b_run(root, ['tools/run_m4_all_s1.py', '--group', '14'])
        three = _p2re.sub(r'(?m)^(CHECK G14 INDETERMINATE source=child) exit=\S+ marker=\S+ ', r'\1 exit=3 marker=seen ', out)
        pins = self.wpins()
        self.assertEqual(pins['classes']['G14'], 'P')
        self.assertEqual(E.check_output(three, code, pins=pins), [], three[-3000:])
        without = '\n'.join(l for l in three.splitlines() if not l.startswith('CLEANUP G14 '))
        self.assertIn('CHECK G14 outcome INDETERMINATE exit=3 needs a pinned class N or B (class: P)',
                      E.check_output(without, code, pins=pins))
        p2b_gone(self, seen)


class AM5CaseRunnerReadings(unittest.TestCase):
    """Rows 97 (reading 10 and S17 (b)), 98 (reading 11) and 95 (reading 8)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am5k_')
        self.doc, _ = E.load_pins()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def go(self, tool, *args):
        p = _p2sp.run([sys.executable, '-I', '-S', 'tools/%s.py' % tool] + list(args), cwd=ROOT, capture_output=True, text=True,
                      timeout=900, stdin=_p2sp.DEVNULL)
        return p.returncode, p.stdout

    def test_row97_argument_errors_are_step_3_refusals(self):
        pins = self.doc['case_inventories']['run_contracts_s1']
        for args, msg in ((['--suite'], 'missing value for --suite'),
                          (['--path', self.tmp], '--path without a candidate factory'),
                          (['--factory', 'p2cand:Store'], 'a candidate factory needs --path'),
                          (['--path', self.tmp, '--factory', 'p2cand::Store'], '--factory must be module:attr'),
                          (['--path', self.tmp, '--factory', 'p2cand:Store:x'], '--factory must be module:attr'),
                          (['--path', self.tmp, '--factory', 'p2 cand:Store'], '--factory must be module:attr'),
                          (['--bogus'], 'unknown argument --bogus')):
            with self.subTest(args=args):
                code, out = self.go('run_contracts_s1', *args)
                self.assertEqual(code, 2, out[-2000:])
                self.assertRegex(out, r'(?m)^RUN_ERROR SELECTION_INVALID %s' % _p2re.escape(msg))
                f = E.parse_result_line(out.strip().splitlines()[-1])[1]
                self.assertEqual((f['suites'], f['suites_selected'], f['selected']), ('-', 0, 0))
                self.assertEqual(f['case_inventory_sha256'], E.sha256_lines([]))
                self.assertNotRegex(out, r'(?m)^CASE ')
                self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])

    def test_row98_the_suites_in_both_orders(self):
        pins = self.doc['case_inventories']['run_contracts_s1']
        a = self.go('run_contracts_s1', '--suite', 'record_store', '--suite', 'audit_log')
        b = self.go('run_contracts_s1', '--suite', 'audit_log', '--suite', 'record_store')
        fa = E.parse_result_line(a[1].strip().splitlines()[-1])[1]
        fb = E.parse_result_line(b[1].strip().splitlines()[-1])[1]
        self.assertEqual((a[0], b[0]), (0, 0))
        self.assertEqual(fa['case_inventory_sha256'], fb['case_inventory_sha256'])
        self.assertEqual((fa['suites'], fb['suites']), ('audit_log,record_store', 'audit_log,record_store'))
        order = lambda out: [l.split()[1].split('/')[0] for l in out.splitlines() if l.startswith('CASE ')]
        oa, ob = order(a[1]), order(b[1])
        self.assertEqual(oa, sorted(oa, key=lambda s: s != 'record_store'))     # the requested execution order is kept
        self.assertEqual(ob, sorted(ob, key=lambda s: s != 'audit_log'))
        self.assertEqual([l for l in a[1].splitlines() if l.startswith('CASE record_store/')],
                         ['CASE record_store/%s PASS cause=ok' % c for c in pins['record_store']['ids']])
        for out, code in ((a[1], a[0]), (b[1], b[0])):
            self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])

    def test_row95_a_start_control_interrupted_before_it_began(self):
        # reading 8: the signal arrives before the start control has started: CONTROL start CONTROL_INTERRUPTED cause=interrupted,
        # control_start=FAIL, every plant NOT_RUN
        pid0 = self.doc['plant_lists']['run_faults_s1']['ids'][0]
        hold = ("        set_phase('control_start')\n        try:\n            cs, cl = control_run('start')\n",
                "        set_phase('control_start')\n        open(os.path.join(root, '_p2', 'before'), 'w').close()\n"
                "        _time.sleep(3)\n        try:\n            cs, cl = control_run('start')\n")
        root = p2b_copy(os.path.join(self.tmp, 'before'), [('tools/evkit.py',) + hold])
        os.makedirs(os.path.join(root, '_p2'))
        code, out, seen = p2b_run(root, ['tools/run_faults_s1.py', '--ids', pid0], when=p2b_mark('before'))
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_INTERRUPTED cause=interrupted$')
        self.assertIn(' control_start=FAIL ', out.strip().splitlines()[-1])
        self.assertRegex(out, r'(?m)^PLANT %s NOT_RUN ' % _p2re.escape(pid0))
        self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=SIGINT at=control_start received=1')
        self.assertEqual(E.check_output(out, code, selected=[pid0]), [], out[-3000:])
        p2b_gone(self, seen)


class AM5AttributionTable(unittest.TestCase):
    """Row 73 (AM-5 (c)) and row 100 (reading 14) at tool level, in temporary copies."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am5a_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    LEAK = "_subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])"

    def test_child_unittest_runner_start_as_its_parent_reads_it(self):
        # the child runner's AUIF verification (its run start) leaves a process: the child refuses (PROCESSES_LEFT run_start, exit 2),
        # and its parent reads it as CHILD_EVIDENCE_ERROR: FILE ITEM_ERROR; the parent itself has no leak
        edit = ("                _auif_dependency.ensure(argv['verify_auif'])\n",
                "                _auif_dependency.ensure(argv['verify_auif'])\n                %s\n" % self.LEAK)
        root = p2b_copy(os.path.join(self.tmp, 'cur_parent'), [('tools/evkit.py',) + edit])
        code, out, seen = p2b_run(root, ['tools/run_m8_tests_s1.py', '--file', 'test_m8_dependency.py'])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 2, out[-3000:])
        self.assertRegex(out, r'(?m)^FILE test_m8_dependency\.py state=ITEM_ERROR ')
        self.assertIn('CHILD_EVIDENCE_ERROR', out)
        self.assertNotRegex(out, r'(?m)^RUN_ERROR PROCESSES_LEFT ')
        self.assertEqual(E.check_output(out, code), [], out[-3000:])
        p2b_gone(self, seen)

    def test_run_start_and_run_end_of_a_mutation_tool(self):
        # m8_mutants_s1: a leak in its AUIF verification (run_start) refuses the run (every mutant NOT_RUN); one by its after-check
        # (run_end) is RUN_ERROR PROCESSES_LEFT run_end
        doc, _ = E.load_pins()
        first = doc['mutation_lists']['m8_mutants_s1']['ids'][0]
        root = p2b_copy(os.path.join(self.tmp, 'm8_start'),
                        [('tools/m8_mutants_s1.py', '            dep = dependency.ensure()\n',
                          '            dep = dependency.ensure()\n            import subprocess as _s\n'
                          '            _s.Popen([sys.executable, "-c", "import time; time.sleep(30)"])\n')])
        code, out, seen = p2b_run(root, ['tools/m8_mutants_s1.py', '--ids', first])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 2, out[-3000:])
        self.assertRegex(out, r'(?m)^RUN_ERROR PROCESSES_LEFT run_start$')
        self.assertEqual([l for l in out.splitlines() if l.startswith('MUTANT ')], ['MUTANT %s NOT_RUN cause=run_error' % first])
        self.assertRegex(out, r'(?m)^CLEANUP run_start by=m8_mutants_s1:\d+ ')
        self.assertEqual(E.check_output(out, code), [], out[-3000:])
        p2b_gone(self, seen)
        # fix 6 (D6-3, row 73): the run_end half its name promises: the after-check's reverification leaves a process
        root = am6_m8_copy(os.path.join(self.tmp, 'm8_end'), 'reverify')
        code, out, seen = p2b_run(root, ['tools/m8_mutants_s1.py', '--ids', first])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 2, out[-3000:])
        self.assertRegex(out, r'(?m)^MUTANT %s (SURVIVED|EQUIVALENT|KILLED) ' % _p2re.escape(first))     # its outcome is kept
        self.assertRegex(out, r'(?m)^RUN_ERROR PROCESSES_LEFT run_end$')
        self.assertRegex(out, r'(?m)^CLEANUP run_end by=m8_mutants_s1:\d+ ')
        self.assertEqual(E.check_output(out, code), [], out[-3000:])
        p2b_gone(self, seen)

    def test_row100_the_child_runner_is_a_supervisor_only_when_it_verifies_a_copy(self):
        # reading 14: child_unittest_runner declares itself a supervisor immediately before verify_auif, and only then; with
        # containment unavailable it refuses there (ENV_NO_PROCESS_SUPERVISION), while the same runner without a copy runs as a leaf
        r = _p2sp.run([sys.executable, '-I', '-S', '-c', 'import sys; sys.path.insert(0, %r)\nfrom apg_auif import dependency as d\n'
                       'print(d.extract(sys.argv[1]))' % ROOT, os.path.join(self.tmp, 'auif')], cwd=ROOT, capture_output=True, text=True,
                      timeout=600)
        auif = r.stdout.strip().splitlines()[-1]
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': self.tmp,
               'PYTHONDONTWRITEBYTECODE': '1'}

        def child(root, with_copy):
            e = dict(env, APG_AUIF_ROOT=auif) if with_copy else env
            p = _p2sp.run([sys.executable, '-I', '-S', 'tools/child_unittest_runner.py', '--caller', 'run_m8_tests_s1', '--mode', 'full',
                           'tests_m8.test_m8_dependency'], cwd=root, capture_output=True, text=True, timeout=1800, env=e)
            return p.returncode, p.stdout
        code, out = child(ROOT, True)
        self.assertEqual(code, 0, out[-2000:])
        self.assertRegex(out, r'(?m)^CLEANUP_SUMMARY units=\d+ leaked=0 remaining=0$')
        code, out = child(ROOT, False)
        self.assertNotRegex(out, r'(?m)^CLEANUP_SUMMARY ')
        root = p2b_copy(os.path.join(self.tmp, 'nolibc'), [('tools/evkit.py', "_LIBC = 'libc.so.6'", "_LIBC = 'libc-missing.so'")])
        code, out = child(root, True)
        self.assertEqual(code, 2, out[-2000:])
        self.assertIn('RUN_ERROR ENV_NO_PROCESS_SUPERVISION unavailable_OSError', out)
        self.assertRegex(out, r'(?m)^FILE test_m8_dependency\.py state=NOT_RUN ')
        code, out = child(root, False)
        self.assertNotIn('ENV_NO_PROCESS_SUPERVISION', out)


AM5_BATCH_OLD = ('def batch(cand):\n    return [[s, cid, bool(ok), str(d)] for s, cid, text, ok, d in R.run(cand.get("--factory") or reference)]\n')


class AM5CaseRunnerOrder(unittest.TestCase):
    """Rows 31 (A.1 steps 5, 6 and 8 keep the resolved selection), 36 and 46 (A.4 / C.2: the import failure keeps the selection and its
    hash, history case mode included), 79 (AM2-1 (a)), 81 (AM2-1 (d) rows 7 and 3 with a leak), 59 and 60 (K.2), in copies."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am5o_')
        self.doc, _ = E.load_pins()
        self.pins = self.doc['case_inventories']['run_contracts_s1']

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def batch_tree(self, name, body):
        root = os.path.join(self.tmp, name)
        p2b_copy(root, [('tools/run_contracts_s1.py', AM5_BATCH_OLD, AM5_BATCH_OLD.replace('def batch(', 'def _batch(') +
                         '\n\ndef batch(cand):\n    rows = _batch(cand)\n' + body + '    return rows\n')])
        os.makedirs(os.path.join(root, '_p2'), exist_ok=True)
        return root

    def kept(self, out, suites, cause='run_error'):
        f = E.parse_result_line(out.strip().splitlines()[-1])[1]
        self.assertEqual(f['suites'], ','.join(sorted(suites)))
        want = ['%s/%s' % (s, c) for s in suites for c in self.pins[s]['ids']]
        self.assertEqual(f['selected'], len(want))
        self.assertEqual(f['case_inventory_sha256'], E.sha256_lines(['%s/%s' % (s, c) for s in sorted(suites) for c in self.pins[s]['ids']]))
        self.assertEqual([l for l in out.splitlines() if l.startswith('CASE ')], ['CASE %s NOT_RUN cause=%s' % (w, cause) for w in want])

    def test_row31_step_5_a_candidate_that_cannot_be_loaded(self):
        code, out, seen = p2b_run(ROOT, ['tools/run_contracts_s1.py', '--suite', 'record_store', '--path', self.tmp, '--factory',
                                         'am5_no_such_module:Store'])
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^RUN_ERROR CANDIDATE_IMPORT_FAILED ')
        self.kept(out, ['record_store'])
        self.assertEqual(E.check_output(out, code, pins=self.pins), [], out[-3000:])

    def test_row31_step_6_an_inventory_that_differs(self):
        root = self.batch_tree('step6', '    rows = [r for r in rows if r[1] != "RS-01"]\n')
        code, out, seen = p2b_run(root, ['tools/run_contracts_s1.py', '--suite', 'record_store'])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^RUN_ERROR CASE_INVENTORY_MISMATCH record_store ')
        self.kept(out, ['record_store'])
        self.assertEqual(E.check_output(out, code, pins=self.pins), [], out[-3000:])
        p2b_gone(self, seen)

    def test_row31_step_8_the_end_check_keeps_the_selection(self):
        # the end identity check (IMPORT_END) refuses after the cases: the selection and its case lines are kept
        root = self.batch_tree('step8', '')
        p = os.path.join(root, 'tools', 'evkit.py')
        src = open(p, encoding='utf-8').read()
        old = 'def import_identity(root=ROOT, preloaded=(), candidate_paths=()):\n'
        self.assertEqual(src.count(old), 1)
        src = src.replace(old, old + '    if [f.function for f in __import__("inspect").stack()][1] == "cases_main":\n'
                          '        if _AM5_END[0]:\n            return [RunError("IMPORT_OUTSIDE_EXTRACTION", "am5 planted")], []\n'
                          '        _AM5_END[0] = True\n')
        open(p, 'w', encoding='utf-8').write(src + '\n_AM5_END = [False]\n')
        code, out, seen = p2b_run(root, ['tools/run_contracts_s1.py', '--suite', 'record_store'])
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^RUN_ERROR IMPORT_OUTSIDE_EXTRACTION am5 planted$')
        f = E.parse_result_line(out.strip().splitlines()[-1])[1]
        self.assertEqual((f['suites'], f['selected']), ('record_store', len(self.pins['record_store']['ids'])))
        self.assertEqual(E.check_output(out, code, pins=self.pins), [], out[-3000:])

    def test_row36_row46_an_import_failure_keeps_the_selection_and_its_hash(self):
        for tool, args, pkey, suites in (('run_contracts_s1', ['--suite', 'record_store'], 'run_contracts_s1', ['record_store']),
                                         ('run_history_contract_s1', ['--path', self.tmp, '--factory', 'am5cand:Store'],
                                          'run_history_contract_s1', None)):
            with self.subTest(tool=tool):
                rel = P2GuardedImports.BREAK[tool]
                root = p2b_copy(os.path.join(self.tmp, 'imp_' + tool))
                p = os.path.join(root, rel)
                src = open(p, encoding='utf-8').read()
                open(p, 'w', encoding='utf-8').write('raise ImportError("planted by test_runner_zero_work (C.2)")\n' + src)
                code, out, seen = p2b_run(root, ['tools/%s.py' % tool] + args)
                self.assertEqual(code, 2, out[-2000:])
                self.assertRegex(out, r'(?m)^RUN_ERROR IMPORT_FAILED ')
                pins = self.doc['case_inventories'][pkey]
                f = E.parse_result_line(out.strip().splitlines()[-1])[1]
                ss = suites or sorted(pins)
                self.assertEqual(f['suites'], ','.join(sorted(ss)))
                self.assertEqual(f['case_inventory_sha256'], E.sha256_lines(['%s/%s' % (s, c) for s in sorted(ss) for c in pins[s]['ids']]))
                cases = [l for l in out.splitlines() if l.startswith('CASE ')]
                self.assertEqual(len(cases), sum(len(pins[s]['ids']) for s in ss))
                self.assertTrue(all(l.endswith(' NOT_RUN cause=run_error') for l in cases))
                self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])

    def test_row79_no_batch_after_a_start_refusal_and_pin_uses_the_batch_unit(self):
        mark = os.path.join(self.tmp, 'batch_ran')
        root = self.batch_tree('pin', '    import os\n    open(%r, "a").write("%%d %%d\\n" %% (os.getpid(), os.getpgid(0)))\n' % mark)
        p = _p2sp.run([sys.executable, '-I', '-S', os.path.join(root, 'tools', 'run_contracts_s1.py')], cwd=self.tmp, capture_output=True,
                      text=True, timeout=600, stdin=_p2sp.DEVNULL)
        self.assertEqual(p.returncode, 2, p.stdout[-2000:])
        self.assertRegex(p.stdout, r'(?m)^RUN_ERROR ENV_CWD ')
        self.assertFalse(os.path.exists(mark), 'the batch ran after a start refusal')
        p = _p2sp.run([sys.executable, '-I', '-S', 'tools/run_contracts_s1.py', '--pin', '--reason', 'am5 test', '--cause', 'am5 test'],
                      cwd=root, capture_output=True, text=True, timeout=600, stdin=_p2sp.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stdout[-2000:])
        pid, pgid = open(mark).read().split()[:2]
        self.assertEqual(pid, pgid)                  # it ran in a forked unit: its own process group

    def test_row81_precedence_rows_7_and_3_with_a_leak(self):
        leak = '    import subprocess, sys\n    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])\n'
        root = self.batch_tree('row7', leak + '    rows = [r for r in rows if r[1] != "RS-01"]\n')
        code, out, seen = p2b_run(root, ['tools/run_contracts_s1.py', '--suite', 'record_store'])
        p2_identity_record(self, seen, out)
        self.assertRegex(out, r'(?m)^RUN_ERROR CASE_INVENTORY_MISMATCH record_store ')     # row 7: the mismatch wins over the leak
        self.assertNotRegex(out, r'(?m)^CASE \S+ INDETERMINATE cause=processes_left$')
        self.assertRegex(out, r'(?m)^CLEANUP \S+ by=run_contracts_s1:\d+ ')                # the leak is still recorded
        self.assertEqual(E.check_output(out, code, pins=self.pins), [], out[-3000:])
        p2b_gone(self, seen)
        root = self.batch_tree('row3', leak + '    raise KeyError("planted")\n')
        code, out, seen = p2b_run(root, ['tools/run_contracts_s1.py', '--suite', 'record_store'])
        p2_identity_record(self, seen, out)
        self.assertRegex(out, r'(?m)^RUN_ERROR CASES_ENUMERATION_FAILED KeyError$')        # row 3 keeps its result with a leak
        self.kept(out, ['record_store'])
        self.assertRegex(out, r'(?m)^CLEANUP \S+ by=run_contracts_s1:\d+ ')
        self.assertEqual(E.check_output(out, code, pins=self.pins), [], out[-3000:])
        p2b_gone(self, seen)

    def test_row59_per_case_message_forms(self):
        ids = self.doc['case_inventories']['run_fin_corpus_s1']['fin_corpus']['ids']
        c0 = ids[0]
        pins = self.doc['case_inventories']['run_fin_corpus_s1']
        wr = ('        import os, json, subprocess, sys, time\n'
              '        w = max(int(x) for x in os.listdir("/proc/self/fd") if int(x) > 2 and os.path.exists("/proc/self/fd/" + x))\n'
              '        def frame(b):\n            os.write(w, len(b).to_bytes(4, "big") + b)\n')
        for name, body, state, cause, code in (
                ('descendant_hang', '        subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"]); time.sleep(60)\n',
                 'INDETERMINATE', 'timeout', 3),
                ('incomplete', '        os.write(w, b"\\x00\\x00\\x01\\x00{\\"ok"); os._exit(0)\n', 'INDETERMINATE', 'crash', 3),
                ('malformed', '        frame(b"{]"); os._exit(0)\n', 'INDETERMINATE', 'bad_result', 3),
                ('ok_false', '        frame(json.dumps({"ok": False, "detail": "planted"}).encode()); os._exit(0)\n', 'FAIL', None, 1),
                ('child_error', '        frame(json.dumps({"child_error": "X"}).encode()); os._exit(0)\n', 'ITEM_ERROR', 'child_error', 2),
                ('kill_writing', '        os.write(w, b"\\x00\\x00\\x01\\x00{"); os.kill(os.getpid(), 9)\n', 'INDETERMINATE', 'crash', 3),
                ('wrong_keys', '        frame(json.dumps({"ok": True}).encode()); os._exit(0)\n', 'INDETERMINATE', 'bad_result', 3),
                ('wrong_types', '        frame(json.dumps({"ok": "yes", "detail": ""}).encode()); os._exit(0)\n', 'INDETERMINATE',
                 'bad_result', 3),
                ('looks_like_ok_false', '        frame(b"ok=false detail=planted"); os._exit(0)\n', 'INDETERMINATE', 'bad_result', 3),
                ('valid_then_hang', '        frame(json.dumps({"ok": True, "detail": ""}).encode()); os.close(w); time.sleep(60)\n',
                 'INDETERMINATE', 'processes_left', 3)):
            with self.subTest(form=name):
                old = "def run_case(cand, suite, cid):\n"
                root = p2b_copy(os.path.join(self.tmp, 'k2_' + name),
                                [('tools/run_fin_corpus_s1.py', old, old + '    if cid == %r:\n' % c0 + wr + body)])
                code_, out, seen = p2b_run(root, ['tools/run_fin_corpus_s1.py', '--only', ','.join(ids[:2])])
                p2_identity_record(self, seen, out)
                self.assertEqual(code_, code, out[-2000:])
                self.assertRegex(out, r'(?m)^CASE fin_corpus/%s %s cause=%s$' % (_p2re.escape(c0), state, cause or r'\S+'))
                self.assertRegex(out, r'(?m)^CASE fin_corpus/%s PASS cause=ok$' % _p2re.escape(ids[1]))
                self.assertEqual(E.check_output(out, code_, pins=pins), [], out[-3000:])
                p2b_gone(self, seen)
                shutil.rmtree(root, ignore_errors=True)

    def test_row60_the_hang_on_run_history_contract_s1_and_run_mkt_corpus_s1(self):
        hpins = self.doc['case_inventories']['run_history_contract_s1']
        s, inv = next(iter(hpins.items()))
        old = 'def batch(cand):\n'
        root = p2b_copy(os.path.join(self.tmp, 'hist'), [('tools/run_history_contract_s1.py', old,
                                                          old + '    import time\n    time.sleep(60)\n')])
        code, out, seen = p2b_run(root, ['tools/run_history_contract_s1.py', '--path', self.tmp, '--factory', 'am5cand:Store'])
        p2_identity_record(self, seen, out)
        self.assertEqual(E.check_output(out, code, pins=hpins), [], out[-3000:])
        p2b_gone(self, seen)
        mpins = self.doc['case_inventories']['run_mkt_corpus_s1']
        s, ids = next(iter(mpins.items()))
        ids = ids['ids']
        root = p2b_copy(os.path.join(self.tmp, 'mkt'), [('tools/run_mkt_corpus_s1.py', "'run_case': lambda cand, s, c: K.check_case(CASES[c])}",
                                                         "'run_case': lambda cand, s, c: __import__('time').sleep(60) if c == %r else "
                                                         "K.check_case(CASES[c])}" % ids[0])])
        code, out, seen = p2b_run(root, ['tools/run_mkt_corpus_s1.py', '--only', ','.join(ids[:2])])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertEqual(E.check_output(out, code, pins=mpins), [], out[-3000:])
        p2b_gone(self, seen)


AM5_CR02_STUB = r'''import os, subprocess, sys, time
# planted by tests_tools/test_runner_zero_work.py (amendment 5, rows 69 and 85): run in place of M10's run_cr02_reference.py in a copy
MODE, MARK = %(mode)r, %(mark)r
def show(r):
    print('FIELDS %%r %%r %%s %%r' %% (r.args[:1] == [sys.executable], r.returncode, type(r.stdout).__name__, r.stdout))
    print('MORE %%r %%s %%r' %% (r.args[1:3], type(r.stderr).__name__, r.stderr))     # fix 6, row 85: stderr and the rewritten command
if MODE == 'leak':
    show(subprocess.run([sys.executable, '-I', '-c', 'import subprocess, sys; subprocess.Popen([sys.executable, "-c", '
                         '"import time; time.sleep(30)"]); print("child ok")'], capture_output=True, text=True, timeout=60))
if MODE == 'interrupt':
    show(subprocess.run([sys.executable, '-I', '-c', 'import sys, time; open(sys.argv[1], "w").close(); time.sleep(60)',
                         os.path.join(MARK, 'first')], capture_output=True, text=True, timeout=120))
    show(subprocess.run([sys.executable, '-I', '-c', 'open(%%r, "w").close()' %% os.path.join(MARK, 'second_started')],
                        capture_output=True, timeout=120))
if MODE == 'normal':
    show(subprocess.run([sys.executable, '-I', '-c', 'print("child ok")'], capture_output=True, text=True, timeout=60))
print('CR-02 stub done')
sys.exit(0)
'''


class AM5CR02(unittest.TestCase):
    """Rows 69 (AM-3: CR-02 under P: a leak, and the cleanup on the SystemExit path) and 85 (AM2-2 (c): the synthetic
    CompletedProcess fields), with M10's script replaced by a stub in a copy (the successor's own M10 hash check pointed at it)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am5cr_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def tree(self, mode):
        root = p2b_copy(os.path.join(self.tmp, mode))
        mark = os.path.join(root, '_p2')
        os.makedirs(mark)
        stub = os.path.join(root, 'tools', 'am5_cr02_stub.py')
        with open(stub, 'w', encoding='utf-8') as fh:
            fh.write(AM5_CR02_STUB % {'mode': mode, 'mark': mark})
        import hashlib
        h = hashlib.sha256(open(stub, 'rb').read()).hexdigest()
        p = os.path.join(root, 'tools', 'run_cr02_reference_s1.py')
        src = open(p, encoding='utf-8').read()
        for old, new in (("os.path.join(ROOT, 'tools', 'run_cr02_reference.py')", "os.path.join(ROOT, 'tools', 'am5_cr02_stub.py')"),
                         ("M10_SHA256 = '59eecd583f8147dabb967fc7afdbb632cc0c520442456cb9d1631c1036ab55cb'", "M10_SHA256 = %r" % h)):
            self.assertEqual(src.count(old), 1, old)
            src = src.replace(old, new)
        open(p, 'w', encoding='utf-8').write(src)
        return root, mark

    def test_row69_a_leak_is_never_a_pass(self):
        root, mark = self.tree('leak')
        code, out, seen = p2b_run(root, ['tools/run_cr02_reference_s1.py'])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 2, out[-2000:])
        self.assertIn('FIELDS True 0 str ', out)
        self.assertRegex(out, r'(?m)^CLEANUP cr02:1 by=run_cr02_reference_s1:\d+ ')
        self.assertNotIn('CR-02 REFERENCE RERUN OK', out)
        p2b_gone(self, seen)

    def test_row69_the_systemexit_path_is_cleaned_up(self):
        root, mark = self.tree('normal')
        code, out, seen = p2b_run(root, ['tools/run_cr02_reference_s1.py'])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 0, out[-2000:])
        self.assertIn("FIELDS True 0 str 'child ok\\n'", out)
        self.assertRegex(out, r'(?m)^CLEANUP_SUMMARY units=1 leaked=0 remaining=0$')
        p2b_gone(self, seen)

    def test_row85_the_synthetic_completed_process_fields(self):
        # a child in flight at the signal is stopped under P.5 and reported as -15 with empty output of the asked type; a child not
        # yet started is not started, and reported the same way
        root, mark = self.tree('interrupt')
        code, out, seen = p2b_run(root, ['tools/run_cr02_reference_s1.py'], when=p2b_mark('first'), sig=_p2sig.SIGTERM)
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertIn("FIELDS True -15 str ''", out)
        self.assertIn("FIELDS True -15 bytes b''", out)
        # fix 6, row 85 (AM2-2 (c)): stderr empty of the same type, and args the command as rewritten (-S added after -I)
        self.assertIn("MORE ['-I', '-S'] str ''", out)
        self.assertIn("MORE ['-I', '-S'] bytes b''", out)
        self.assertFalse(os.path.exists(os.path.join(mark, 'second_started')))
        self.assertRegex(out.strip().splitlines()[-1], r'^INTERRUPTED signal=SIGTERM at=\S+ received=1$')
        p2b_gone(self, seen)


class AM5NoResultSupervisors(unittest.TestCase):
    """Rows 83 (AM2-2 (a): SIGNAL_AFTER_COMPLETION's place, M10's exit unchanged) and 66 (AM-2: F.2 in the leaves and in
    child_unittest_runner between tests; run_m8_tests_s1), in temporary copies."""

    setUp = P2NoResultSupervisors.setUp
    tearDown = P2NoResultSupervisors.tearDown
    copy = P2NoResultSupervisors.copy

    def test_row83_signal_after_completion_keeps_the_exit_and_its_place(self):
        hold = ('            fixed = CANCEL.fix(last=(k == last_step))\n',
                '            fixed = CANCEL.fix(last=(k == last_step))\n            if k == "R01":\n'
                '                open(os.path.join(root, "_p2_after_R01"), "w").close()\n                _time.sleep(3)\n')
        root = self.copy('plain', edits=[('tools/evkit.py',) + hold])
        code0, out0, seen0 = p2b_run(root, ['tools/run_regression_m8_s1.py', '--step', 'R01'])
        root = self.copy('after83', edits=[('tools/evkit.py',) + hold])
        code, out, seen = p2b_run(root, ['tools/run_regression_m8_s1.py', '--step', 'R01'],
                                  when=lambda t, d: os.path.exists(os.path.join(t, '_p2_after_R01')), sig=_p2sig.SIGTERM)
        p2_identity_record(self, seen, out)
        self.assertEqual(code, code0, out[-2000:])                    # M10's exit, unchanged by a signal after completion
        lines = [l for l in out.splitlines() if l.strip()]
        lines0 = [l for l in out0.splitlines() if l.strip()]
        self.assertEqual(lines[-1], lines0[-1])                       # the tool's own last line stays last
        k = lines.index('SIGNAL_AFTER_COMPLETION signal=SIGTERM')
        self.assertEqual(k, len(lines) - 2)                           # immediately before it, after the CLEANUP lines
        self.assertTrue(any(l.startswith('CLEANUP_SUMMARY ') for l in lines[:k]))
        self.assertNotRegex(out, r'(?m)^INTERRUPTED ')
        p2b_gone(self, seen)

    LEAF_TESTS = ('import os, time, unittest\n'
                  'D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_p2")\n\n\n'
                  'class T(unittest.TestCase):\n'
                  '    def test_a(self):\n        open(os.path.join(D, "in_test"), "w").close()\n        time.sleep(6)\n\n'
                  '    def test_b(self):\n        open(os.path.join(D, "b_started"), "w").close()\n')

    def leaf_tree(self, name):
        root = self.copy(name)
        os.makedirs(os.path.join(root, '_p2'), exist_ok=True)
        with open(os.path.join(root, 'tests_m8', 'test_m8_dependency.py'), 'w', encoding='utf-8') as fh:
            fh.write(self.LEAF_TESTS)
        p = _p2sp.run([sys.executable, '-I', '-S', '-c', 'import sys; sys.path.insert(0, "."); import tools.evkit as E; '
                       'E.update_pins("am5 row 66 (test copy)", "am5", files=["tests_m8/test_m8_dependency.py"])'],
                      cwd=root, capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return root

    def test_row66_child_unittest_runner_stops_between_tests(self):
        root = self.leaf_tree('leaf66')
        code, out, seen = p2b_run(root, ['tools/child_unittest_runner.py', '--caller', 'run_m8_tests_s1', '--mode', 'full',
                                         'tests_m8.test_m8_dependency'], when=lambda t, d: os.path.exists(os.path.join(t, '_p2', 'in_test')))
        self.assertTrue(os.path.exists(os.path.join(root, '_p2', 'in_test')))
        self.assertFalse(os.path.exists(os.path.join(root, '_p2', 'b_started')), 'a test started after the signal')
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out.strip().splitlines()[-1], r'^RESULT v=2 kind=tests ')
        self.assertRegex(out, r'(?m)^INTERRUPTED signal=SIGINT at=\S+ received=1$')
        pins = E.test_file_pins(E.load_pins(os.path.join(root, 'tools', 'expected_counts.json'))[0], ['tests_m8/test_m8_dependency.py'])
        self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])
        p2b_gone(self, seen)

    def test_row66_run_m8_tests_s1_stops_between_tests(self):
        root = self.leaf_tree('m8_66')
        code, out, seen = p2b_run(root, ['tools/run_m8_tests_s1.py', '--file', 'test_m8_dependency.py'],
                                  when=lambda t, d: os.path.exists(os.path.join(t, '_p2', 'in_test')))
        p2_identity_record(self, seen, out)
        self.assertFalse(os.path.exists(os.path.join(root, '_p2', 'b_started')), 'a test started after the signal')
        self.assertEqual(code, 3, out[-2000:])
        pins = E.test_file_pins(E.load_pins(os.path.join(root, 'tools', 'expected_counts.json'))[0], ['tests_m8/test_m8_dependency.py'])
        self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])
        p2b_gone(self, seen)


# ---------------------------------------------------------------------------------------------------------------------------------------
# Fix 6 (owner, 2026-11-13 18:34, "Fix them, then re-run"): the gaps the step 6 re-mapping found (rows 21, 30, 52, 53, 71 and 73,
# discrepancy D6-3). Tests only, in temporary copies; no product or successor-tool logic is changed.
# ---------------------------------------------------------------------------------------------------------------------------------------
AM6_AUIF_LEAK = {     # AUIF's own code starts a child that is left running: in ensure() (the run's start) or in reverify() (its end)
    'ensure': ('    info = verify_tree(root)\n    if root not in sys.path:\n',
               "    subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n    info = verify_tree(root)\n"
               "    if root not in sys.path:\n"),
    'reverify': ('    return verify_tree(root)\n',
                 "    subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n    return verify_tree(root)\n")}


def am6_mt():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import test_mutation_timeout as MT
    return MT


def am6_m8_copy(dest, where):
    """A copy whose AUIF code leaves a child at `where`, with m8_mutants_s1's test command stubbed (every tier passes)."""
    root = p2b_copy(dest, [('apg_auif/dependency.py',) + AM6_AUIF_LEAK[where]])
    MT = am6_mt()
    ok, failed, evidence = MT._stub_text('ok')[0], MT._stub_text('failed')[0], MT._stub_text('evidence')[0]
    with open(os.path.join(root, 'tools', 'child_unittest_runner.py'), 'w', encoding='utf-8') as fh:
        fh.write(MT.STUB % {'mode': 'ok', 'ok': ok, 'failed': failed, 'evidence': evidence, 'sleep': 60})
    return root


class AM6AttributionAndSignals(unittest.TestCase):
    """Fix 6: row 71 (AM-5 (a): m8_mutants_s1's own AUIF children registered), row 73 (AM-5 (c): run_m8_tests_s1's start and end,
    R03's "(INCOMPLETE: processes left)"), row 30 (an unkillable forked case), rows 52 and 53 (F.2 at the remaining points) and row 21
    (gone at the RESULT line) at tool level."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am6z_')
        self.doc, _ = E.load_pins()
        self.unkill = []

    def tearDown(self):
        for f in self.unkill:
            try:
                os.kill(f, 9)
            except OSError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_row71_m8_mutants_s1s_own_auif_children_are_registered_at_its_start(self):
        # the child AUIF's ensure() itself starts (not one planted after it) is registered under run_start: left running, the run is
        # refused (RUN_ERROR PROCESSES_LEFT run_start, every mutant NOT_RUN, exit 2), and the run_start record names it
        first = self.doc['mutation_lists']['m8_mutants_s1']['ids'][0]
        root = am6_m8_copy(os.path.join(self.tmp, 'm8_ensure'), 'ensure')
        code, out, seen = p2b_run(root, ['tools/m8_mutants_s1.py', '--ids', first])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 2, out[-3000:])
        self.assertRegex(out, r'(?m)^RUN_ERROR PROCESSES_LEFT run_start$')
        self.assertEqual([l for l in out.splitlines() if l.startswith('MUTANT ')], ['MUTANT %s NOT_RUN cause=run_error' % first])
        self.assertRegex(out, r'(?m)^CLEANUP run_start by=m8_mutants_s1:\d+ .* left=\d+:\d+')
        self.assertEqual(E.check_output(out, code), [], out[-3000:])
        p2b_gone(self, seen)

    def test_row73_run_m8_tests_s1s_start_and_end(self):
        # AM-5 (c): its AUIF verification (run_start) and reverification (run_end), each leaving a child: PROCESSES_LEFT run_start
        # (no file runs) and PROCESSES_LEFT run_end (the file's result kept), each with its CLEANUP record
        for where, phase in (('ensure', 'run_start'), ('reverify', 'run_end')):
            with self.subTest(phase=phase):
                root = p2b_copy(os.path.join(self.tmp, 'm8t_' + where), [('apg_auif/dependency.py',) + AM6_AUIF_LEAK[where]])
                code, out, seen = p2b_run(root, ['tools/run_m8_tests_s1.py', '--file', 'test_m8_dependency.py'])
                p2_identity_record(self, seen, out)
                self.assertEqual(code, 2, out[-3000:])
                self.assertRegex(out, r'(?m)^RUN_ERROR PROCESSES_LEFT %s$' % phase)
                self.assertRegex(out, r'(?m)^CLEANUP %s by=run_m8_tests_s1:\d+ .* left=\d+:\d+' % phase)
                if phase == 'run_start':
                    self.assertNotRegex(out, r'(?m)^CHILD test_m8_dependency\.py ')
                else:      # the file ran and its result is kept (the planted AUIF edit also reaches the child's own verification)
                    self.assertRegex(out, r'(?m)^CHILD test_m8_dependency\.py CHILD_\S+ ')
                    self.assertRegex(out, r'(?m)^FILE test_m8_dependency\.py state=')
                self.assertEqual(E.check_output(out, code), [], out[-3000:])
                p2b_gone(self, seen)

    def test_row73_an_m10_steps_child_that_leaves_a_process(self):
        # AM-5 (c) / AM2-2: a child of an M10 regression step (R03's make_m8_registers.py) leaves a process: the step reads
        # "(INCOMPLETE: processes left)", and the step's CLEANUP record names the process
        root = P2NoResultSupervisors.copy(self, 'r03_leak', prepend=[(
            'tools/make_m8_registers.py',
            "import subprocess as _am6s, sys as _am6y\n_am6s.Popen([_am6y.executable, '-c', 'import time; time.sleep(30)'])\n")])
        code, out, seen = p2b_run(root, ['tools/run_regression_m8_s1.py', '--step', 'R03'])
        p2_identity_record(self, seen, out)
        self.assertRegex(out, r'(?m)^FAIL R03 .*\(INCOMPLETE: processes left\)', out[-3000:])
        self.assertRegex(out, r'(?m)^CLEANUP \S*R03\S* .* left=\d+:\d+')
        self.assertNotRegex(out, r'(?m)^INTERRUPTED ')
        p2b_gone(self, seen)

    def test_row30_a_forked_case_that_cannot_be_killed_after_its_valid_result(self):
        # P.10: the case unit's child writes a valid result, ignores SIGTERM and (simulated) cannot be killed: the case is INDETERMINATE
        # processes_left, the run RUN_ERROR CLEANUP_INCOMPLETE with exit 2, its record deadline=kill_verify and remaining= the process
        ids = self.doc['case_inventories']['run_fin_corpus_s1']['fin_corpus']['ids']
        root = os.path.join(self.tmp, 'fin_unkill')
        old = "def run_case(cand, suite, cid):\n"
        body = ('    if cid == %r:\n        import os, signal, json, time\n        signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                '        open(os.path.join(%r, "_p2", "unkillable"), "a").write("%%d\\n" %% os.getpid())\n'
                '        _n = os.open(os.devnull, os.O_WRONLY)\n        os.dup2(_n, 1)\n        os.dup2(_n, 2)\n'
                '        w = max(int(x) for x in os.listdir("/proc/self/fd") if int(x) > 2 and os.path.exists("/proc/self/fd/" + x))\n'
                '        data = json.dumps({"ok": True, "detail": ""}).encode()\n'
                '        os.write(w, len(data).to_bytes(4, "big") + data)\n        os.close(w)\n        while True:\n'
                '            time.sleep(1)\n' % (ids[0], root))
        unk = ('        _pidfd_send_signal(fd, sig)\n        return True\n',
               '        if sig == _signal.SIGKILL and _am6_unkillable(pid):\n            return False\n'
               '        _pidfd_send_signal(fd, sig)\n        return True\n')
        p2b_copy(root, [('tools/run_fin_corpus_s1.py', old, old + body), ('tools/evkit.py',) + unk])
        os.makedirs(os.path.join(root, '_p2'))
        with open(os.path.join(root, 'tools', 'evkit.py'), 'a', encoding='utf-8') as fh:
            fh.write('\n\ndef _am6_unkillable(pid):\n    f = os.path.join(%r, "_p2", "unkillable")\n'
                     '    return os.path.exists(f) and str(pid) in open(f).read().split()\n' % root)
        code, out, seen = p2b_run(root, ['tools/run_fin_corpus_s1.py', '--only', ids[0]])
        p2_identity_record(self, seen, out)
        self.unkill = [int(x) for x in open(os.path.join(root, '_p2', 'unkillable')).read().split()]
        alive = [q for q in self.unkill if E.proc_stat(q) is not None and E.proc_stat(q)[0] != 'Z']
        self.assertEqual(len(alive), 1)
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^CASE fin_corpus/%s INDETERMINATE cause=processes_left$' % _p2re.escape(ids[0]))
        self.assertRegex(out, r'(?m)^RUN_ERROR CLEANUP_INCOMPLETE fin_corpus/%s %d:\d+$' % (_p2re.escape(ids[0]), alive[0]))
        self.assertRegex(out, r'(?m)^CLEANUP fin_corpus/%s .* deadline=kill_verify .* remaining=%d:\d+$' % (_p2re.escape(ids[0]), alive[0]))
        self.assertRegex(out, r'(?m)^CLEANUP_SUMMARY units=\d+ leaked=1 remaining=1$')
        self.assertEqual(E.check_output(out, code, pins=self.doc['case_inventories']['run_fin_corpus_s1']), [], out[-3000:])

    def test_rows52_53_run_contracts_s1_sigterm_and_both_signals_during_the_batchs_cleanup(self):
        P = P2CaseRunners()
        P.tmp, P.doc = self.tmp, self.doc
        pins = self.doc['case_inventories']['run_contracts_s1']
        root = P.batch_tree('batch:hang')
        code, out, seen = p2b_run(root, ['tools/run_contracts_s1.py'], when=p2b_mark('started'), sig=_p2sig.SIGTERM)
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertEqual(len(_p2re.findall(r'(?m)^CASE \S+ INDETERMINATE cause=interrupted$', out)), 38, out[-2000:])
        self.assertTrue(out.strip().splitlines()[-2].startswith('INTERRUPTED signal=SIGTERM at=audit_log/'))
        self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])
        p2b_gone(self, seen)
        for sig in (_p2sig.SIGINT, _p2sig.SIGTERM):
            with self.subTest(sig=sig.name):
                shutil.rmtree(root, ignore_errors=True)
                root = P.batch_tree('batch:leak_ignoring')
                code, out, seen = p2b_run(root, ['tools/run_contracts_s1.py'], when=p2b_mark('leaked'), delay=0.5, sig=sig)
                p2_identity_record(self, seen, out)
                self.assertEqual(code, 3, out[-2000:])
                self.assertRegex(out, r'(?m)^CLEANUP run_contracts_s1:batch by=run_contracts_s1:\d+ ')
                self.assertTrue(_p2re.search(r'(?m)^(INTERRUPTED signal=%s |SIGNAL_AFTER_COMPLETION signal=%s$)' % (sig.name, sig.name), out),
                                out[-2000:])
                self.assertEqual(E.check_output(out, code, pins=pins), [], out[-3000:])
                p2b_gone(self, seen)

    def test_rows52_53_sabotage_m7_s1_between_items_on_either_signal(self):
        MT = am6_mt()
        ids = self.doc['plant_lists']['sabotage_m7_s1']['ids'][:2]
        hold = ('        def begin(mid):\n            with flock:\n',
                '        def begin(mid):\n            if begun[0] == 1:\n                open(os.path.join(root, "_p2mark", "between"), "w")'
                '.close()\n                _time.sleep(3)\n            with flock:\n')
        for sig in (_p2sig.SIGINT, _p2sig.SIGTERM):
            with self.subTest(sig=sig.name):
                tree = os.path.join(self.tmp, 'm7_between_' + sig.name)
                MT.sabotage_tree(tree, 'm7', 'failed')
                os.makedirs(os.path.join(tree, '_p2mark'), exist_ok=True)
                MT.p2_patch_evkit(tree, [hold])
                code, out, seen = p2b_run(tree, ['tools/sabotage_m7_s1.py', '--ids', ','.join(ids), '--jobs', '1'],
                                          when=lambda t, d: os.path.exists(os.path.join(t, '_p2mark', 'between')), sig=sig)
                p2_identity_record(self, seen, out)
                self.assertEqual(code, 3, out[-2000:])
                self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=%s at=between received=1' % sig.name)
                self.assertRegex(out, r'(?m)^PLANT %s (CAUGHT|MISSED) ' % _p2re.escape(ids[0]))         # fixed before the signal
                self.assertRegex(out, r'(?m)^PLANT %s NOT_RUN cause=run_stopped$' % _p2re.escape(ids[1]))
                self.assertEqual(E.check_output(out, code, selected=ids), [], out[-3000:])
                p2b_gone(self, seen)
                shutil.rmtree(tree, ignore_errors=True)

    def faults_tree(self, mode, hold=False):
        F = P2FaultRunners()
        F.tmp = self.tmp
        root = F.tree(mode)
        if hold:      # between items: after the first plant's outcome, the loop holds before the second plant starts
            p = os.path.join(root, 'tools', 'evkit.py')
            src = open(p, encoding='utf-8').read()
            old = '        for n, pid in enumerate(sel):\n            if CANCEL.set:\n                break\n'
            self.assertEqual(src.count(old), 1)
            open(p, 'w', encoding='utf-8').write(src.replace(old, (
                '        for n, pid in enumerate(sel):\n            if n == 1:\n                open(os.path.join(%r, "_p2", "between"), "w").close()\n'
                '                _time.sleep(3)\n            if CANCEL.set:\n                break\n') % root))
        return root

    def test_rows52_53_run_faults_s1_between_items_and_during_the_end_controls_cleanup(self):
        ids = self.doc['plant_lists']['run_faults_s1']['ids'][:2]
        for sig in (_p2sig.SIGINT, _p2sig.SIGTERM):
            with self.subTest(point='between', sig=sig.name):
                root = self.faults_tree('none:x', hold=True)
                code, out, seen = p2b_run(root, ['tools/run_faults_s1.py', '--ids', ','.join(ids)], when=p2b_mark('between'), sig=sig)
                p2_identity_record(self, seen, out)
                self.assertEqual(code, 3, out[-2000:])
                self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=%s at=between received=1' % sig.name)
                self.assertRegex(out, r'(?m)^PLANT %s (CAUGHT|MISSED) ' % _p2re.escape(ids[0]))
                self.assertRegex(out, r'(?m)^PLANT %s NOT_RUN cause=run_stopped$' % _p2re.escape(ids[1]))
                self.assertEqual(E.check_output(out, code, selected=ids), [], out[-3000:])
                p2b_gone(self, seen)
                shutil.rmtree(root, ignore_errors=True)
            with self.subTest(point='end_control_cleanup', sig=sig.name):
                # K.1: the end control returned a valid result and left a process; the signal comes during its cleanup: the control's
                # outcome is fixed (CONTROL_FAIL processes_left) and the signal is SIGNAL_AFTER_COMPLETION, never INTERRUPTED
                root = self.faults_tree('control_end:leak_ignoring')
                code, out, seen = p2b_run(root, ['tools/run_faults_s1.py', '--ids', ids[0]], when=p2b_mark('leaked'), delay=0.5, sig=sig)
                p2_identity_record(self, seen, out)
                self.assertRegex(out, r'(?m)^CONTROL end CONTROL_FAIL cause=processes_left ', out[-2000:])
                self.assertRegex(out, r'(?m)^SIGNAL_AFTER_COMPLETION signal=%s$' % sig.name)
                self.assertNotRegex(out, r'(?m)^INTERRUPTED ')
                self.assertIn(' control_end=FAIL ', out.strip().splitlines()[-1])
                self.assertEqual(E.check_output(out, code, selected=[ids[0]]), [], out[-3000:])
                p2b_gone(self, seen)
                shutil.rmtree(root, ignore_errors=True)

    def test_row21_a_fault_runners_descendants_are_gone_when_its_result_line_is_printed(self):
        # P.5 step 9 (discrepancy 12) at tool level on a fault runner: a plant leaves a process; checked when the RESULT line arrives
        MT = am6_mt()
        root = self.faults_tree('plant:leak_ignoring')
        pid0 = self.doc['plant_lists']['run_faults_s1']['ids'][0]
        code, out, seen, at_result = MT.p2_run_result_check(root, 'run_faults_s1.py', ['--ids', pid0])
        P2B_PGIDS.update(MT.P2_PGIDS)
        p2_identity_record(self, seen, out)
        self.assertEqual(len(at_result), 1, out[-3000:])
        self.assertEqual(at_result[0], [])
        self.assertRegex(out, r'(?m)^CLEANUP %s .* killed=\d+:\d+' % _p2re.escape(pid0))
        self.assertTrue(seen)
        self.assertEqual(E.check_output(out, code, selected=[pid0]), [], out[-3000:])


AM6_ALLOW = {'PATH', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR', 'PYTHONDONTWRITEBYTECODE'}


def am6_probe_py(path, cls, quit_if=None):
    """A probe prepended to a script in a copy: it records what this process received (argv, -I/-S/-B flags, environment names, never
    values) as one JSON line, then lets the script run (or exits 1 when the environment variable quit_if is set, to keep a run short)."""
    return ('import json as _pj, os as _po, sys as _ps\nopen(%r, "a").write(_pj.dumps({"class": %d, "argv": _ps.argv[:1], '
            '"flags": [_ps.flags.isolated, _ps.flags.no_site, _ps.flags.dont_write_bytecode], "env": sorted(_po.environ)}) + "\\n")\n'
            % (path, cls)) + ('if %r in _po.environ:\n    _ps.exit(1)\n' % quit_if if quit_if else '')


class AM6FindingThirteenProbes(unittest.TestCase):
    """Fix 6, row 75 (AM-5 (e), amendment 1: "the new evidence asserts what each class actually receives, by a probe in each path"):
    classes 2 to 6 of open finding 13 (class 1 is AM5Supervision.test_row72...). Each probe's record is written to the test log as
    P_PROBE lines (the T-set evidence) and asserted against finding 13's own description of that class."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am6p_')
        self.doc, _ = E.load_pins()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def records(self, path, cls):
        recs = [_json.loads(l) for l in open(path)] if os.path.exists(path) else []
        sys.stderr.write(''.join('P_PROBE test=%s %s\n' % (self.id(), _json.dumps(r, sort_keys=True)) for r in recs))
        self.assertTrue(recs, 'the class %d probe recorded nothing' % cls)
        return recs

    def test_row75_class2_the_r03_register_generators(self):
        # -I -B, no time limit; the environment is the allowlist (the successor replaces os.environ first)
        probe = os.path.join(self.tmp, 'c2.jsonl')
        root = P2NoResultSupervisors.copy(self, 'c2', prepend=[('tools/make_m8_registers.py', am6_probe_py(probe, 2))])
        code, out, seen = p2b_run(root, ['tools/run_regression_m8_s1.py', '--step', 'R03'])
        p2_identity_record(self, seen, out)
        for r in self.records(probe, 2):
            self.assertEqual(r['flags'][0], 1)                 # -I
            self.assertEqual(r['flags'][2], 1)                 # -B
            self.assertLessEqual(set(r['env']), AM6_ALLOW, r['env'])
        p2b_gone(self, seen)

    def test_row75_class3_cr02s_grandchildren(self):
        # cr02_materiality_mutants.py:114: -I without -S, 300 s; the environment its parent was given plus CR02_MODEL_PATH
        probe = os.path.join(self.tmp, 'c3.jsonl')
        root = P2NoResultSupervisors.copy(self, 'c3', prepend=[('reference/cr02/cr02_materiality_tests.py',
                                                                 am6_probe_py(probe, 3, quit_if='CR02_MODEL_PATH'))])
        code, out, seen = p2b_run(root, ['tools/run_cr02_reference_s1.py'])
        p2_identity_record(self, seen, out)
        recs = self.records(probe, 3)
        grand = [r for r in recs if 'CR02_MODEL_PATH' in r['env']]
        self.assertTrue(grand, recs)
        for r in grand:
            self.assertEqual(r['flags'][:2], [1, 0])           # -I, no -S
            self.assertLessEqual(set(r['env']) - {'CR02_MODEL_PATH'}, AM6_ALLOW, r['env'])
        p2b_gone(self, seen)

    def test_row75_class4_the_grandchildren_of_an_m10_tool_run_as_a_child(self):
        # sabotage_m7_s1's check runs M10's run_regression_m7.py --step R07 as a child; its own child, make_m7_registers.py, is started
        # by plain subprocess.run with -I and no -S, with the allowlist environment the M10 tool was given
        MT = am6_mt()
        probe = os.path.join(self.tmp, 'c4.jsonl')
        tree = os.path.join(self.tmp, 'c4')
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        p = os.path.join(tree, 'tools', 'make_m7_registers.py')
        src = open(p, encoding='utf-8').read()
        open(p, 'w', encoding='utf-8').write(am6_probe_py(probe, 4) + src)
        MT.p2_patch_evkit(tree)
        code, out, seen = p2b_run(tree, ['tools/sabotage_m7_s1.py', '--ids', 'S15'])
        p2_identity_record(self, seen, out)
        for r in self.records(probe, 4):
            self.assertEqual(r['flags'][:2], [1, 0])           # -I, no -S
            self.assertLessEqual(set(r['env']), AM6_ALLOW, r['env'])
        p2b_gone(self, seen)

    def test_row75_class5_a_process_a_test_file_starts(self):
        # a test file run in-process starts a child with plain subprocess.run (no -I, no -S, no time limit of its own here): it gets the
        # environment the test runner was given, the allowlist
        probe = os.path.join(self.tmp, 'c5.jsonl')
        root = p2b_copy(os.path.join(self.tmp, 'c5'))
        rel = sorted(k for k in self.doc['test_files'] if k.startswith('tests/'))[0]
        with open(os.path.join(root, rel), 'w', encoding='utf-8') as fh:
            fh.write('import subprocess, sys, unittest\n\n\nclass T(unittest.TestCase):\n    def test_a(self):\n'
                     '        subprocess.run([sys.executable, "-c", %r], timeout=60)\n' % am6_probe_py(probe, 5))
        q = _p2sp.run([sys.executable, '-I', '-S', '-c', 'import sys; sys.path.insert(0, "."); import tools.evkit as E; '
                       'E.update_pins("fix 6 row 75 (test copy)", "fix6", files=[%r])' % rel], cwd=root, capture_output=True, text=True,
                      timeout=600)
        self.assertEqual(q.returncode, 0, q.stdout + q.stderr)
        code, out, seen = p2b_run(root, ['tools/run_test_files_s1.py', os.path.basename(rel)])
        p2_identity_record(self, seen, out)
        for r in self.records(probe, 5):
            self.assertEqual(r['flags'][:2], [0, 0])           # plain: neither -I nor -S
            self.assertLessEqual(set(r['env']), AM6_ALLOW, r['env'])
        p2b_gone(self, seen)

    def test_row75_class6_sabotage_m10s_ui_check_a_node_child_and_its_grandchild(self):
        # a Node child (-I and -S do not apply) whose test starts a grandchild (a browser, here a second node process standing for it)
        probe = os.path.join(self.tmp, 'c6.jsonl')
        js = ('const fs = require("fs"), cp = require("child_process");\nconst F = %s;\n'
              'fs.appendFileSync(F, JSON.stringify({class: 6, who: "node", execArgv: process.execArgv, '
              'env: Object.keys(process.env).sort()}) + "\\n");\n'
              'cp.spawnSync(process.execPath, ["-e", "require(\\"fs\\").appendFileSync(" + JSON.stringify(F) + ", JSON.stringify({class: 6, '
              'who: \\"grandchild\\", env: Object.keys(process.env).sort()}) + \\"\\\\n\\")"], {timeout: 60000});\nprocess.exit(1);\n'
              % _json.dumps(probe))
        root = p2b_copy(os.path.join(self.tmp, 'c6'))
        with open(os.path.join(root, 'ui_tests', 'run_ui_tests.js'), 'w', encoding='utf-8') as fh:
            fh.write(js)
        code, out, seen = p2b_run(root, ['tools/sabotage_m10_s1.py', '--ids', 'U01'])
        p2_identity_record(self, seen, out)
        recs = self.records(probe, 6)
        self.assertEqual({r['who'] for r in recs}, {'node', 'grandchild'})
        for r in recs:
            self.assertLessEqual(set(r['env']), AM6_ALLOW, r['env'])
        self.assertEqual(E.check_output(out, code, selected=['U01']), [], out[-3000:])
        p2b_gone(self, seen)


class AM6RunEndAndCounts(unittest.TestCase):
    """Fix 6: row 96 (reading 9) and row 99 (reading 13) at tool level, on run_faults_s1 in a copy."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am6e_')
        self.doc, _ = E.load_pins()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_row96_a_child_outside_every_unit_and_phase_is_the_run_ends_at_tool_level(self):
        # reading 9: the tool itself starts a child outside every unit and phase and leaves it running: it is attributed to run_end,
        # and the run's close is RUN_ERROR PROCESSES_LEFT run_end (exit 2), with the run_end CLEANUP record
        pid0 = self.doc['plant_lists']['run_faults_s1']['ids'][0]
        old = "        set_phase('control_start')\n        try:\n            cs, cl = control_run('start')\n"
        new = ("        _subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])     # fix 6 test plant: unowned\n" + old)
        root = p2b_copy(os.path.join(self.tmp, 'r96'), [('tools/evkit.py', old, new)])
        code, out, seen = p2b_run(root, ['tools/run_faults_s1.py', '--ids', pid0])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 2, out[-3000:])
        self.assertRegex(out, r'(?m)^RUN_ERROR PROCESSES_LEFT run_end$')
        self.assertRegex(out, r'(?m)^CLEANUP run_end by=run_faults_s1:\d+ .* left=\d+:\d+')
        self.assertRegex(out, r'(?m)^PLANT %s CAUGHT ' % _p2re.escape(pid0))           # the plant's own outcome is kept
        self.assertEqual(E.check_output(out, code, selected=[pid0]), [], out[-3000:])
        p2b_gone(self, seen)

    def test_row99_a_real_runs_units_count_reconciled(self):
        # reading 13 on a real run: run_faults_s1 with two plants starts four units (the start control, two plants, the end control)
        ids = self.doc['plant_lists']['run_faults_s1']['ids'][:2]
        root = p2b_copy(os.path.join(self.tmp, 'r99'))
        code, out, seen = p2b_run(root, ['tools/run_faults_s1.py', '--ids', ','.join(ids)])
        p2_identity_record(self, seen, out)
        self.assertEqual(code, 0, out[-3000:])
        units = 2 + len([l for l in out.splitlines() if l.startswith('CONTROL ')])
        self.assertEqual(units, 4, out[-3000:])
        self.assertIn('CLEANUP_SUMMARY units=%d leaked=0 remaining=0' % units, out)
        self.assertEqual(E.check_output(out, code, selected=ids), [], out[-3000:])


if __name__ == '__main__':
    unittest.main()
