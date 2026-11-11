"""Run the contract suites against an implementation.

  python3 -I tools/run_contracts.py                                   # the reference implementations (all must pass)
  python3 -I tools/run_contracts.py --factory my_module:make_env --path /dir/with/my_module

A FACTORY is a zero-argument callable returning a fresh apg.contracts.framework.ContractEnv(provider, store, audit, advance)."""
from . import framework, audit_log_contract


def run(factory, suites=None):
    audit_log_contract.FACTORY_HOLDER['factory'] = factory
    return framework.run_suite(factory, suites)


def summarise(results):
    bad = [r for r in results if not r[3]]
    return len(results), len(bad), bad
