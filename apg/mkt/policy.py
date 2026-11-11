"""Procurement policy and specification register.  Blueprint: Section 08 sections 4.1 (comparability gate), 6 (tax treatment explicit; landed-cost components), 7.1 (decision-specific
freshness thresholds, recorded), 8 (scenarios use explicit price scenarios, never a universal rule), 12 (critical international checks), 16 ("define material specification normalisation and
comparability rules"; "implement quote validity, freshness and source-quality controls"); Section 06 section 5.1 (thresholds are configuration, never silently changed by AI).

TWO versioned, immutable records, each APPROVED only when a human holding the named role, who is not the proposer, has approved it through `approve_policy` or `approve_spec`, from
that person's own verified context, and the audit log confirms it (correction APG-F67, finding F-67; apg/policy_approval.py):

  mkt_policy   every threshold, window, basis table and scenario assumption a procurement rule needs.  NO DEFAULTS: a rule or analysis whose parameters are missing does not run and
               says which are missing (the run records `not_configured`); silence is never the answer.  Role: procurement_policy_owner.
  mkt_spec     the specification register: which attributes make up each material family, how each attribute is compared (exact, at least, at most), the catalogue specification of each material
               code, and the unit conversions a person has declared.  Role: specification_owner.  An unapproved register makes every comparison 'unverified'.

This module chooses no value.  Values in the demonstration policy (mkt/demo_mkt.py) are SYNTHETIC and ILLUSTRATIVE and are labelled as such."""
from .. import canon, policy_approval as PA

POLICY_KIND, SPEC_KIND = 'mkt_policy', 'mkt_spec'
POLICY_ROLE, SPEC_ROLE = 'procurement_policy_owner', 'specification_owner'
DECISIONS = ('quote_ranking', 'buy_timing', 'benchmark', 'import_costing')
COMPONENTS = ('freight', 'insurance', 'duty', 'clearance', 'handling')
TAX_TREATMENTS = ('ex_gst', 'inc_gst')
MATCH_MODES = ('exact', 'at_least', 'at_most')
CHECK_STATUSES = ('resolved', 'unresolved', 'not_applicable')


class MktPolicyError(ValueError):
    pass


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _nonneg(v):
    return _int(v) and v >= 0


def _pos(v):
    return _int(v) and v >= 1


def _bps(v):
    return _int(v) and 0 <= v <= 10000


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def _texts(v):
    return isinstance(v, list) and bool(v) and all(_text(x) for x in v) and len(set(v)) == len(v)


def _fresh(v):
    return isinstance(v, dict) and set(v) == {'quote_max_age_days', 'index_max_age_days', 'fx_max_age_days'} and all(_nonneg(x) for x in v.values())


def _price_tax(v):
    return isinstance(v, dict) and set(v) == {'supplier_quote', 'purchase_order'} and all(x in TAX_TREATMENTS for x in v.values())


def _bases(v):
    return isinstance(v, dict) and bool(v) and all(_text(k) and k == k.lower() and isinstance(e, dict) and set(e) == {'includes'} and isinstance(e['includes'], list)
                                                   and all(c in COMPONENTS for c in e['includes']) and len(set(e['includes'])) == len(e['includes']) for k, e in v.items())


def _required_components(v):
    return isinstance(v, dict) and set(v) == {'domestic', 'international'} and all(isinstance(x, list) and all(c in COMPONENTS for c in x) and len(set(x)) == len(x) for x in v.values())


def _paths(v):
    return isinstance(v, list) and bool(v) and all(isinstance(p, dict) and set(p) == {'name', 'change_bps', 'horizon_days'} and _text(p['name']) and _int(p['change_bps'])
                                                    and -10000 < p['change_bps'] <= 100000 and _nonneg(p['horizon_days']) for p in v) and len({p['name'] for p in v}) == len(v)


def _stage(v):
    return (isinstance(v, dict) and set(v) == {'splits_bps', 'offsets_days', 'extra_delivery_cents', 'admin_cents_per_order'} and isinstance(v['splits_bps'], list) and len(v['splits_bps']) >= 2
            and all(_pos(x) for x in v['splits_bps']) and sum(v['splits_bps']) == 10000 and isinstance(v['offsets_days'], list) and len(v['offsets_days']) == len(v['splits_bps'])
            and all(_nonneg(x) for x in v['offsets_days']) and v['offsets_days'] == sorted(v['offsets_days']) and _nonneg(v['extra_delivery_cents']) and _nonneg(v['admin_cents_per_order']))


