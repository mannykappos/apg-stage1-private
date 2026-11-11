#!/usr/bin/env python3
"""Every APG-F67.4 check as a short numbered group, so that each finishes well inside a short execution limit.  Groups 1 to 10 are the probes, the correction tests, the
regression steps, the contracts, the mutation baseline and a check that the suite groups cover every test file exactly once.  Groups 11 to 23 are the whole unit suite in
13 small parts, each a fixed list of test files with its test count, so that a reviewer can add them up (about 15 seconds each on the build machine; the longest part is the
single file test_mie_construction.py).  The whole suite also stays runnable as one command: python3 -I tools/run_m2_tests.py -q
Usage: python3 -I tools/run_f674_all.py --list | --group N | --range A-B | --files-list | --file N | --files A-B   (one test file per group: --file, --files)
A group cut off by a time limit is incomplete, not a pass: run it again alone and report it as incomplete if it still does not finish.  Exit 0 only if every group run passed."""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
T = 'tools/run_m2_tests.py'
OK = 'failures 0  errors 0'
SUITE = [
    ('whole suite, part 1 of 13: test_adversarial_builder_zero.py to test_det_detect.py (12 files)', ['test_adversarial_builder_zero.py', 'test_api_action_port_contract.py', 'test_api_approval_boundary.py', 'test_api_m92_corrections.py', 'test_api_m93_corrections.py', 'test_api_m94_corrections.py', 'test_api_static.py', 'test_det_approval_binding.py', 'test_det_common.py', 'test_det_contracts.py', 'test_det_corpus.py', 'test_det_detect.py'], 245),
    ('whole suite, part 2 of 13: test_det_findings.py to test_det_policy_bounds.py (8 files)', ['test_det_findings.py', 'test_det_findings_edges.py', 'test_det_golden.py', 'test_det_intake.py', 'test_det_monitor.py', 'test_det_noise.py', 'test_det_policy.py', 'test_det_policy_bounds.py'], 151),
    ('whole suite, part 3 of 13: test_det_portfolio.py to test_det_static.py (12 files)', ['test_det_portfolio.py', 'test_det_proposal_binding.py', 'test_det_proposal_identity.py', 'test_det_rules_commercial.py', 'test_det_rules_commercial_edges.py', 'test_det_rules_cost.py', 'test_det_rules_cost_edges.py', 'test_det_rules_ops.py', 'test_det_rules_ops_edges.py', 'test_det_run_edges.py', 'test_det_signal.py', 'test_det_static.py'], 321),
    ('whole suite, part 4 of 13: test_det_transition_gate.py to test_fin_forecast.py (15 files)', ['test_det_transition_gate.py', 'test_det_version_types.py', 'test_f671_approval_recovery.py', 'test_f672_forged_entry.py', 'test_f673_approval_integrity.py', 'test_f674_type_strict.py', 'test_f67_policy_approval.py', 'test_fin_arith.py', 'test_fin_boundaries.py', 'test_fin_bridge_book.py', 'test_fin_cash.py', 'test_fin_commitments.py', 'test_fin_corpus.py', 'test_fin_costs.py', 'test_fin_forecast.py'], 383),
    ('whole suite, part 5 of 13: test_fin_golden.py to test_golden.py (6 files)', ['test_fin_golden.py', 'test_fin_intake.py', 'test_fin_records.py', 'test_fin_revenue.py', 'test_fin_static.py', 'test_golden.py'], 84),
    ('whole suite, part 6 of 13: test_ingest_adversarial.py to test_ingest_contracts.py (3 files)', ['test_ingest_adversarial.py', 'test_ingest_boundaries.py', 'test_ingest_contracts.py'], 87),
    ('whole suite, part 7 of 13: test_ingest_golden.py to test_materiality_engine.py (6 files)', ['test_ingest_golden.py', 'test_ingest_mapping.py', 'test_ingest_pipeline.py', 'test_ingest_reconcile.py', 'test_ingest_support.py', 'test_materiality_engine.py'], 182),
    ('whole suite, part 8 of 13: test_mie_construction.py to test_mie_construction.py (1 files)', ['test_mie_construction.py'], 23),
    ('whole suite, part 9 of 13: test_mie_core_adversarial.py to test_mkt_demand.py (19 files)', ['test_mie_core_adversarial.py', 'test_mie_core_audit.py', 'test_mie_core_boundaries.py', 'test_mie_core_canon.py', 'test_mie_core_m11_corrections.py', 'test_mie_core_observations.py', 'test_mie_core_pack.py', 'test_mie_core_ports.py', 'test_mie_core_replay.py', 'test_mie_core_signals.py', 'test_mie_core_static.py', 'test_mie_core_tenancy.py', 'test_mie_core_timing.py', 'test_mie_flow.py', 'test_mie_portability.py', 'test_mkt_compare.py', 'test_mkt_contracts.py', 'test_mkt_corpus.py', 'test_mkt_demand.py'], 273),
    ('whole suite, part 10 of 13: test_mkt_detect.py to test_mkt_fx_fresh.py (7 files)', ['test_mkt_detect.py', 'test_mkt_edges_base.py', 'test_mkt_edges_demand.py', 'test_mkt_edges_landed.py', 'test_mkt_edges_policy.py', 'test_mkt_edges_rules.py', 'test_mkt_fx_fresh.py'], 259),
    ('whole suite, part 11 of 13: test_mkt_golden.py to test_mkt_spec.py (8 files)', ['test_mkt_golden.py', 'test_mkt_intake.py', 'test_mkt_landed.py', 'test_mkt_opportunities.py', 'test_mkt_policy.py', 'test_mkt_rules.py', 'test_mkt_scenarios.py', 'test_mkt_spec.py'], 214),
    ('whole suite, part 12 of 13: test_mkt_static.py to test_rec_m71_corrections.py (8 files)', ['test_mkt_static.py', 'test_rec_constraints.py', 'test_rec_edges.py', 'test_rec_eligibility.py', 'test_rec_golden.py', 'test_rec_isolation.py', 'test_rec_lifecycle.py', 'test_rec_m71_corrections.py'], 153),
    ('whole suite, part 13 of 13: test_rec_m72_race.py to test_values.py (12 files)', ['test_rec_m72_race.py', 'test_rec_m73_insert_race.py', 'test_rec_money.py', 'test_rec_policy.py', 'test_rec_ranking.py', 'test_rec_repro.py', 'test_rec_verify.py', 'test_repro.py', 'test_source_authority.py', 'test_status_model.py', 'test_tenancy.py', 'test_values.py'], 208),
]

