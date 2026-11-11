"""Demonstration set-up for the procurement layer on Builder Zero (Blueprint Section 08; Section 06 section 5.1: every threshold is configuration).  EVERYTHING HERE IS SYNTHETIC OR ILLUSTRATIVE.  Nothing
below is approved for any real builder or is a product-owner decision.  Every value is the builder's own illustrative choice (`builder`); real values come from a procurement policy owner's approval and
from the pilot.  The specification register is likewise a demonstration: a real register is the specification owner's."""
from . import intake as MI, policy as MP
from ..det import demo_det as DD

ILLUSTRATIVE_NOTE = 'SYNTHETIC / ILLUSTRATIVE procurement policy - not a product decision'
SPEC_NOTE = 'SYNTHETIC / ILLUSTRATIVE specification register - not a specification owner decision'
AS_OF = DD.AS_OF
OWNER_ROLES = DD.OWNER_ROLES + (MP.POLICY_ROLE, MP.SPEC_ROLE)                 # the demonstration owner's roles (APG-F67); the session is the caller's
DEMO_OWNER = DD.DEMO_OWNER
POLICY_APPROVER, SPEC_APPROVER = 'synthetic.procurement_policy_owner', 'synthetic.specification_owner_approver'

ORIGIN = {k: 'builder (illustrative)' for k in (
    'scope.watch_materials', 'freshness.*', 'basis.*', 'fx.divergence_tolerance_bps', 'demand.order_match_window_days', 'demand.surplus_tolerance_bps', 'demand.duplicate_window_days',
    'scenarios.*', 'supplier.*', 'portfolio.*', 'international.*', 'savings.min_gap_bps')}


def demo_mkt_fields():
    return dict(
        scope={'watch_materials': ['MAT-CU', 'MAT-PBOARD', 'MAT-REO', 'MAT-STEEL']},
        freshness={'quote_ranking': {'quote_max_age_days': 45, 'index_max_age_days': 45, 'fx_max_age_days': 30},
                   'buy_timing': {'quote_max_age_days': 30, 'index_max_age_days': 45, 'fx_max_age_days': 14},
                   'benchmark': {'quote_max_age_days': 90, 'index_max_age_days': 45, 'fx_max_age_days': 45},
                   'import_costing': {'quote_max_age_days': 45, 'index_max_age_days': 45, 'fx_max_age_days': 30}},
        basis={'home_currency': 'AUD', 'price_tax': {'supplier_quote': 'ex_gst', 'purchase_order': 'ex_gst'},
               'delivery_bases': {'delivered': {'includes': ['freight', 'handling']}, 'ex-works': {'includes': []}, 'fob': {'includes': []}},
               'international_bases': ['fob', 'cif'], 'required_components': {'domestic': ['freight'], 'international': ['freight', 'insurance', 'duty', 'clearance']},
               'freight_currency': 'quote_currency'},
        fx={'method': 'latest_on_or_before', 'convention': 'foreign_per_aud', 'divergence_tolerance_bps': 100},
        demand={'order_match_window_days': 180, 'surplus_tolerance_bps': 500, 'duplicate_window_days': 0},
        scenarios={'decision_window_days': 45, 'price_paths': [{'name': 'flat', 'change_bps': 0, 'horizon_days': 30}, {'name': 'down_5pct', 'change_bps': -500, 'horizon_days': 30},
                                                               {'name': 'up_5pct', 'change_bps': 500, 'horizon_days': 30}],
                   'financing_bps_pa': 800, 'storage_cents_per_unit_per_day': 50, 'lead_time_variation_days': 7,
                   'stage': {'splits_bps': [5000, 5000], 'offsets_days': [0, 30], 'extra_delivery_cents': 25000, 'admin_cents_per_order': 5000}, 'day_count_basis': 365, 'context_points': 4},
        supplier={'min_sample': 3, 'min_acceptance_bps': 9500, 'min_fill_bps': 9500},
        portfolio={'window_days': 365, 'min_projects': 2, 'rate_gap_bps': 500},
        international={'critical_checks': ['customs_classification', 'duty_rate_confirmed', 'import_permit'], 'checks': ['customs_classification', 'duty_rate_confirmed', 'import_permit', 'supplier_vetting']},
        savings={'min_gap_bps': 300},
        note=ILLUSTRATIVE_NOTE)


