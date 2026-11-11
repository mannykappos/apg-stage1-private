#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_cr02_reference.py (P1-F6: 'builds its child environment from os.environ today; moves to clean_env(),
§2.8'; DP-1.2 (B): the M10 file stays byte-identical).  M10's script runs unchanged (checked against its M10 SHA-256), with three changes
around it: the start sequence first (§2.8, §2.5); this process's environment replaced by the allowlist, so its children inherit only that;
and every Python child started with -I -S.  M10 also set CR02_MUT_JOBS=4 for the mutants child; it is not set here (a variable outside the
allowlist, DP-1.3 (a)), so the CR-02 harness uses its own default of 2 jobs: slower, the same results.  No result kind is assigned to this
tool (T_tooling.md T-K, 'Not assigned a kind'), so its output is M10's; the marker CR-02 REFERENCE RERUN OK only on success.
Usage: python3 -I -S tools/run_cr02_reference_s1.py          BUILDER-EXECUTED: NOT INDEPENDENT."""
import hashlib
import os
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

M10_SHA256 = '59eecd583f8147dabb967fc7afdbb632cc0c520442456cb9d1631c1036ab55cb'


def main():
    lines, errs = E.start(ROOT, preloaded=E.PRELOADED_AT_EVKIT_IMPORT)
    for l in lines:
        print(l)
    if errs:
        for e in errs:
            print(e.line())
        print('CR-02 REFERENCE RERUN FAILED')
        return 2
    path = os.path.join(ROOT, 'tools', 'run_cr02_reference.py')
    with open(path, 'rb') as fh:
        src = fh.read()
    if hashlib.sha256(src).hexdigest() != M10_SHA256:
        print(E.RunError('M10_SOURCE_CHANGED', 'run_cr02_reference %s' % hashlib.sha256(src).hexdigest()).line())
        return 2
    import tempfile
    tmp = tempfile.mkdtemp(prefix='s1_cr02_')
    env = E.clean_env(tmp)
    os.environ.clear()
    os.environ.update(env)
    real_run = subprocess.run

    def run(cmd, *a, **k):
        cmd = list(cmd)
        if cmd[:2] == [sys.executable, '-I'] and '-S' not in cmd[:3]:
            cmd.insert(2, '-S')
        if 'env' in k:
            k['env'] = {x: v for x, v in k['env'].items() if x in env}
        return real_run(cmd, *a, **k)
    subprocess.run = run
    try:
        exec(compile(src, path, 'exec'), {'__name__': '__main__', '__file__': path})
    finally:
        subprocess.run = real_run
    return 0


if __name__ == '__main__':
    sys.exit(main())
