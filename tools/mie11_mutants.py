#!/usr/bin/env python3
"""The MIE-1 mutation run (tools/mie_mutants.py, reused unchanged: same modules, same kinds, every site a mutant) with the MIE-1.1 correction tests added to the tests run
against each mutant.  The site count grows with the MIE-1.1 code.  Usage: python3 -I tools/mie11_mutants.py [--list] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline]
Exit 0 only if every mutant is killed or is a documented equivalent."""
import importlib.util, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('mie_mutants', os.path.join(ROOT, 'tools', 'mie_mutants.py'))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
M.ALL_TESTS.insert(0, 'test_mie_core_m11_corrections.py')          # the correction tests first: they kill the new sites fastest
M.EQUIV.update({})

if __name__ == '__main__':
    sys.exit(M.main())