PRE = [
    ('Static regression against the delivered APG-F67.3 package (R01 to R05, R10 to R12, with the history contract)', ['tools/run_regression_f674.py', '--static'], 'failed 0', None),
    ('The F-75 probe: type-changing edits break an approval, the owner approves afresh, a type-changed re-store is refused, on all five records', ['tools/probe_f674.py'], 'F-75 IS CORRECTED', None),
    ('unit tests: the F-67.4 type-strict tests', [T, '-q', 'test_f674_type_strict.py'], OK, 9),
    ('The F-74, F-73, F-72 and F-67 probes and tests and the M7 audit-findings probe still corrected (regression step R08)', ['tools/run_regression_f674.py', '--step', 'R08'], 'failed 0', None),
    ('The golden Builder Zero runs are unchanged (regression step R09)', ['tools/run_regression_f674.py', '--step', 'R09'], 'failed 0', None),
    ('The M2 store contracts', ['tools/run_contracts.py'], 'ALL CONTRACT CASES PASS', None),
    ('The M2 faulty implementations: each caught by the contract suite', ['tools/run_faults.py'], 'ALL FAULTS CAUGHT', None),
    ('The record-store guard contract (M7.3)', ['tools/run_guard_contract.py'], 'ALL GUARD CASES PASS', None),
    ('Mutation baseline (the unparsed modules pass every test the F-67.4 mutation run uses)', ['tools/f674_mutants.py', '--baseline'], 'BASELINE OK', None),
    ('The suite groups below, and the per-file list (--files-list), cover every test file in tests/ exactly once', None, None, None),
]
GROUPS = PRE + [(name, ['tools/run_test_files.py', '-q'] + files, OK, n) for name, files, n in SUITE]
WHOLE = 2583                                                         # the whole unit suite: groups 11 to 23 add up to this (the APG-F67.3 suite of 2,574 and the 9 F-67.4 tests)
FIRST, LAST = 11, 23
# APG-F67.4: the finest grain - every test file as its own group, with its test count (python3 -I tools/run_f674_all.py --files-list | --file N | --files A-B)
PER_FILE = [
    ('test_adversarial_builder_zero.py', 33),
    ('test_api_action_port_contract.py', 4),
    ('test_api_approval_boundary.py', 67),
    ('test_api_m92_corrections.py', 24),
    ('test_api_m93_corrections.py', 18),
    ('test_api_m94_corrections.py', 29),
    ('test_api_static.py', 7),
    ('test_det_approval_binding.py', 21),
    ('test_det_common.py', 10),
    ('test_det_contracts.py', 4),
    ('test_det_corpus.py', 6),
    ('test_det_detect.py', 22),
    ('test_det_findings.py', 39),
    ('test_det_findings_edges.py', 28),
    ('test_det_golden.py', 8),
    ('test_det_intake.py', 24),
    ('test_det_monitor.py', 13),
    ('test_det_noise.py', 14),
    ('test_det_policy.py', 19),
    ('test_det_policy_bounds.py', 6),
    ('test_det_portfolio.py', 23),
    ('test_det_proposal_binding.py', 47),
    ('test_det_proposal_identity.py', 29),
    ('test_det_rules_commercial.py', 41),
    ('test_det_rules_commercial_edges.py', 14),
    ('test_det_rules_cost.py', 51),
    ('test_det_rules_cost_edges.py', 8),
    ('test_det_rules_ops.py', 39),
    ('test_det_rules_ops_edges.py', 25),
    ('test_det_run_edges.py', 12),
    ('test_det_signal.py', 18),
    ('test_det_static.py', 14),
    ('test_det_transition_gate.py', 36),
    ('test_det_version_types.py', 34),
    ('test_f671_approval_recovery.py', 11),
    ('test_f672_forged_entry.py', 11),
    ('test_f673_approval_integrity.py', 12),
    ('test_f674_type_strict.py', 9),
    ('test_f67_policy_approval.py', 12),
    ('test_fin_arith.py', 24),
    ('test_fin_boundaries.py', 63),
    ('test_fin_bridge_book.py', 31),
    ('test_fin_cash.py', 45),
    ('test_fin_commitments.py', 19),
    ('test_fin_corpus.py', 4),
    ('test_fin_costs.py', 28),
    ('test_fin_forecast.py', 44),
    ('test_fin_golden.py', 7),
    ('test_fin_intake.py', 23),
    ('test_fin_records.py', 24),
    ('test_fin_revenue.py', 20),
    ('test_fin_static.py', 8),
    ('test_golden.py', 2),
    ('test_ingest_adversarial.py', 29),
    ('test_ingest_boundaries.py', 46),
    ('test_ingest_contracts.py', 12),
    ('test_ingest_golden.py', 4),
    ('test_ingest_mapping.py', 30),
    ('test_ingest_pipeline.py', 31),
    ('test_ingest_reconcile.py', 44),
    ('test_ingest_support.py', 28),
    ('test_materiality_engine.py', 45),
    ('test_mie_construction.py', 23),
    ('test_mie_core_adversarial.py', 4),
    ('test_mie_core_audit.py', 15),
    ('test_mie_core_boundaries.py', 33),
    ('test_mie_core_canon.py', 8),
    ('test_mie_core_m11_corrections.py', 10),
    ('test_mie_core_observations.py', 18),
    ('test_mie_core_pack.py', 37),
    ('test_mie_core_ports.py', 6),
    ('test_mie_core_replay.py', 9),
    ('test_mie_core_signals.py', 23),
    ('test_mie_core_static.py', 15),
    ('test_mie_core_tenancy.py', 8),
    ('test_mie_core_timing.py', 24),
    ('test_mie_flow.py', 7),
    ('test_mie_portability.py', 4),
    ('test_mkt_compare.py', 22),
    ('test_mkt_contracts.py', 5),
    ('test_mkt_corpus.py', 5),
    ('test_mkt_demand.py', 20),
    ('test_mkt_detect.py', 34),
    ('test_mkt_edges_base.py', 46),
    ('test_mkt_edges_demand.py', 22),
    ('test_mkt_edges_landed.py', 39),
    ('test_mkt_edges_policy.py', 52),
    ('test_mkt_edges_rules.py', 37),
    ('test_mkt_fx_fresh.py', 29),
    ('test_mkt_golden.py', 11),
    ('test_mkt_intake.py', 19),
    ('test_mkt_landed.py', 20),
    ('test_mkt_opportunities.py', 25),
    ('test_mkt_policy.py', 15),
    ('test_mkt_rules.py', 64),
    ('test_mkt_scenarios.py', 27),
    ('test_mkt_spec.py', 33),
    ('test_mkt_static.py', 19),
    ('test_rec_constraints.py', 16),
    ('test_rec_edges.py', 41),
    ('test_rec_eligibility.py', 20),
    ('test_rec_golden.py', 4),
    ('test_rec_isolation.py', 8),
    ('test_rec_lifecycle.py', 22),
    ('test_rec_m71_corrections.py', 23),
    ('test_rec_m72_race.py', 18),
    ('test_rec_m73_insert_race.py', 12),
    ('test_rec_money.py', 10),
    ('test_rec_policy.py', 9),
    ('test_rec_ranking.py', 11),
    ('test_rec_repro.py', 9),
    ('test_rec_verify.py', 13),
    ('test_repro.py', 23),
    ('test_source_authority.py', 40),
    ('test_status_model.py', 34),
    ('test_tenancy.py', 18),
    ('test_values.py', 11)
]


