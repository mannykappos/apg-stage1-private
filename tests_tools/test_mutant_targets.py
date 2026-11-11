"""Stage 1 (APG-M11-S1), Workstream T, E1-RI10 and T-0: the mutation preflight (R1_REQUIREMENTS.md §2.1): every mutant's target text
occurs exactly once (or exactly its declared count) before any mutant runs; anything else is PREFLIGHT_INVALID_TARGET, a tool-definition
error, and the run stops before any mutant executes.
Run from the package root:  python3 -I -S tests_tools/test_mutant_targets.py      BUILDER-EXECUTED: NOT INDEPENDENT."""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402


def load_m10_tool(name):
    """Load an M10 mutation tool (byte-identical in the successor, DP-1.2 (B)) by file path, for its mutant definitions only; its
    main() is guarded and is not run."""
    spec = importlib.util.spec_from_file_location('m10_' + name, os.path.join(ROOT, 'tools', name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Preflight(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='s1_pre_')
        with open(os.path.join(self.dir, 'm.py'), 'w') as f:
            f.write('a = 1\nb = 2\nb = 2\n')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_exactly_once_passes(self):
        errs, human = E.preflight_text([('X1', 'm.py', 'a = 1', 'a = 0', None)], self.dir)
        self.assertEqual((errs, human), ([], []))

    def test_zero_occurrences_fails(self):
        errs, human = E.preflight_text([('X1', 'm.py', 'c = 3', 'c = 0', None)], self.dir)
        self.assertEqual([e.line() for e in errs], ['RUN_ERROR PREFLIGHT_INVALID_TARGET X1:occurrences=0,expected=1'])
        self.assertEqual(human, ['PREFLIGHT FAILED X1: occurrences=0 expected=1 in m.py'])

    def test_more_than_once_fails_unless_declared(self):
        errs, _ = E.preflight_text([('X2', 'm.py', 'b = 2', 'b = 0', None)], self.dir)
        self.assertEqual(errs[0].code, 'PREFLIGHT_INVALID_TARGET')
        self.assertEqual(E.preflight_text([('X2', 'm.py', 'b = 2', 'b = 0', 2)], self.dir)[0], [])
        self.assertEqual(E.preflight_text([('X2', 'm.py', 'b = 2', 'b = 0', 'all')], self.dir)[0], [])
        self.assertEqual(E.preflight_text([('X2', 'm.py', 'b = 2', 'b = 0', 3)], self.dir)[0][0].code, 'PREFLIGHT_INVALID_TARGET')

    def test_missing_file_fails(self):
        errs, _ = E.preflight_text([('X3', 'nope.py', 'a', 'b', None)], self.dir)
        self.assertEqual(errs[0].line(), 'RUN_ERROR PREFLIGHT_INVALID_TARGET X3:file_missing')

    def test_a_preflight_failure_stops_every_mutant(self):
        sel = ['X1', 'X3']
        errs, _ = E.preflight_text([('X1', 'm.py', 'a = 1', 'a = 0', None), ('X3', 'nope.py', 'a', 'b', None)], self.dir)
        lines, code = E.finish_items('mutation', 't', 'r', sel, {}, run_errors=errs, preflight='FAIL', control_start='NOT_RUN',
                                     not_run_cause='preflight_failed')
        self.assertEqual(code, 2)
        self.assertEqual([l for l in lines if l.startswith('MUTANT')],
                         ['MUTANT X1 NOT_RUN cause=preflight_failed', 'MUTANT X3 NOT_RUN cause=preflight_failed'])


class TheRI10CaseOnTheRealMutantList(unittest.TestCase):
    """E1-RI10: the M10 M2 mutant list holds RI10, whose target text is absent from the released apg/reference_impl.py.  M10's tool
    reports it per mutant as an ERROR mid-run (m2_mutants.py:232-233), after other mutants have started; the successor preflight finds
    it before any mutant runs."""

    def setUp(self):
        self.m2 = load_m10_tool('m2_mutants')
        self.muts = [(mid, os.path.join('apg', f), old, new, None) for mid, f, old, new in self.m2.MUT]

    def test_successor_preflight_finds_exactly_ri10_before_any_mutant(self):
        errs, human = E.preflight_text(self.muts, ROOT)
        self.assertEqual([e.detail.split(':')[0] for e in errs], ['RI10-query-crosses-tenants'])
        self.assertEqual(errs[0].line(), 'RUN_ERROR PREFLIGHT_INVALID_TARGET RI10-query-crosses-tenants:occurrences=0,expected=1')

    def test_m10_tool_only_finds_it_per_mutant(self):
        # on M10 the check is inside run_one, which a worker reaches only after the run has started (m2_mutants.py:229-233)
        item = [m for m in self.m2.MUT if m[0] == 'RI10-query-crosses-tenants'][0]
        mid, st, info = self.m2.run_one(item, tempfile.gettempdir())
        self.assertEqual((mid, st), ('RI10-query-crosses-tenants', 'ERROR'))
        self.assertIn('pattern not found', info)
        # and M10's own check is "at least once", not "exactly once": a target present twice passes there
        self.assertIn('if src.count(old) < 1:', open(os.path.join(ROOT, 'tools', 'm2_mutants.py')).read())



def literal_list(path, name):
    """A list assigned at module level, read with ast.literal_eval from the source, without importing the tool."""
    import ast
    with open(path, encoding='utf-8') as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError('%s not found in %s' % (name, path))


# The plants of the earlier releases' sabotage tools whose target text is not exactly once in this tree (stage 1 report finding F2): M10's
# tools apply str.replace to them without checking (a plant that changes nothing, or only the first of several places); the successor's
# preflight refuses each of them, so a run that selects one stops before any plant (EVIDENCE_ERROR, exit 2).  Pinned here so that any
# change to the set is seen.
NOT_EXACTLY_ONCE = {
    'sabotage_f67': ['S07:occurrences=0,expected=1', 'S12:occurrences=0,expected=1', 'S20:occurrences=15,expected=1',
                     'S23:occurrences=24,expected=1', 'S24:occurrences=8,expected=1'],
    'sabotage_f671': ['S01:occurrences=0,expected=1', 'S02:occurrences=0,expected=1', 'S03:occurrences=0,expected=1',
                      'S09:occurrences=0,expected=1', 'S11:occurrences=0,expected=1', 'S13:occurrences=0,expected=1',
                      'S18:occurrences=3,expected=1', 'S22:occurrences=8,expected=1', 'S23:occurrences=0,expected=1'],
    'sabotage_f672': ['S04:occurrences=0,expected=1', 'S08:occurrences=0,expected=1', 'S14:occurrences=5,expected=1',
                      'S15:occurrences=11,expected=1', 'S19:occurrences=12,expected=1'],
    'sabotage_f673': ['S01:occurrences=0,expected=1', 'S02:occurrences=0,expected=1', 'S13:occurrences=2,expected=1',
                      'S16:occurrences=5,expected=1', 'S20:occurrences=13,expected=1'],
    'sabotage_f674': ['S09:occurrences=5,expected=1', 'S13:occurrences=15,expected=1'],
    'sabotage_m7': ['S07:occurrences=117,expected=1'],
    'sabotage_m71': ['S07:occurrences=117,expected=1', 'S16:occurrences=2,expected=1'],
    'sabotage_m72': ['S07:occurrences=117,expected=1', 'S16:occurrences=2,expected=1', 'S20:occurrences=0,expected=1',
                     'S21:occurrences=0,expected=1', 'S22:occurrences=0,expected=1'],
    'sabotage_m73': ['S07:occurrences=117,expected=1', 'S16:occurrences=2,expected=1'],
    'sabotage_m10': [],
}


class EveryTextListOnTheSource(unittest.TestCase):
    """E1-RI10 (a): M10's M2 list read from the source with ast.literal_eval: RI10's target is absent (occurrences 0), so the check fails
    on M10; the successor's corrected list (tools/m2_mutants_s1.py, RI10 only changed) has every target exactly once.  The same check for
    the other text lists the successor runs: M8's mutants (every target exactly once) and the plants of every sabotage tool whose successor
    takes M10's CASES (sabotage_f67, f671 to f674, m7, m71, m72, m73 and m10), where the plants whose target is not exactly once are
    exactly the pinned set NOT_EXACTLY_ONCE (finding F2), which the successor's preflight refuses.  (The MIE sabotage catalogues and sabotage_m8's function plants are checked by
    their own preflight at the start of every run.)"""

    def test_m10_m2_list_from_the_source_fails_only_on_ri10(self):
        mut = literal_list(os.path.join(ROOT, 'tools', 'm2_mutants.py'), 'MUT')
        self.assertEqual(len(mut), 199)
        errs, _ = E.preflight_text([(mid, os.path.join('apg', f), old, new, None) for mid, f, old, new in mut], ROOT)
        self.assertEqual([e.line() for e in errs], ['RUN_ERROR PREFLIGHT_INVALID_TARGET RI10-query-crosses-tenants:occurrences=0,expected=1'])

    def test_the_successor_m2_list_has_every_target_exactly_once(self):
        S = E.load_tool_module('m2_mutants_s1', ROOT)
        lst = S.mut_list()
        self.assertEqual([m[0] for m in lst], [m[0] for m in literal_list(os.path.join(ROOT, 'tools', 'm2_mutants.py'), 'MUT')])
        errs, _ = E.preflight_text([(mid, os.path.join('apg', f), old, new, None) for mid, f, old, new in lst], ROOT)
        self.assertEqual(errs, [])

    def test_m8_mutants_and_the_sabotage_plants(self):
        m8 = E.load_tool_module('m8_mutants', ROOT).MUTANTS       # built from named constants, so loaded (main() is guarded)
        self.assertEqual(E.preflight_text([(mid, f, old, new, None) for mid, f, old, new in m8 if f], ROOT)[0], [])
        for tool in ('sabotage_f67', 'sabotage_f671', 'sabotage_f672', 'sabotage_f673', 'sabotage_f674', 'sabotage_m7', 'sabotage_m71',
                     'sabotage_m72', 'sabotage_m73', 'sabotage_m10'):
            with self.subTest(tool=tool):
                M = E.load_tool_module(tool, ROOT)
                plants = [E.text_plant(*c[:6]) for c in M.CASES]
                items = [(p.id, p.relpath, p.text_old, None, p.occurrences) for p in plants if not p.creates]
                self.assertTrue(items)
                errs = E.preflight_text(items, ROOT)[0]
                self.assertEqual(sorted(e.detail for e in errs), NOT_EXACTLY_ONCE[tool])
                for p in plants:                       # a plant that adds a file: the file must not exist yet
                    if p.creates:
                        self.assertFalse(os.path.lexists(os.path.join(ROOT, p.relpath)), p.id)


STUB_LOGGING = """import sys, time
open(%r, 'a').write(' '.join(sys.argv[1:]) + '\\n')
print('tests 1  failures 0  errors 0')
sys.exit(0)
"""


class PreflightFailClosedAtToolLevel(unittest.TestCase):
    """E1-RI10 (b) test_preflight_fail_closed, with its (R4) lines: in a temporary copy one mutant's target text is removed from its file.
    On M10 (its list trimmed in the copy to three mutants, its children replaced by a logging stub) the workers start and run the other
    mutants, and the ERROR is reported only afterwards (exit 2).  On the successor the run stops in the preflight: PREFLIGHT FAILED, its
    RUN_ERROR line, 199 MUTANT NOT_RUN lines, no KILLED or SURVIVED, no worker directory, and preflight=FAIL started=0 not_run=199
    control_end=NOT_RUN status=EVIDENCE_ERROR exit=2; with two texts removed, two RUN_ERROR lines and run_errors=2."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_pfc_')
        self.mut = literal_list(os.path.join(ROOT, 'tools', 'm2_mutants.py'), 'MUT')
        self.ok = [m for m in self.mut if m[0] != 'RI10-query-crosses-tenants']

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def copy_without(self, name, items):
        tree = os.path.join(self.tmp, name)
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        for mid, f, old, new in items:
            p = os.path.join(tree, 'apg', f)
            with open(p, encoding='utf-8') as fh:
                src = fh.read()
            assert src.count(old) == 1
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write(src.replace(old, '# removed by tests_tools for ' + mid))
        return tree

    def run_tool(self, tree, script, args, site):
        import subprocess
        tmpdir = os.path.join(self.tmp, 'TMP_' + os.path.basename(tree))
        os.makedirs(tmpdir)
        cmd = [sys.executable, '-I'] + ([] if site else ['-S']) + [os.path.join('tools', script)] + args
        p = subprocess.run(cmd, cwd=tree, capture_output=True, text=True, timeout=900,
                           env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmpdir,
                                'PYTHONDONTWRITEBYTECODE': '1'})
        return p.returncode, p.stdout, os.listdir(tmpdir)

    def test_m10_starts_the_workers_and_reports_the_error_afterwards(self):
        gone = self.ok[0]
        tree = self.copy_without('m10', [gone])
        log = os.path.join(self.tmp, 'children.log')
        for f in ('run_m2_tests.py', 'run_contracts.py'):
            with open(os.path.join(tree, 'tools', f), 'w') as fh:
                fh.write(STUB_LOGGING % log)
        keep = [gone[0], self.ok[1][0], self.ok[2][0]]
        p = os.path.join(tree, 'tools', 'm2_mutants.py')
        with open(p, encoding='utf-8') as fh:
            src = fh.read()
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(src.replace('\ndef main():\n', '\nMUT = [m for m in MUT if m[0] in %r]\n\n\ndef main():\n' % keep, 1))
        code, out, _ = self.run_tool(tree, 'm2_mutants.py', ['--jobs', '1'], site=True)
        self.assertEqual(code, 2, out[-1500:])
        self.assertIn('ERROR %s: pattern not found' % gone[0], out)
        with open(log) as fh:
            self.assertGreaterEqual(len(fh.read().splitlines()), 2)      # the other mutants' children ran first

    def test_successor_stops_in_the_preflight(self):
        for n in (1, 2):
            with self.subTest(removed=n):
                gone = self.ok[:n]
                code, out, tmpfiles = self.run_tool(self.copy_without('s1_%d' % n, gone), 'm2_mutants_s1.py', [], site=False)
                self.assertEqual(code, 2, out[-2000:])
                for mid, f, old, new in gone:
                    self.assertIn('RUN_ERROR PREFLIGHT_INVALID_TARGET %s:occurrences=0,expected=1' % mid, out)
                    self.assertIn('PREFLIGHT FAILED %s:' % mid, out)
                self.assertEqual(len([l for l in out.splitlines() if l.startswith('MUTANT ') and l.endswith(' NOT_RUN cause=preflight_failed')]), 199)
                self.assertNotRegex(out, r'(?m)^MUTANT \S+ (KILLED|SURVIVED)')
                self.assertEqual(tmpfiles, [])                                   # no worker directory was made
                last = out.strip().splitlines()[-1]
                self.assertIn(' preflight=FAIL control_start=NOT_RUN started=0 ', last)
                self.assertIn(' not_run=199 control_end=NOT_RUN run_errors=%d ' % n, last)
                self.assertTrue(last.endswith(' status=EVIDENCE_ERROR exit=2'))
                self.assertEqual(E.check_output(out, code), [])

if __name__ == '__main__':
    unittest.main()
