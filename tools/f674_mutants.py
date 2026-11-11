#!/usr/bin/env python3
"""Mutation run over the APG-F67 to APG-F67.4 approval code (findings F-67, F-72 to F-75), in small batches.  It reuses tools/f673_mutants.py unchanged (and through it the
F-67.2 rule that a mutant which times out under a short --timeout is rerun under 300 seconds before it is classified, and the M7 method: CMP, BOL, NOT, RSE and ARI, every site a
mutant, none chosen or skipped).  The whole of apg/policy_approval.py is mutated, including the new fingerprint and same; the recommendation policy's store_policy is added
(APG-F67.4 changed its re-store comparison); the F-67.4 tests are run first.
Usage: python3 -I tools/f674_mutants.py [--list] [--batch K/N] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline] [--verbose] [--timeout SECONDS]
Exit 0 only if every mutant run is killed or is a documented equivalent."""
import importlib.util, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('f673_mutants', os.path.join(ROOT, 'tools', 'f673_mutants.py'))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
F = M.F
F.TARGETS = [t if t[0] != 'RP' else ('RP', 'apg/rec/policy.py', ('approve_policy', '_confirm', 'approval_status', 'verified_approvers', 'store_policy')) for t in F.TARGETS]
F.TESTS = ['test_f674_type_strict.py'] + F.TESTS
F.EQUIV.clear()                                  # mutant ids are renumbered when sites are added; the documented equivalents are listed again below
F.EQUIV.update({
    'PA-CMP-013': 'equivalent for any store that meets the record-store history contract (apg/contracts/record_store_history_contract.py, RH-03: a revision outside 1..n, '
                  'including 0, reads as nothing): for revision 1 the mutant (>= instead of >) reads revision 0, which reads as None, the value the original assigns. '
                  '(The same mutant as APG-F67.2 PA-CMP-012 and APG-F67.3 PA-CMP-013.)'})

if __name__ == '__main__':
    sys.exit(F.main())