# section -> parameter -> check.  A section or parameter that is absent is NOT defaulted.
SCHEMA = {
    'scope': {'watch_materials': lambda v: isinstance(v, list) and all(_text(x) for x in v) and len(set(v)) == len(v)},
    'freshness': {d: _fresh for d in DECISIONS},
    'basis': {'home_currency': _text, 'price_tax': _price_tax, 'gst_bps': _bps, 'delivery_bases': _bases, 'international_bases': lambda v: isinstance(v, list) and all(_text(x) and x == x.lower() for x in v),
              'required_components': _required_components, 'freight_currency': lambda v: v in ('aud', 'quote_currency')},
    'fx': {'method': lambda v: v == 'latest_on_or_before', 'convention': lambda v: v == 'foreign_per_aud', 'divergence_tolerance_bps': _nonneg},
    'demand': {'order_match_window_days': _pos, 'surplus_tolerance_bps': _nonneg, 'duplicate_window_days': _nonneg},
    'scenarios': {'decision_window_days': _nonneg, 'price_paths': _paths, 'financing_bps_pa': _bps, 'storage_cents_per_unit_per_day': _nonneg, 'lead_time_variation_days': _nonneg,
                  'stage': _stage, 'day_count_basis': lambda v: v in (360, 365), 'context_points': lambda v: _int(v) and v >= 2},
    'supplier': {'min_sample': _pos, 'min_acceptance_bps': _bps, 'min_fill_bps': _bps},
    'portfolio': {'window_days': _pos, 'min_projects': lambda v: _int(v) and v >= 2, 'rate_gap_bps': _pos},
    'international': {'critical_checks': _texts, 'checks': _texts},
    'savings': {'min_gap_bps': _pos},
}
OPTIONAL = {('basis', 'gst_bps')}                         # needed only when two price sources carry different tax treatments

# rule id -> (name, parameters that must be configured (section.parameter), what decision they stand for)
RULES = {
    'MP01': ('Market evidence stale, expired or unavailable for a material in scope (Section 08 7.1, 14)',
             ('scope.watch_materials', 'freshness.benchmark'), 'which materials are watched and how old benchmark evidence may be'),
    'MP02': ('Cheaper quote that fails the comparability gate (Section 08 4.1)',
             ('freshness.quote_ranking', 'freshness.benchmark', 'basis.home_currency', 'basis.price_tax', 'basis.delivery_bases', 'basis.international_bases', 'basis.required_components',
              'basis.freight_currency', 'fx.method', 'fx.convention', 'fx.divergence_tolerance_bps'), 'the basis on which prices are made comparable'),
    'MP03': ('Purchase decision due: uncovered demand with quotes and scenarios (Section 08 8)',
             ('freshness.buy_timing', 'scenarios.decision_window_days', 'basis.home_currency', 'basis.price_tax', 'basis.delivery_bases', 'basis.international_bases', 'basis.required_components',
              'basis.freight_currency', 'fx.method', 'fx.convention', 'fx.divergence_tolerance_bps', 'demand.order_match_window_days', 'demand.surplus_tolerance_bps'), 'how far ahead a purchase decision is flagged and the order-matching window'),
    'MP04': ('Ordered or delivered above the demand (Section 08 4, 13)', ('demand.order_match_window_days', 'demand.surplus_tolerance_bps'), 'matching window and surplus tolerance'),
    'MP05': ('Possible duplicate order (Section 08 4, 13)', ('demand.duplicate_window_days',), 'days within which identical orders are suspected duplicates'),
    'MP06': ('International quote converted at an old or diverging FX rate (Section 08 6, 12)',
             ('fx.method', 'fx.convention', 'fx.divergence_tolerance_bps', 'freshness.import_costing', 'basis.home_currency'), 'FX method, age limit and divergence tolerance'),
    'MP07': ('International quote with unresolved checks (Section 08 12)', ('international.critical_checks', 'international.checks', 'basis.home_currency', 'basis.international_bases'), 'which import and compliance checks are critical'),
    'MP08': ('Supplier performance below a configured level, with sample size (Section 08 9)', ('supplier.min_sample', 'supplier.min_acceptance_bps', 'supplier.min_fill_bps'), 'sample size and performance levels'),
    'MP09': ('Saving opportunity from a comparable quote (Section 08 11)',
             ('savings.min_gap_bps', 'freshness.quote_ranking', 'basis.home_currency', 'basis.price_tax', 'basis.delivery_bases', 'basis.international_bases', 'basis.required_components',
              'basis.freight_currency', 'fx.method', 'fx.convention', 'fx.divergence_tolerance_bps', 'demand.order_match_window_days', 'demand.surplus_tolerance_bps', 'freshness.benchmark'), 'the price gap that counts as an opportunity'),
    'MP10': ('Portfolio purchasing: the same material bought by several authorised projects (Section 08 3, 11)', ('portfolio.window_days', 'portfolio.min_projects', 'portfolio.rate_gap_bps'),
             'window, number of projects and rate gap'),
    'MPD1': ('Held procurement records that could not be used (Section 04)', (), 'no threshold'),
}
RULE_IDS = tuple(RULES)