def coverage():
    have = sorted(f for f in os.listdir(os.path.join(ROOT, 'tests')) if f.startswith('test_') and f.endswith('.py'))
    listed = [f for _, files, _ in SUITE for f in files]
    dup = sorted({f for f in listed if listed.count(f) > 1})
    missing, extra = sorted(set(have) - set(listed)), sorted(set(listed) - set(have))
    per = [f for f, _ in PER_FILE]
    per_ok = sorted(per) == have and len(set(per)) == len(per) and sum(n for _, n in PER_FILE) == WHOLE   # APG-F67.4: the per-file list too
    ok = not dup and not missing and not extra and per_ok
    return ok, ('test files %d, listed once each in the groups and in the per-file list (%d tests)' % (len(have), WHOLE) if ok else
                'missing %r  extra %r  twice %r  per-file list complete and adding up: %s' % (missing, extra, dup, per_ok))


def per_file(want):
    """Run test files one at a time (each in its own interpreter, with its expected count)."""
    bad, total = [], 0
    for n in want:
        name, count = PER_FILE[n - 1]
        try:
            r = subprocess.run([sys.executable, '-I', 'tools/run_test_files.py', '-q', name], cwd=ROOT, capture_output=True, text=True, timeout=1800)
            out = r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            r, out = None, 'INCOMPLETE: cut off by the time limit'
        m = re.search(r'tests (\d+)  failures', out)
        ran = int(m.group(1)) if m else None
        ok = r is not None and r.returncode == 0 and OK in out and ran == count
        total += ran or 0
        print('%s file %d: %s | %s' % ('PASS' if ok else 'FAIL', n, name, ('tests %d (expected %d)' % (ran, count)) if ran is not None else (out.strip().splitlines() or [''])[-1]), flush=True)
        if not ok:
            bad.append(n)
    if want == list(range(1, len(PER_FILE) + 1)):
        print('whole suite file by file: %d tests in %d files (expected %d)%s' % (total, len(PER_FILE), WHOLE, '' if total == WHOLE else '  MISMATCH'))
        if total != WHOLE:
            bad.append('whole-suite count')
    print('files %d  failed %d%s' % (len(want), len(bad), ('  FAILED: %r' % bad) if bad else ''))
    return 0 if not bad else 1