def demo_mkt_policy(version='SYN-MKT-POL-1', proposer='synthetic.proposer', **override):
    """The demonstration procurement policy as PROPOSED (APG-F67: no approval; `install_mkt` stores it and has the owner approve it in person)."""
    fields = demo_mkt_fields()
    fields.update(override)
    return MP.new_policy(version, proposer, **fields)


def demo_mkt_spec(version='SYN-MKT-SPEC-1', proposer='synthetic.spec_proposer', **override):
    """The demonstration specification register as PROPOSED (APG-F67: no approval; `install_spec` stores it and has the owner approve it in person)."""
    fields = dict(
        families={'concrete': {'attributes': {'strength_mpa': {'match': 'at_least'}}},
                  'steel_section': {'attributes': {'grade': {'match': 'exact'}, 'section': {'match': 'exact'}}},
                  'plasterboard': {'attributes': {'thickness_mm': {'match': 'exact'}}},
                  'reinforcing_bar': {'attributes': {'bar_size': {'match': 'exact'}}},
                  'copper_pipe': {'attributes': {'diameter_mm': {'match': 'exact'}}}},
        materials={'MAT-CONC40': {'family': 'concrete', 'attributes': {'strength_mpa': 40}, 'unit': 'm3'},
                   'MAT-CONC32': {'family': 'concrete', 'attributes': {'strength_mpa': 32}, 'unit': 'm3'},
                   'MAT-STEEL': {'family': 'steel_section', 'attributes': {'grade': '300PLUS', 'section': '250UB'}, 'unit': 'tonne'},
                   'MAT-PBOARD': {'family': 'plasterboard', 'attributes': {'thickness_mm': '13'}, 'unit': 'sheet'},
                   'MAT-REO': {'family': 'reinforcing_bar', 'attributes': {'bar_size': 'N16'}, 'unit': 'tonne'},
                   'MAT-CU': {'family': 'copper_pipe', 'attributes': {'diameter_mm': '22'}, 'unit': 'metre'}},
        unit_conversions=[], note=SPEC_NOTE)
    fields.update(override)
    return MP.new_spec(version, proposer, **fields)


def install_mkt(scoped, clock, owner=None, version='SYN-MKT-POL-1', **override):
    """Store the demonstration procurement policy proposed by the person of `scoped` and, with the owner's own session, approve it from that session (APG-F67).  -> the payload."""
    MP.store_policy(scoped, demo_mkt_policy(version, scoped.ctx.user_id, **override))
    if owner is not None:
        return MP.approve_policy(owner, clock, version, 'SYNTHETIC demonstration: approved by the demonstration owner in person')
    return scoped.get(MP.POLICY_KIND, version).payload


def install_spec(scoped, clock, owner=None, version='SYN-MKT-SPEC-1', **override):
    """Store the demonstration specification register proposed by the person of `scoped` and, with the owner's own session, approve it from that session (APG-F67)."""
    MP.store_spec(scoped, demo_mkt_spec(version, scoped.ctx.user_id, **override))
    if owner is not None:
        return MP.approve_spec(owner, clock, version, 'SYNTHETIC demonstration: approved by the demonstration owner in person')
    return scoped.get(MP.SPEC_KIND, version).payload


def load_mkt(root, scoped, clock, tenant='zero_one'):
    out = {}
    for t, data, src, name, rev in MI.mkt_files(root, tenant):
        out[name] = MI.ingest_mkt_file(scoped, clock, t, data, src, name, None, rev)
    return out


def load_mkt_all(root, scoped, clock, tenant='zero_one', register=None, as_of=AS_OF, owner=None):
    """M3 + M4 + M5 + M6 files for one Builder Zero tenant, reconciled, with the demonstration financial, detection, procurement policies and specification register stored as
    proposed by the person of `scoped` and approved by `owner` in person when the owner's session is given (APG-F67; without it they stay unapproved).
    -> (receipts, fin policy version, det policy version, mkt policy version, mkt spec version)."""
    receipts, fv, dv = DD.load_zero_all(root, scoped, clock, tenant, register, as_of, owner)
    receipts.update(load_mkt(root, scoped, clock, tenant))
    mp, sp = install_mkt(scoped, clock, owner), install_spec(scoped, clock, owner)
    return receipts, fv, dv, mp['version'], sp['version']
