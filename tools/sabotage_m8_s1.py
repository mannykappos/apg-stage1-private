#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/sabotage_m8.py (P1-F6, P7-B3; decision K-1 K17: kind=sabotage; DP-1.2 (B): the M10 file stays byte-identical).
The plants are M10's CASES (id, what, function, command), unchanged: each function damages one thing in a private copy of the whole tree,
and its site (pinned) is the function's own source.  Their checks:
  - ['tools/run_m8_tests.py', '--file', F]: redirected to tools/run_m8_tests_s1.py --file F under the pinned caller profile
    run_m8_tests_s1@sabotage_tool (mode=full: DP-2.3 F6 sets run_m8_tests to full, and F9 names sabotage_m8's commands without a mode
    change; M10 ran them without -f), read from its RESULT v=2 line;
  - ['tools/run_regression_m8.py', '--step', R]: redirected to tools/run_regression_m8_s1.py, read by its own PASS/FAIL line (F9).
What changes (P7-B3): exact selection (--only, an unknown id is SELECTION_INVALID, exit 2; M10 gave 'sabotage cases 0' and exit 0), start
and end controls on the unbroken tree with every selected plant's check, a plant that changes nothing an ITEM_ERROR (never MISSED), a
timeout INDETERMINATE (M10's INCOMPLETE), one RESULT v=2 kind=sabotage line.
Usage: python3 -I -S tools/sabotage_m8_s1.py [--list] [--only ID[,ID]] [--jobs N] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import hashlib
import inspect
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'sabotage_m8_s1'
M = None   # moved into load() under evkit.import_guard (corrective pass 2, C.1)

def load():
    """C.1: the M10 load, and every module-level statement that uses it, after the start checks (evkit.guarded_load)."""
    global M
    with E.import_guard('sabotage_m8'):
        M = E.load_tool_module('sabotage_m8', ROOT)


def tree_digest(work):
    h = hashlib.sha256()
    for d, ds, fs in os.walk(work):
        ds[:] = sorted(x for x in ds if x != '__pycache__')
        for f in sorted(fs):
            p = os.path.join(d, f)
            h.update(os.path.relpath(p, work).encode() + b'\0')
            with open(p, 'rb') as fh:
                h.update(hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


def plant(cid, desc, fn, cmd):
    def apply(work, fn=fn):
        before = tree_digest(work)
        fn(work)
        if tree_digest(work) == before:
            raise RuntimeError('the plant changed nothing')
    p = E.Mutant(cid, '', 'function|%s|%s' % (fn.__name__, inspect.getsource(fn)), apply, what=desc, check=' '.join(cmd))
    p.m10_cmd = list(cmd)
    return p


def cmd(work, m10_cmd, run_id):
    if m10_cmd[0] == 'tools/run_m8_tests.py':
        return (' '.join(m10_cmd), E.child_cmd(os.path.join(work, 'tools', 'run_m8_tests_s1.py'),
                                                ['--caller', 'sabotage_tool', '--run-id', run_id] + m10_cmd[1:]))
    if m10_cmd[0] == 'tools/run_regression_m8.py' and m10_cmd[1] == '--step':
        return (' '.join(m10_cmd), E.child_cmd(os.path.join(work, 'tools', 'run_regression_m8_s1.py'), m10_cmd[1:]),
                E.regression_step_classifier(m10_cmd[2]))
    raise ValueError('no stage 1 route for %r' % (m10_cmd,))


def commands(work, p):
    return [cmd(work, p.m10_cmd, p.id)]


def control_commands(work, items):
    seen, out = [], []
    for p in items:
        if p.m10_cmd not in seen:
            seen.append(p.m10_cmd)
            out.append(cmd(work, p.m10_cmd, 'control'))
    return out


def main(argv):
    if '--timeout' in argv:
        return E.refuse_run('sabotage', TOOL, [c[0] for c in M.CASES], E.RunError('SELECTION_INVALID', "--timeout is fixed at M10's default (900 s) in the successor"))
    argv = ['--ids' if a == '--only' else a for a in argv]
    return E.mutation_main(TOOL, [plant(*c) for c in M.CASES], commands, argv, timeout=900, kind='sabotage', control_commands=control_commands,
                           copy_ignore=E.FULL_TREE_IGNORE)


if __name__ == '__main__':
    rc = E.guarded_load(TOOL, 'sabotage', load)
    if rc is not None:
        sys.exit(rc)
    sys.exit(main(sys.argv[1:]))
