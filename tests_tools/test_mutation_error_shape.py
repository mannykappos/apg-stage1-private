"""Stage 1 (APG-M11-S1), Workstream T, P2-S3, P3-S01, P4-S14, P5-S07 and T-0: a mutation worker's error never crashes the run or hides the
other results.  On M10, m3/m4/m5/m6/m7/m91_mutants.py return a 3-tuple from a worker whose mutate() raises and then unpack two names, so the
run dies with a traceback (exit 1) before its ERROR branch can run.  The successor dry-runs every selected mutant's mutation in the preflight
(RUN_ERROR PREFLIGHT_INVALID_TARGET <id>:mutate_raised, every mutant NOT_RUN, exit 2, before any work), and a worker exception that still
happens is that mutant's ITEM_ERROR cause=worker_exception, with every other line printed and exit 2.  Each case runs in a temporary copy in
which the M10 tool's mutate() is patched to raise for one mutant; the M10 tools are byte-identical in this tree (DP-1.2 (B)).
Run from the package root:  python3 -I -S tests_tools/test_mutation_error_shape.py      BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOLS = ('m3', 'm4', 'm5', 'm6', 'm7', 'm91')
PATCH = '''
_s1_test_orig_mutate = mutate
_s1_test_calls = [0]


def mutate(src, kind, idx):     # planted by tests_tools/test_mutation_error_shape.py
    if (kind, idx) == %r:
        _s1_test_calls[0] += 1
        if _s1_test_calls[0] > %d:
            raise RuntimeError('planted: mutate raises for this mutant')
    return _s1_test_orig_mutate(src, kind, idx)


'''


def run(tree, script, *args, isolated_site=True):
    tmp = tempfile.mkdtemp(prefix='s1_err_')
    try:
        cmd = [sys.executable, '-I'] + (['-S'] if isolated_site else []) + [os.path.join('tools', script)] + list(args)
        p = subprocess.run(cmd, cwd=tree, capture_output=True, text=True, timeout=1800,
                           env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp,
                                'PYTHONDONTWRITEBYTECODE': '1'})
        return p.returncode, p.stdout, p.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def first_candidate(tool):
    M = E.load_tool_module('%s_mutants' % tool, ROOT)
    return M.candidates()[0]


def planted_copy(dest, tool, raise_after_calls):
    """A copy of this tree whose tools/<tool>_mutants.py mutate() raises for the tool's first candidate, after raise_after_calls calls."""
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
    mid, _, kind, idx = first_candidate(tool)
    p = os.path.join(dest, 'tools', '%s_mutants.py' % tool)
    with open(p, encoding='utf-8') as f:
        src = f.read()
    marker = "\nif __name__ == '__main__':"
    assert src.count(marker) == 1
    with open(p, 'w', encoding='utf-8') as f:
        f.write(src.replace(marker, '\n' + PATCH % ((kind, idx), raise_after_calls) + marker.lstrip('\n')))
    return mid


class MutateRaises(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_errshape_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_m10_crashes_with_a_traceback(self):
        for tool in TOOLS:
            with self.subTest(tool=tool):
                tree = os.path.join(self.tmp, tool + '_m10')
                mid = planted_copy(tree, tool, 0)
                code, out, err = run(tree, '%s_mutants.py' % tool, '--ids', mid, '--jobs', '1', isolated_site=False)
                self.assertEqual(code, 1, out[-1500:] + err[-1500:])
                self.assertIn('Traceback', err)
                self.assertIn('ValueError: too many values to unpack', err)
                self.assertNotIn('ERROR %s' % mid, out)       # the ERROR branch never runs

    def test_successor_stops_in_the_preflight(self):
        for tool in TOOLS:
            with self.subTest(tool=tool):
                tree = os.path.join(self.tmp, tool + '_s1')
                mid = planted_copy(tree, tool, 0)
                code, out, err = run(tree, '%s_mutants_s1.py' % tool, '--ids', mid)
                self.assertEqual(code, 2, out[-2000:] + err[-2000:])
                self.assertIn('RUN_ERROR PREFLIGHT_INVALID_TARGET %s:mutate_raised' % mid, out)
                self.assertIn('MUTANT %s NOT_RUN cause=preflight_failed' % mid, out)
                last = out.strip().splitlines()[-1]
                self.assertIn(' preflight=FAIL control_start=NOT_RUN started=0 ', last)
                self.assertTrue(last.endswith(' status=EVIDENCE_ERROR exit=2'), last)
                self.assertNotIn('Traceback', err)
                self.assertEqual(E.check_output(out, code, selected=[mid]), [])

    def test_successor_reports_a_worker_exception_as_that_mutants_item_error(self):
        # raise only after the preflight's dry run, so the worker meets the exception: the run still prints every line and exits 2
        tree = os.path.join(self.tmp, 'm91_worker')
        mid = planted_copy(tree, 'm91', 1)
        M = E.load_tool_module('m91_mutants', ROOT)
        other = M.candidates()[1][0]
        code, out, err = run(tree, 'm91_mutants_s1.py', '--ids', '%s,%s' % (mid, other))
        self.assertEqual(code, 2, out[-2000:] + err[-2000:])
        self.assertIn('MUTANT %s ITEM_ERROR cause=worker_exception' % mid, out)
        self.assertRegex(out, r'(?m)^MUTANT %s (KILLED|SURVIVED|EQUIVALENT) ' % other)   # the other mutant's result is still there
        self.assertIn(' item_errors=1 ', out.strip().splitlines()[-1])
        self.assertTrue(out.strip().splitlines()[-1].endswith(' status=EVIDENCE_ERROR exit=2'))
        self.assertEqual(E.check_output(out, code, selected=[mid, other]), [])


    def test_every_tool_reports_a_worker_exception_as_that_mutants_item_error(self):
        # the same case for m3, m4, m5, m6 and m7 (m91 above runs its real child): the copy's child test runner is the passing stub of
        # test_mutation_timeout.py, so the other mutant SURVIVES quickly and the raising one is ITEM_ERROR
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import test_mutation_timeout as H
        ok = H._stub_text('ok')[0]
        for tool in ('m3', 'm4', 'm5', 'm6', 'm7'):
            with self.subTest(tool=tool):
                tree = os.path.join(self.tmp, tool + '_worker')
                mid = planted_copy(tree, tool, 1)
                for f in H.MUT_TOOLS[tool][1]:
                    with open(os.path.join(tree, 'tools', f), 'w', encoding='utf-8') as fh:
                        fh.write(H.STUB % {'mode': 'ok', 'ok': ok, 'failed': ok, 'evidence': ok, 'sleep': 0})
                M = E.load_tool_module('%s_mutants' % tool, ROOT)
                other = M.candidates()[1][0]
                code, out, err = run(tree, '%s_mutants_s1.py' % tool, '--ids', '%s,%s' % (mid, other))
                self.assertEqual(code, 2, out[-2000:] + err[-2000:])
                self.assertIn('MUTANT %s ITEM_ERROR cause=worker_exception' % mid, out)
                self.assertRegex(out, r'(?m)^MUTANT %s (SURVIVED|EQUIVALENT) ' % other)
                last = out.strip().splitlines()[-1]
                self.assertIn(' item_errors=1 ', last)
                self.assertTrue(last.endswith(' status=EVIDENCE_ERROR exit=2'))
                self.assertEqual(E.check_output(out, code, selected=[mid, other]), [])
                shutil.rmtree(tree, ignore_errors=True)

if __name__ == '__main__':
    unittest.main()
