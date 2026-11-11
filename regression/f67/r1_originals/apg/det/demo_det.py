"""Demonstration set-up for the detection layer on Builder Zero (Blueprint Section 06 section 5.1: every threshold is configuration).  EVERYTHING HERE IS SYNTHETIC OR ILLUSTRATIVE.  The thresholds below are NOT approved for any real builder and
are NOT product-owner decisions.  Where a value comes from the Builder Zero file builder_zero/scenarios/test_thresholds.json it is marked `test_thresholds.json`; every other
value is the builder's own illustrative choice, marked `builder`.  Real values come from a policy owner's approval and from the pilot."""
from . import intake as DI, policy as DP
from ..fin import demo_fin as DF, policy as FP

ILLUSTRATIVE_NOTE = 'SYNTHETIC / ILLUSTRATIVE detection policy - not a product decision'
AS_OF = '2026-09-30'

ORIGIN = {
    'R01.tolerance_bps': 'test_thresholds.json (budget_tolerance_bps 500)', 'R03.tolerance_bps': 'test_thresholds.json (invoice_vs_po_tolerance_bps 100)',
    'R04.unresolved_days': 'test_thresholds.json (variation_unresolved_days 60)', 'R06.warning_days': 'test_thresholds.json (insurance_expiry_warning_days 30)',
    'AGG.window_days': 'test_thresholds.json (aggregation_window_days 30)', 'AGG.single_order_abs_cents': 'test_thresholds.json (single_order_materiality_abs_cents 25000000)',
    'AGG.keys': 'builder (test_thresholds.json says ["project"]; that key alone marks 96 of 101 orders material, finding F-01 and F-23)',
    'R04B.min_age_days': 'builder', 'R04B.instruction_types': 'builder', 'R05.grace_days': 'builder', 'R07.tolerance_bps': 'builder', 'R07.pairs': 'builder (a person declares comparability)',
    'R08.min_excess_days': 'builder', 'R09.movement_abs_cents': 'builder', 'DLY.min_overlap_days': 'builder', 'LAB.baseline_weeks': 'builder', 'LAB.recent_weeks': 'builder',
    'LAB.decline_bps': 'builder', 'DEF.min_events': 'builder', 'severity_bands': 'builder', 'noise': 'builder'}


def demo_det_policy(version='SYN-DET-POL-1', approved=True, **override):
    fields = dict(
        rules={'R01': {'tolerance_bps': 500}, 'R02': {}, 'R03': {'tolerance_bps': 100}, 'R04': {'unresolved_days': 60}, 'R04B': {'min_age_days': 30, 'instruction_types': ['client_instruction']},
               'R05': {'grace_days': 0}, 'R06': {'warning_days': 30},
               'R07': {'tolerance_bps': 100, 'pairs': [{'quote': 'Q-0001', 'reference_kind': 'quote', 'reference': 'Q-0002'}]},
               'R08': {'min_excess_days': 7}, 'R09': {'movement_abs_cents': 5000000},
               'AGG': {'keys': ['project', 'supplier', 'material', 'cost_code'], 'window_days': 30, 'single_order_abs_cents': 25000000},
               'DLY': {'min_overlap_days': 1}, 'LAB': {'baseline_weeks': 8, 'recent_weeks': 4, 'decline_bps': 1000}, 'DEF': {'min_events': 3}},
        severity_bands=[{'min_cents': 0, 'label': 'low'}, {'min_cents': 5000000, 'label': 'medium'}, {'min_cents': 25000000, 'label': 'high'}],
        noise={'suppression_days': 7, 'renotify_on': ['severity_increase', 'status_transition', 'material_evidence']},
        note=ILLUSTRATIVE_NOTE)
    fields.update(override)
    p = DP.new_policy(version, 'synthetic.proposer', **fields)
    if approved:
        p = DP.approve(p, 'synthetic.det_policy_owner', DP.POLICY_ROLE, 'human', AS_OF)
    return p


def load_det(root, scoped, clock, tenant='zero_one'):
    out = {}
    for t, data, src, name, rev in DI.det_files(root, tenant):
        out[name] = DI.ingest_det_file(scoped, clock, t, data, src, name, None, rev)
    return out


def load_zero_all(root, scoped, clock, tenant='zero_one', register=None, as_of=AS_OF, approved=True):
    """M3 + M4 + M5 files for one Builder Zero tenant, reconciled, with the demonstration financial and detection policies stored.  -> (receipts, fin policy version, det policy version)."""
    receipts = DF.load_zero(root, scoped, clock, tenant, register, as_of)
    receipts.update(load_det(root, scoped, clock, tenant))
    fp = DF.demo_policy(approved=approved)
    FP.store_policy(scoped, fp)
    dp = demo_det_policy(approved=approved)
    DP.store_policy(scoped, dp)
    return receipts, fp['version'], dp['version']
