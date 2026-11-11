#!/usr/bin/env python3
"""Mutation run over the APG-F67 and APG-F67.1 approval code (findings F-67 and F-72), in small batches.  It reuses tools/f67_mutants.py (and through it the M7 method of
tools/m7_mutants.py: CMP, BOL, NOT, RSE and ARI, every site a mutant, none chosen or skipped), with:
  PA  apg/policy_approval.py                        the whole module
  FP  apg/fin/policy.py   } the functions APG-F67 and APG-F67.1 changed or added: new_policy, new_spec, is_approved, view, spec_view, store_policy, store_spec,
  DP  apg/det/policy.py   } approve_policy, approve_spec, approval_status, spec_approval_status
  MP  apg/mkt/policy.py   }
  RP  apg/rec/policy.py   the functions APG-F67.1 changed or added: approve_policy, _confirm, approval_status
and the F-67.1 recovery tests run first.
Batches, so that every part finishes well inside a short execution limit:
  --batch K/N        run only the K-th of N equal, fixed slices of the full mutant list (the list and its order are those of --list)
  --timeout SECONDS  the per-mutant test timeout (default 300, as the earlier tools; 30 is ample here: one mutant's tests take a few seconds)
Usage: python3 -I tools/f671_mutants.py [--list] [--batch K/N] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline] [--verbose] [--timeout SECONDS]
Exit 0 only if every mutant run is killed or is a documented equivalent."""
import importlib.util, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('f67_mutants', os.path.join(ROOT, 'tools', 'f67_mutants.py'))
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)

CHANGED = F.CHANGED + ('approval_status', 'spec_approval_status')
F.TARGETS = [('PA', 'apg/policy_approval.py', None), ('FP', 'apg/fin/policy.py', CHANGED), ('DP', 'apg/det/policy.py', CHANGED), ('MP', 'apg/mkt/policy.py', CHANGED),
             ('RP', 'apg/rec/policy.py', ('approve_policy', '_confirm', 'approval_status'))]
F.TESTS = ['test_f671_approval_recovery.py', 'test_f67_policy_approval.py', 'test_rec_policy.py', 'test_rec_m71_corrections.py'] + F.TESTS[1:] + ['test_rec_golden.py']
_all = F.candidates


def candidates():
    c = _all()
    if '--batch' in sys.argv:
        k, n = (int(x) for x in sys.argv[sys.argv.index('--batch') + 1].split('/'))
        assert 1 <= k <= n
        size = -(-len(c) // n)
        c = c[(k - 1) * size:k * size]
    return c


F.candidates = candidates

if __name__ == '__main__':
    sys.exit(F.main())
