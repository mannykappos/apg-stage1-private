"""APG-M10 tests: the prototype's view model (test_m10_viewmodel.py).  The browser tests of the screens are in ui_tests/ (Node and Playwright)."""
import os, sys
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