def main():
    a = sys.argv[1:]
    if a and a[0] == '--files-list':
        for i, (name, n) in enumerate(PER_FILE, 1):
            print('%3d  %s [%d tests]    (python3 -I tools/run_test_files.py -q %s)' % (i, name, n, name))
        print('files 1 to %d together are the whole unit suite: %d tests (the sum of the counts above: %d)' % (len(PER_FILE), WHOLE, sum(n for _, n in PER_FILE)))
        return 0
    if a and a[0] == '--file':
        return per_file([int(a[1])])
    if a and a[0] == '--files':
        lo, hi = (int(x) for x in a[1].split('-'))
        return per_file(list(range(lo, hi + 1)))
    if not a or a[0] == '--list':
        for i, (name, cmd, _, n) in enumerate(GROUPS, 1):
            print('%2d  %s%s    (%s)' % (i, name, (' [%d tests]' % n) if n else '', ('python3 -I ' + ' '.join(cmd)) if cmd else 'built in'))
        print('groups %d to %d together are the whole unit suite: %d tests' % (FIRST, LAST, WHOLE))
        return 0
    if a[0] == '--group':
        want = [int(a[1])]
    elif a[0] == '--range':
        lo, hi = (int(x) for x in a[1].split('-'))
        want = list(range(lo, hi + 1))
    else:
        print(__doc__)
        return 2
    bad, total = [], 0
    for n in want:
        name, cmd, expect, count = GROUPS[n - 1]
        if cmd is None:
            ok, detail = coverage()
            ran = None
        else:
            try:
                r = subprocess.run([sys.executable, '-I'] + cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
                out = r.stdout + r.stderr
            except subprocess.TimeoutExpired:
                r, out = None, 'INCOMPLETE: cut off by the time limit'
            m = re.search(r'tests (\d+)  failures', out)
            ran = int(m.group(1)) if m else None
            ok = r is not None and r.returncode == 0 and expect in out and (count is None or ran == count)
            detail = ('tests %d' % ran) if ran is not None else (out.strip().splitlines() or [''])[-1]
        if FIRST <= n <= LAST and ran:
            total += ran
        print('%s group %d: %s | %s' % ('PASS' if ok else 'FAIL', n, name, detail), flush=True)
        if not ok:
            bad.append(n)
    if set(range(FIRST, LAST + 1)) <= set(want):
        print('whole suite: %d tests in groups %d to %d (expected %d)%s' % (total, FIRST, LAST, WHOLE, '' if total == WHOLE else '  MISMATCH'))
        if total != WHOLE:
            bad.append('whole-suite count')
    print('groups %d  failed %d%s' % (len(want), len(bad), ('  FAILED: %r' % bad) if bad else ''))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
