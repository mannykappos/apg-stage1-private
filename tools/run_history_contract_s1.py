#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_history_contract.py (amendment 1 row 12, T-K; decision R12 option (a), 2026-10-31 13:18;
DP-1.2 (B): the M10 file stays byte-identical).  One file, two invocations, each with exactly one result kind:
  - no option: kind=sabotage.  The plants are M10's four faulty stores, each with its one named case it must fail (M10 line 96); the
    reference store (InMemoryRecordStore) runs RH-01 to RH-06 at the start and at the end and must pass all six (tools/evkit.faults_main).
    The marker ALL HISTORY CASES PASS AND EVERY FAULTY STORE IS CAUGHT only on exit 0.
  - --factory module:attr (with --path DIR): kind=cases, the RH case inventory pinned; the candidate is loaded after the trusted harness,
    from its own package appended to the path, and a trusted name is refused (§2.5, DP-4.3 (c); tools/evkit.cases_main).
    The marker ALL HISTORY CASES PASS only on exit 0.
The four faulty stores are defined in M10's script, which runs at import; their definitions are loaded from that file, checked against its
M10 SHA-256, with no command-line option reaching it (tools/evkit.load_m10_prefix).
Usage: python3 -I -S tools/run_history_contract_s1.py [--list] [--ids ID[,ID]] [--run-id ID] | --pin --reason TEXT --cause TEXT
       python3 -I -S tools/run_history_contract_s1.py --path DIR --factory module:attr [--only RH-01,..] [--run-id ID]
       python3 -I -S tools/run_history_contract_s1.py --pin-cases --reason TEXT --cause TEXT
Exit codes as §2.4.     BUILDER-EXECUTED: NOT INDEPENDENT.
Corrective pass 2 (C, B, amendment 2 AM2-1): the M10 load and STORES run in load(), under evkit.import_guard; the fault mode's
plants and controls are forked units under P (evkit.faults_main); the case mode's one harness call is batch(), one forked unit
(evkit.cases_main)."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

M10_SHA256 = "c8a887c9e8423997a4ffb7fedaa283ba289d26035f3fd00b39f987524097c1f8"
SUITE = "record_store_history"
H = None
STORES = ()


def load():
    global H, STORES
    with E.import_guard("run_history_contract"):
        H = E.load_m10_prefix("run_history_contract", "if opt('--factory'):", M10_SHA256)
        STORES = ((H.OutOfRangeReadsLatest, "RH-03"), (H.LeaksStoredObjects, "RH-06"), (H.AppendsIdentical, "RH-04"),
                  (H.RewritesHistory, "RH-02"))
    return {"batch": batch}


def failed(cls):
    return {r[0] for r in H.run_history_suite(H.env_for(cls)) if not r[2]}


def batch(cand):
    return [[SUITE, r[0], bool(r[2]), str(r[3])] for r in H.run_history_suite(cand.get("--factory") or H.env_for(H.InMemoryRecordStore))]


def main(argv):
    if "--factory" in argv or "--path" in argv or "--pin-cases" in argv:
        argv = ["--pin" if a == "--pin-cases" else a for a in argv]
        return E.cases_main("run_history_contract_s1", None, None, argv, candidate_options=("--factory",),
                            success_marker="ALL HISTORY CASES PASS", human_label="history cases", load=load)
    rc = E.guarded_load("run_history_contract_s1", "sabotage", load)
    if rc is not None:
        return rc
    plants = [(cls.__name__, cls.__doc__.strip(), (lambda cls=cls: failed(cls)), [must]) for cls, must in STORES]
    return E.faults_main("run_history_contract_s1", plants, lambda: failed(H.InMemoryRecordStore), argv,
                         success_marker="ALL HISTORY CASES PASS AND EVERY FAULTY STORE IS CAUGHT", total_label="faulty stores")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
