#!/usr/bin/env python3
"""Mutation run over the APG-F67, APG-F67.1 and APG-F67.2 approval code (findings F-67, F-72, F-73), in small batches.  It reuses tools/f671_mutants.py unchanged (and through it
tools/f67_mutants.py and the M7 method of tools/m7_mutants.py: CMP, BOL, NOT, RSE and ARI, every site a mutant, none chosen or skipped), with the recommendation policy's
verified_approvers added (APG-F67.2 binds it to the revision that added the entry) and the F-67.2 tests run first.  The whole of apg/policy_approval.py is mutated, including the
new added_at.
Usage: python3 -I tools/f672_mutants.py [--list] [--batch K/N] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline] [--verbose] [--timeout SECONDS]
  --batch K/N        run only the K-th of N equal, fixed slices of the full mutant list (the order of --list)
  --timeout SECONDS  the per-mutant test timeout (default 300; 30 is ample: one mutant's tests take a few seconds)
Exit 0 only if every mutant run is killed or is a documented equivalent."""
import importlib.util, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('f671_mutants', os.path.join(ROOT, 'tools', 'f671_mutants.py'))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
F = M.F
F.TARGETS = [t if t[0] != 'RP' else ('RP', 'apg/rec/policy.py', ('approve_policy', '_confirm', 'approval_status', 'verified_approvers')) for t in F.TARGETS]
F.TESTS = ['test_f672_forged_entry.py'] + F.TESTS
F.EQUIV.update({
    'PA-CMP-012': 'equivalent against the reference store: for revision 1 the mutant (>= instead of >) reads revision 0, and the reference RecordStorePort.get returns None for any '
                  'revision outside 1..n, the same value the original assigns. The guard is kept for an Engine store that might treat revision 0 otherwise; the record-store '
                  'contract does not yet pin this down (noted for EDR-39/EDR-40).'})
_run_tests = F.run_tests


def run_tests(work, env):
    """As tools/f67_mutants.py, except that a timeout under a SHORT --timeout is not taken as a kill: with no early failure the full test list can take longer than a short
    timeout, so the mutant is run again under the tools' original 300 seconds and classified by that run (found while building APG-F67.2: two survivors had been hidden)."""
    res = _run_tests(work, env)
    if res == 'timeout' and F.TIMEOUT < 300:
        short, F_timeout = F.TIMEOUT, 300
        try:
            r = F.subprocess.run([sys.executable, '-I', 'tools/mut_runner.py'] + F.TESTS, cwd=work, env=env, capture_output=True, text=True, timeout=F_timeout)
        except F.subprocess.TimeoutExpired:
            return 'timeout (also under 300 s)'
        if r.returncode != 0:
            return (r.stdout.strip().splitlines() or ['crash'])[-1] + ' (rerun under 300 s after %d s timeout)' % short
        return None
    return res


F.run_tests = run_tests

if __name__ == '__main__':
    sys.exit(F.main())