def get_path(p, path):
    cur = p
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def validate_policy(p):
    bad = []
    if not isinstance(p, dict):
        return ['policy must be a dict']
    for k in p:
        if k not in ('version', 'proposer', 'approvals', 'note', 'rules') + tuple(SCHEMA):
            bad.append('unknown field ' + str(k))
    if not _text(p.get('version')):
        bad.append('version')
    if not _text(p.get('proposer')):
        bad.append('proposer')
    ap = p.get('approvals', [])
    if not isinstance(ap, list) or not all(isinstance(a, dict) and set(a) == {'approver', 'role', 'kind', 'date'} and all(_text(v) for v in a.values()) for a in ap):
        bad.append('approvals')
    for sec, params in SCHEMA.items():
        if sec not in p:
            continue
        if not isinstance(p[sec], dict):
            bad.append('section ' + sec)
            continue
        for k, v in p[sec].items():
            if k not in params or not params[k](v):
                bad.append(f'{sec}.{k}')
    rules = p.get('rules', {})
    if not isinstance(rules, dict):
        bad.append('rules')
    else:
        for rid, ent in rules.items():
            if rid not in RULES or not isinstance(ent, dict) or set(ent) - {'enabled'} or ('enabled' in ent and not isinstance(ent['enabled'], bool)):
                bad.append('rule ' + str(rid))
    return bad


def new_policy(version, proposer, **fields):
    """A policy as proposed: it never carries an approval (APG-F67)."""
    if 'approvals' in fields:
        raise MktPolicyError('a proposed policy carries no approval; approvals are recorded only through approve_policy by an authorised person')
    p = {'version': version, 'proposer': proposer, 'approvals': []}
    p.update(fields)
    bad = validate_policy(p)
    if bad:
        raise MktPolicyError('; '.join(bad))
    return canon.deep_copy(p)


def is_approved(p, role=POLICY_ROLE, confirmed=()):
    """A human holding `role`, not the proposer, approved this version AND the audit log confirms it (`confirmed`, pinned by the run)."""
    return PA.counted(p, role, confirmed)


def view(p, confirmed=()):
    q = canon.deep_copy(p)
    q['_approved'] = is_approved(p, POLICY_ROLE, confirmed)
    return q


def rule_params(p, rid):
    """-> (params dict, missing [dotted names]).  A missing parameter means the rule does not run.  `enabled: False` is a recorded switch-off, reported as such."""
    need = RULES[rid][1]
    missing = []
    out = {}
    for path in need:
        v = get_path(p, path)
        if v is None:
            missing.append(path)
        else:
            out[path] = canon.deep_copy(v)
    return (None, missing) if missing else (out, [])


def store_policy(scoped, p):
    """Store a PROPOSED procurement-policy version, as the person storing it, without approvals (APG-F67)."""
    return PA.store(scoped, POLICY_KIND, p, validate_policy, MktPolicyError, 'procurement policy')


def approve_policy(scoped, clock, version, rationale):
    """The only way a procurement-policy approval is recorded (APG-F67): a person holding 'procurement_policy_owner', not the proposer, from that person's own verified context;
    an audit event mkt_policy.approved is written, and a run counts the approval only when the log confirms it."""
    return PA.approve(scoped, clock, POLICY_KIND, POLICY_ROLE, version, rationale, MktPolicyError, 'procurement policy')


