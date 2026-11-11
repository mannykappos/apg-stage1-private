"""Make the package under test importable.  APG-M11-S1 (P1-F6): APG_ROOT is no longer read.  The package root is this file's own tree; it
is inserted only if absent, and an apg package resolving anywhere else is refused here (the early guard).  The runner's import-identity
check (tools/evkit.py, R1_REQUIREMENTS.md §2.5) is the second line of defence."""
import os, sys
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
HERE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # the package root that holds builder_zero/ etc.
import apg as _apg                                                          # noqa: E402
if not os.path.realpath(_apg.__file__).startswith(os.path.realpath(HERE_ROOT) + os.sep):
    raise ImportError('apg resolves outside this package root: %s (expected under %s)' % (_apg.__file__, HERE_ROOT))
