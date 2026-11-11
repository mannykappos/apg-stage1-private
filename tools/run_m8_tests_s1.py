#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m8_tests.py (P7-B2, P7-B3, P1-F6; DP-1.2 (B): tools/run_m8_tests.py stays byte-identical).
Runs the APG-M8 tests (tests_m8/) one test file at a time, each in its own child (tools/child_unittest_runner.py, started with -I -S), with
the AUIF dependency verified by hash before the run (apg_auif.dependency.ensure) and again after it.  The child environment is the
evkit allowlist; its one exception is APG_AUIF_ROOT, set only to the AUIF copy verified here (DP-1.3 (a)).  The test inventory is the
pinned one (tools/expected_counts.json), not M10's count table.  Prints kind=tests evidence (R1_REQUIREMENTS.md §2.7), mode=full.
Usage (from the package root):  python3 -I -S tools/run_m8_tests_s1.py [--caller NAME] [--run-id ID] [--file NAME ...]
Exit codes as §2.4.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'run_m8_tests_s1'
CHILD = os.path.join(ROOT, 'tools', 'child_unittest_runner.py')


def main(argv):
    caller, run_id, names, errors = 'standalone', 'run', None, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('--caller', '--run-id'):
            if i + 1 >= len(argv):
                errors.append(E.RunError('SELECTION_INVALID', 'missing value for %s' % a))
                break
            caller, run_id = (argv[i + 1], run_id) if a == '--caller' else (caller, argv[i + 1])
            i += 1
        elif a == '--file':
            names = names or []
            j = i + 1
            while j < len(argv) and not argv[j].startswith('-'):
                names.append(argv[j])
                j += 1
            i = j - 1
        else:
            errors.append(E.RunError('SELECTION_INVALID', 'unknown argument %s' % a))
        i += 1
    preloaded = tuple(k for k in sys.modules if k.split('.')[0] in E.TRUSTED_PACKAGES and k not in ('tools', 'tools.evkit'))
    lines, errs = E.start(ROOT, preloaded=preloaded)
    errs += errors
    fpins, rel = {}, []
    try:
        pins, _ = E.load_pins()
        if E.runner_mode(pins, TOOL, caller) != 'full':
            errs.append(E.RunError('RUNNER_MODE_NOT_PINNED', '%s@%s' % (TOOL, caller)))
        pinned = sorted(k for k in pins['test_files'] if k.startswith('tests_m8/'))
        on_disk = sorted('tests_m8/' + f for f in os.listdir(os.path.join(ROOT, 'tests_m8')) if f.startswith('test_') and f.endswith('.py'))
        for extra in sorted(set(on_disk) - set(pinned)):
            errs.append(E.RunError('TEST_FILE_NOT_IN_PINS', os.path.basename(extra)))
        rel = pinned if names is None else ['tests_m8/' + n for n in names]
        if not rel:
            errs.append(E.RunError('SELECTION_INVALID', 'no_files'))
        fpins = E.test_file_pins(pins, rel)
    except E.RunError as e:
        errs.append(e)
    names = [os.path.basename(r) for r in rel]
    results, extra_lines = {}, []
    tmp = tempfile.mkdtemp(prefix='s1_m8run_')
    try:
        if not errs and all(n in fpins for n in names):
            from apg_auif import dependency
            try:
                dep = dependency.ensure()
            except dependency.AuifDependencyError as e:
                errs.append(E.RunError('AUIF_DEPENDENCY_UNVERIFIED', str(e)[:200]))
                dep = None
            if dep:
                extra_lines.append('AUIF verified_before zip=%s tree=%s core=%s files=%d root=%s' % (
                    dep['zip_sha256'], dep['tree_sha256'], dep['core_tree_sha256'], dep['files_checked'], dep['root']))
                env = E.clean_env(tmp, auif_root=dep['root'])
                for r, n in zip(rel, names):
                    cmd = E.child_cmd(CHILD, ['--caller', TOOL, '--mode', 'full', '--run-id', run_id, r[:-3].replace('/', '.')])
                    outcome, out, err, secs, kind, fields = E.run_child(cmd, 3600, env, ROOT, pins={n: fpins[n]}, selected=[n])
                    results[n] = E.file_result_from_child(n, outcome, out)
                    extra_lines.append('CHILD %s %s %.1fs' % (n, outcome, secs))
                after = dependency.reverify(dep['root'])
                same = after['tree_sha256'] == dependency.TREE_SHA256 and after['core_tree_sha256'] == dependency.CORE_TREE_SHA256
                extra_lines.append('AUIF verified_after %s' % ('unchanged' if same else 'CHANGED'))
                if not same:
                    errs.append(E.RunError('AUIF_CHANGED_BY_RUN', after['tree_sha256']))
            verified = E.verified_auif_root()
            ierrs, recs = E.import_identity(ROOT, preloaded=preloaded, candidate_paths=(verified,) if verified else ())
            errs += ierrs
            extra_lines += ['IMPORT_END %s %s' % (n, p) for n, p in recs]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out, code = E.finish_tests(TOOL, 'full', run_id, names, results, fpins, errs)
    k = next(i for i, l in enumerate(out) if l.startswith('RUN_ERROR') or l.startswith('RESULT'))
    t = sum(len(r.tests) for r in results.values() if r.state == 'COMPLETED')
    nbad = sum(1 for r in results.values() if r.state != 'COMPLETED' or any(s in ('FAIL', 'ERROR') for _, s in r.tests))
    human = ['M8 tests %d in %d files, failed files %d' % (t, len(names), nbad)]
    return E.emit(lines + out[:k] + extra_lines + human + out[k:], code)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
