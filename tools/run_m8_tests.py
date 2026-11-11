#!/usr/bin/env python3
"""Runs the APG-M8 tests (tests_m8/), ONE TEST FILE AT A TIME, with the AUIF dependency (rev14 from APG-M8.1) verified by hash BEFORE the run (ZIP SHA-256, fresh extraction, AUIF's own
manifest check, core tree hash) and again AFTER it (the run changed no AUIF file).  Standard library only; synthetic data; no network.
Usage: python3 -I tools/run_m8_tests.py [--list] [--file NAME ...]       Exit 0 only if every file passed with its expected count and AUIF was unchanged."""
import os, platform, re, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from apg_auif import dependency                                    # noqa: E402

EXPECTED = {'test_m8_dependency.py': 7, 'test_m8_dev01.py': 10, 'test_m8_conformance.py': 7, 'test_m8_layout_config.py': 5, 'test_m8_definitions.py': 29,
            'test_m8_path_equivalence.py': 11, 'test_m8_corpus.py': 5, 'test_m8_no_fallback.py': 24, 'test_m8_events.py': 13, 'test_m8_delivery_rules.py': 5,
            'test_m8_findings.py': 10, 'test_m8_integrity.py': 21, 'test_m8_lineage.py': 7, 'test_m8_boundary.py': 8,
            'test_m8r1_empty_source.py': 10}      # M8-R1: the empty-source tests (finding M8-F7)


def files():
    return sorted(f for f in os.listdir(os.path.join(ROOT, 'tests_m8')) if f.startswith('test_') and f.endswith('.py'))


def run_file(f, env):
    t = time.time()
    r = subprocess.run([sys.executable, '-B', '-W', 'ignore', '-m', 'unittest', 'tests_m8.' + f[:-3]], cwd=ROOT, env=env, capture_output=True, text=True, timeout=3600)
    m = re.search(r'Ran (\d+) test', r.stderr)
    n = int(m.group(1)) if m else -1
    ok = r.returncode == 0 and n == EXPECTED.get(f)
    return ok, n, time.time() - t, r.stderr.strip().splitlines()[-12:]


def main():
    a = sys.argv[1:]
    if '--list' in a:
        for i, f in enumerate(files(), 1):
            print('%2d %-32s %d tests' % (i, f, EXPECTED.get(f, -1)))
        print('total %d tests in %d files' % (sum(EXPECTED.values()), len(EXPECTED)))
        return 0
    want = a[a.index('--file') + 1:] if '--file' in a else files()
    missing = sorted(set(files()) ^ set(EXPECTED))
    if missing:
        print('the expected-count table and tests_m8/ disagree: %s' % missing)
        return 1
    print('interpreter: %s | %s' % (sys.version.split()[0], platform.platform()))
    dep = dependency.ensure()
    print('AUIF verified before the run: zip %s | tree %s | core %s | %d files | %s' % (dep['zip_sha256'][:16], dep['tree_sha256'][:16], dep['core_tree_sha256'][:16], dep['files_checked'], dep['root']), flush=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **{dependency.ENV: dep['root']})
    env.pop('APG_ROOT', None) if 'APG_ROOT' not in os.environ else None
    bad, total = [], 0
    for f in want:
        ok, n, secs, tail = run_file(f, env)
        total += max(n, 0)
        print('%s %-32s tests %3d (expected %3s)  %5.1fs' % ('PASS' if ok else 'FAIL', f, n, EXPECTED.get(f), secs), flush=True)
        if not ok:
            bad.append(f)
            print('   ' + '\n   '.join(tail))
    after = dependency.reverify(dep['root'])
    same = after['tree_sha256'] == dependency.TREE_SHA256 and after['core_tree_sha256'] == dependency.CORE_TREE_SHA256
    print('AUIF verified after the run: %s' % ('unchanged (tree %s, core %s)' % (after['tree_sha256'][:16], after['core_tree_sha256'][:16]) if same else 'CHANGED'))
    print('M8 tests %d in %d files, failed files %d' % (total, len(want), len(bad)) + (': %s' % bad if bad else ''))
    return 0 if not bad and same else 1


if __name__ == '__main__':
    sys.exit(main())