def approval_status(scoped, version):
    """APG-F67.1 (F-72): which approvals of this version are recorded in the policy, which the audit log confirms, and which are recorded but not confirmed (they do not count)."""
    return PA.status(scoped, POLICY_KIND, version)


# ---------------------------------------------------------------- specification register
def _attr_value(v):
    return (_int(v)) or _text(v)


def validate_spec(p):
    bad = []
    if not isinstance(p, dict):
        return ['register must be a dict']
    for k in p:
        if k not in ('version', 'proposer', 'approvals', 'note', 'families', 'materials', 'unit_conversions'):
            bad.append('unknown field ' + str(k))
    if not _text(p.get('version')):
        bad.append('version')
    if not _text(p.get('proposer')):
        bad.append('proposer')
    ap = p.get('approvals', [])
    if not isinstance(ap, list) or not all(isinstance(a, dict) and set(a) == {'approver', 'role', 'kind', 'date'} and all(_text(v) for v in a.values()) for a in ap):
        bad.append('approvals')
    fam = p.get('families')
    if not isinstance(fam, dict) or not fam:
        bad.append('families')
        fam = {}
    for f, ent in fam.items():
        if not _text(f) or not isinstance(ent, dict) or set(ent) != {'attributes'} or not isinstance(ent['attributes'], dict) or not ent['attributes']:
            bad.append('family ' + str(f))
            continue
        for a, rule in ent['attributes'].items():
            if not _text(a) or not isinstance(rule, dict) or set(rule) != {'match'} or rule['match'] not in MATCH_MODES:
                bad.append(f'family {f} attribute {a}')
    mats = p.get('materials')
    if not isinstance(mats, dict) or not mats:
        bad.append('materials')
        mats = {}
    for m, ent in mats.items():
        if not _text(m) or not isinstance(ent, dict) or set(ent) != {'family', 'attributes', 'unit'} or ent['family'] not in fam or not _text(ent['unit']) or not isinstance(ent['attributes'], dict):
            bad.append('material ' + str(m))
            continue
        for a, v in ent['attributes'].items():
            rule = fam[ent['family']]['attributes'].get(a)
            if rule is None or not _attr_value(v) or (rule['match'] != 'exact' and not _int(v)):
                bad.append(f'material {m} attribute {a}')
    conv = p.get('unit_conversions', [])
    if not isinstance(conv, list) or not all(isinstance(c, dict) and set(c) == {'material', 'from_unit', 'to_unit', 'factor_micro'} and _text(c['material']) and _text(c['from_unit'])
                                              and _text(c['to_unit']) and _pos(c['factor_micro']) for c in conv):
        bad.append('unit_conversions')
    return bad


def new_spec(version, proposer, **fields):
    """A register as proposed: it never carries an approval (APG-F67)."""
    if 'approvals' in fields:
        raise MktPolicyError('a proposed specification register carries no approval; approvals are recorded only through approve_spec by an authorised person')
    p = {'version': version, 'proposer': proposer, 'approvals': []}
    p.update(fields)
    bad = validate_spec(p)
    if bad:
        raise MktPolicyError('; '.join(bad))
    return canon.deep_copy(p)


def spec_view(p, confirmed=()):
    q = canon.deep_copy(p)
    q['_approved'] = is_approved(p, SPEC_ROLE, confirmed)
    return q


def store_spec(scoped, p):
    """Store a PROPOSED specification-register version, as the person storing it, without approvals (APG-F67)."""
    return PA.store(scoped, SPEC_KIND, p, validate_spec, MktPolicyError, 'specification register')


def approve_spec(scoped, clock, version, rationale):
    """The only way a specification-register approval is recorded (APG-F67): a person holding 'specification_owner', not the proposer, from that person's own verified context;
    an audit event mkt_spec.approved is written, and a run counts the approval only when the log confirms it."""
    return PA.approve(scoped, clock, SPEC_KIND, SPEC_ROLE, version, rationale, MktPolicyError, 'specification register')


def spec_approval_status(scoped, version):
    """APG-F67.1 (F-72): which approvals of this version are recorded in the register, which the audit log confirms, and which are recorded but not confirmed (they do not count)."""
    return PA.status(scoped, SPEC_KIND, version)

