#!/usr/bin/env python3
"""Mutation run over the APG-F67 to APG-F67.3 approval code (findings F-67, F-72, F-73, F-74), in small batches.  It reuses tools/f672_mutants.py unchanged (and through it
tools/f671_mutants.py, tools/f67_mutants.py and the M7 method of tools/m7_mutants.py: CMP, BOL, NOT, RSE and ARI, every site a mutant, none chosen or skipped), including its
rule that a mutant which times out under a short --timeout is rerun under 300 seconds before it is classified.  The whole of apg/policy_approval.py is mutated, including the new
holds and content; the F-67.3 tests are run first.
Usage: python3 -I tools/f673_mutants.py [--list] [--batch K/N] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline] [--verbose] [--timeout SECONDS]
Exit 0 only if every mutant run is killed or is a documented equivalent."""
import importlib.util, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('f672_mutants', os.path.join(ROOT, 'tools', 'f672_mutants.py'))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
F = M.F
F.TESTS = ['test_f673_approval_integrity.py'] + F.TESTS
F.EQUIV.clear()                                  # mutant ids are renumbered when sites are added; the documented equivalents are listed again below
F.EQUIV.update({
    'PA-CMP-013': 'equivalent for any store that meets the record-store history contract (apg/contracts/record_store_history_contract.py, RH-03: a revision outside 1..n, '
                  'including 0, reads as nothing): for revision 1 the mutant (>= instead of >) reads revision 0, which reads as None, the value the original assigns. '
                  '(APG-F67.2 documented the same mutant as PA-CMP-012; the history contract now states and tests the store guarantee it relies on.)'})

if __name__ == '__main__':
    sys.exit(F.main())
