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
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

M10_SHA256 = '59eecd583f8147dabb967fc7afdbb632cc0c520442456cb9d1631c1036ab55cb'


def main():
    lines, errs = E.start(ROOT, preloaded=E.PRELOADED_AT_EVKIT_IMPORT)
    E._SUP.run_without_result = True
    lines = list(lines) + [E.limit_line(None)]
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
    leaked = []
    n = [0]

    def run(cmd, *a, **k):
        # AM-3: each child M10's script starts is a unit under P (its own group, stdin /dev/null, registered, cleaned up on every path);
        # the command rewriting (-S) and the environment filtering are kept; no time limit is added (M10 sets none)
        cmd = list(cmd)
        if cmd[:2] == [sys.executable, '-I'] and '-S' not in cmd[:3]:
            cmd.insert(2, '-S')
        child_env = {x: v for x, v in k['env'].items() if x in env} if 'env' in k else dict(os.environ)
        text = bool(k.get('text') or k.get('universal_newlines') or k.get('encoding') or k.get('errors'))
        empty = '' if text else b''
        if E.CANCEL.set:       # amendment 2, AM2-2 (c): a child not yet started is not started
            return subprocess.CompletedProcess(cmd, -15, empty, empty)
        n[0] += 1
        r = E.run_unit('cr02:%d' % n[0], cmd, k.get('timeout'), child_env, k.get('cwd'))
        if r.how == 'launch_error':
            raise OSError(r.stderr)
        if r.how == 'timeout':
            raise subprocess.TimeoutExpired(cmd, k.get('timeout'))
        if r.how == 'interrupted':     # AM2-2 (c): a child in flight is stopped under P.5 and reported as terminated by SIGTERM
            return subprocess.CompletedProcess(cmd, -15, empty, empty)
        if r.leaked:
            leaked.append(n[0])
        out, err = (r.stdout, r.stderr) if text else (r.stdout.encode('utf-8'), r.stderr.encode('utf-8'))
        return subprocess.CompletedProcess(cmd, r.returncode, out, err)
    subprocess.run = run
    real = sys.stdout
    hold = E._HoldLast(real)
    sys.stdout = hold
    code = 0
    try:
        try:
            exec(compile(src, path, 'exec'), {'__name__': '__main__', '__file__': path})
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        except Exception as e:      # AM2-2 (c): any other exception from M10's script: the same cleanup and record
            print('CR-02 REFERENCE RERUN FAILED (%s)' % type(e).__name__)
            code = 1
    finally:
        subprocess.run = real_run
        sys.stdout = real
        shutil.rmtree(tmp, ignore_errors=True)
    if leaked and code == 0:
        code = 2     # P.6: a child that left processes is never a pass (the CLEANUP line names it); reading recorded in the documents
    return E.finish_no_result_run(hold.buf, real, code)


if __name__ == '__main__':
    sys.exit(main())
