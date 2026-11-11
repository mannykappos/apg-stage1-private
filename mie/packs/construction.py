"""The APG construction pack (MIE1_SPEC section 11; MIE-R-49 to MIE-R-52).  The first field pack: it lets the universal core speak about construction materials, using the
vocabulary M6 already uses (material identity, units, geography, the source and kind of a market observation, currency pairs).

  * BUY only.  A builder buys materials for a job; SELL is refused by the core (INTENTION_NOT_ALLOWED) and no sell-side outcome can be produced.
  * CONTEXT_ONLY.  Until the product owner decides the Section 08 change request (MIE1_DRAFT_CHANGE_REQUEST_S08.md, unnumbered and unapproved), no rule may use a market signal:
    signals are shown beside the outcome as context, and the signal-influence class of every outcome is NONE.
  * Structure only from the author.  base_pack() carries no tracked material, threshold, freshness limit, parameter value, licence grant or decision rule.  It is INCOMPLETE:
    activated as it stands, every assessment is NOT_ASSESSED with the missing items listed.  The owner's inputs make a new, complete pack version (complete()); the author invents
    none of them.  owner_inputs_from_m6_policy() shows how the values a tenant's M6 procurement policy already holds map onto the pack (its watched materials and its buy-timing
    freshness limits); everything M6 does not hold stays null until the owner supplies it.
  * Isolation gate (MIE-R-51): nothing in APG imports the core or this pack; no finding or recommendation consumes a signal.  Landed cost stays in M6 (no hook is bound)."""
from mie.core import canon

PACK_ID = 'APG-CONSTRUCTION'
M6_KIND_MAP = {'index': ('HISTORICAL_MOVEMENT', 'INDEX')}          # M6 kind_text -> core observation class and value basis (derived from apg/mkt/fresh.py index_state)
FX_CLASS = ('CURRENT_REFERENCE', 'INDEX')                           # an M6 fx_rate is a reference rate used as the latest on or before a date (apg/mkt/fx.py)
NOT_NAMED = 'POLICY-OWNER-NOT-YET-NAMED'


def base_pack(version='0.1.0'):
    """Structure only (section 11).  Nothing here is a value the author chose for the owner."""
    return {
        'pack_schema': 'mie-pack-1',
        'pack_id': PACK_ID,
        'pack_version': version,
        'field_label': 'Construction materials (Anchor Profit Guardian)',
        'core_compat': ['mie-core-1.0.0'],
        'allowed_intentions': ['BUY'],
        'decision_profile': 'CONTEXT_ONLY',
        'vocabulary': {'subject_kinds': ['material', 'currency_pair'], 'subjects': [], 'units': [], 'markets': []},
        'aliases': [],
        'comparison_groups': [],
        'sources': [],
        'licences': [],
        'event_mapping': [],
        'conversions': [],
        'signals': [],
        'parameters': [],
        'freshness_limits': [],
        'required_evidence': [],
        'decision_table': None,
        'hooks': [],
        'provenance': {'author_ref': 'APG builder (structure only)', 'owner_ref': NOT_NAMED, 'synthetic': False},
    }


def complete(base, inputs, version):
    """A new pack version from the owner's inputs.  inputs keys (each optional, each the owner's): subjects (list of material ids), units, markets, sources, licences,
    conversions (list of {pair, rate_unit, market, from_unit, to_unit}), movement (dict of window_days, min_points, movement_basis, threshold or None),
    conversion_movement (the same), parameters, freshness_limits, required_evidence, decision_table, owner_ref."""
    doc = canon.copy(base)
    doc['pack_version'] = version
    conv = []
    subjects = []
    for c in inputs.get('conversions', []):
        cid = 'FX:' + c['pair']
        conv.append({'conversion_id': cid, 'subject_id': cid, 'from_unit': c['from_unit'], 'to_unit': c['to_unit'], 'rate_unit': c['rate_unit'], 'market': c['market']})
        subjects.append({'subject_id': cid, 'kind': 'currency_pair', 'conversions': []})
    for m in inputs.get('subjects', []):
        subjects.append({'subject_id': m, 'kind': 'material', 'conversions': [c['conversion_id'] for c in conv]})
    doc['vocabulary']['subjects'] = sorted(subjects, key=lambda s: s['subject_id'])
    doc['vocabulary']['units'] = inputs.get('units', [])
    doc['vocabulary']['markets'] = inputs.get('markets', [])
    doc['conversions'] = conv
    doc['sources'] = inputs.get('sources', [])
    doc['licences'] = inputs.get('licences', [])
    owner = inputs.get('owner_ref', NOT_NAMED)
    sig = []
    if 'movement' in inputs:
        sig.append({'signal_id': 'APG-INDEX-MOVEMENT', 'type': 'LEVEL_MOVEMENT', 'selector': {'observation_class': 'HISTORICAL_MOVEMENT', 'value_basis': 'INDEX'},
                    'params': dict({'window_days': None, 'min_points': None, 'movement_basis': None, 'threshold': None}, **inputs['movement']), 'parameter_owner_ref': owner})
    if 'conversion_movement' in inputs:
        for c in conv:
            sig.append({'signal_id': 'APG-FX-MOVEMENT-' + c['conversion_id'][3:].replace('/', '-'), 'type': 'CONVERSION_MOVEMENT', 'selector': {'conversion_id': c['conversion_id']},
                        'params': dict({'window_days': None, 'min_points': None, 'movement_basis': None, 'threshold': None}, **inputs['conversion_movement']),
                        'parameter_owner_ref': owner})
    doc['signals'] = sig
    doc['parameters'] = inputs.get('parameters', [])
    doc['freshness_limits'] = inputs.get('freshness_limits', [])
    doc['required_evidence'] = inputs.get('required_evidence', [])
    doc['decision_table'] = inputs.get('decision_table')
    doc['provenance'] = dict(doc['provenance'], owner_ref=owner)
    return doc


def owner_inputs_from_m6_policy(policy, owner_ref):
    """The part of the owner's inputs that the tenant's M6 procurement policy (mkt_policy) already holds: the watched materials (scope.watch_materials) and the buy-timing
    freshness limits (freshness.buy_timing index_max_age_days and fx_max_age_days).  Nothing else is taken, and nothing is invented: movement parameters, licences, units,
    markets, sources and the decision table stay for the owner to supply."""
    bt = policy['freshness']['buy_timing']
    return {'subjects': list(policy['scope']['watch_materials']),
            'freshness_limits': [{'observation_class': 'HISTORICAL_MOVEMENT', 'days': bt['index_max_age_days'], 'owner_ref': owner_ref + ' (M6 buy_timing index_max_age_days)'},
                                 {'observation_class': 'CURRENT_REFERENCE', 'days': bt['fx_max_age_days'], 'owner_ref': owner_ref + ' (M6 buy_timing fx_max_age_days)'}],
            'owner_ref': owner_ref}


def pack_bytes(doc):
    return canon.dumps(doc)
