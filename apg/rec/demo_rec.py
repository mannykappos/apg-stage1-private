"""The DEMONSTRATION recommendation policy (the configuration of Section 10 sections 3, 4, 5, 7 and 9 and Section 05 section 10.1).  Every value here is SYNTHETIC and ILLUSTRATIVE: the builder's own choice, made so that the engine can be run and tested end to end.  None is a
recommendation to a builder and none is approved by the product owner.  A real policy is written, proposed and approved by people (rec/policy.py); nothing in apg/rec falls back to these values.  The policy is returned as proposed and unapproved: in a test or demonstration a policy owner
session approves it through policy.approve_policy, like any other policy."""
from . import policy as RP

NOTE = 'SYNTHETIC demonstration policy (builder-chosen illustrative values; not approved by the product owner)'


def demo_rec_policy(version='SYN-REC-POL-1', proposer='builder-demo-proposer', **override):
    fields = dict(
        eligibility={'stale_after_days': 30, 'min_strength_for_action': 'moderate', 'due_soon_days': 14},
        categories={'actual_loss': 'recover', 'forecast_exposure': 'prevent', 'potential_opportunity': 'optimise', 'potential_revenue_at_risk': 'recover',
                    'cash_timing_exposure': 'correct', 'compliance_risk': 'correct', 'operational_risk': 'prevent'},
        mandatory_reviews={'quality_defects': ['quality'], 'suppliers_compliance': ['legal'], 'schedule_holding': ['contractual'], 'commercial_revenue': ['contractual'],
                           'procurement_materials': ['quality']},
        approval_bands=[{'min_cents': 0, 'role': 'project_manager'}, {'min_cents': 2000000, 'role': 'commercial_manager'}, {'min_cents': 10000000, 'role': 'director'}],
        rank_order=['actionability', 'time_sensitivity', 'urgency', 'confidence', 'net_benefit', 'magnitude'],
        scenario_required_above_cents=1000000,
        verification={'offset_components': ['implementation_labour', 'freight_and_handling', 'storage_and_waste', 'financing', 'switching_and_qualification', 'rework_and_delay']},
        note=NOTE)
    for k, v in override.items():
        if v is None:
            fields.pop(k, None)
        else:
            fields[k] = v
    return RP.new_policy(version, proposer, **fields)      # unapproved: an approval is recorded only through policy.approve_policy by a policy owner's own session (APG-M7.1, F-66)
