"""The synthetic portability pack (MIE1_SPEC section 12; MIE-R-53, MIE-R-54).  Field label "TEST FIELD (SYNTHETIC)".  Invented identifiers, BUY and SELL, the SIGNAL_RULES
profile so that the rule machinery is exercised.  It names no vendor, uses no real data, makes no claim about any market, and has no field-specific function.  EVERY value in
it is a TEST-ONLY fixture value chosen by the author for the tests; none is guidance.  It exists only to show that a second field runs on the same core unchanged."""
from mie.core import canon

TEST_ONLY = 'TEST-ONLY'


def pack(version='1.0.0', **override):
    doc = {
        'pack_schema': 'mie-pack-1',
        'pack_id': 'SYN-TEST-FIELD',
        'pack_version': version,
        'field_label': 'TEST FIELD (SYNTHETIC)',
        'core_compat': ['mie-core-1.0.0'],
        'allowed_intentions': ['BUY', 'SELL'],
        'decision_profile': 'SIGNAL_RULES',
        'vocabulary': {
            'subject_kinds': ['SYN-KIND-ITEM', 'SYN-KIND-RATE'],
            'subjects': [{'subject_id': 'SYN-ITEM-A', 'kind': 'SYN-KIND-ITEM', 'conversions': ['SYN-CONV-1']},
                         {'subject_id': 'SYN-ITEM-B', 'kind': 'SYN-KIND-ITEM', 'conversions': []},
                         {'subject_id': 'SYN-RATE-1', 'kind': 'SYN-KIND-RATE', 'conversions': []}],
            'units': [{'unit_id': 'SYN-UNIT', 'decimal_scale': 2, 'value_domain': 'POSITIVE'},
                      {'unit_id': 'SYN-UNIT-2', 'decimal_scale': 2, 'value_domain': 'POSITIVE'},
                      {'unit_id': 'SYN-SIGNED', 'decimal_scale': 0, 'value_domain': 'SIGNED'},
                      {'unit_id': 'SYN-COUNT', 'decimal_scale': 0, 'value_domain': 'NON_NEGATIVE'},
                      {'unit_id': 'SYN-RATE-UNIT', 'decimal_scale': 4, 'value_domain': 'POSITIVE'}],
            'markets': ['SYN-MARKET-1', 'SYN-MARKET-2'],
        },
        'aliases': [{'alias': 'SYN-ITEM-A-ALT', 'canonical': 'SYN-ITEM-A'}],
        'comparison_groups': [{'group_id': 'SYN-GROUP-ASK', 'subject_id': 'SYN-ITEM-A', 'unit': 'SYN-UNIT', 'market': 'SYN-MARKET-1',
                               'observation_class': 'CURRENT_REFERENCE', 'value_basis': 'ASKING', 'sources': ['SYN-SRC-1', 'SYN-SRC-2']}],
        'sources': [{'source_id': 'SYN-SRC-1', 'licence_ref': 'SYN-LIC-1', 'value_bases': ['INDEX', 'ASKING', 'OFFER', 'COMPLETED_TRANSACTION']},
                    {'source_id': 'SYN-SRC-2', 'licence_ref': 'SYN-LIC-1', 'value_bases': ['ASKING', 'OFFER']},
                    {'source_id': 'SYN-SRC-U', 'licence_ref': 'SYN-LIC-2', 'value_bases': ['INDEX']},
                    {'source_id': 'SYN-SRC-K', 'licence_ref': 'SYN-LIC-3', 'value_bases': ['INDEX']},
                    {'source_id': 'SYN-SRC-W', 'licence_ref': 'SYN-LIC-4', 'value_bases': ['INDEX']}],
        'licences': [{'licence_id': 'SYN-LIC-1', 'status': 'LICENSED', 'valid_from': '2020-01-01', 'valid_to': '2030-12-31', 'terms_ref': 'TEST-ONLY synthetic terms'},
                     {'licence_id': 'SYN-LIC-2', 'status': 'UNLICENSED', 'valid_from': '2020-01-01', 'valid_to': '2030-12-31', 'terms_ref': 'TEST-ONLY synthetic terms'},
                     {'licence_id': 'SYN-LIC-3', 'status': 'UNKNOWN', 'valid_from': '2020-01-01', 'valid_to': '2030-12-31', 'terms_ref': 'TEST-ONLY synthetic terms'},
                     {'licence_id': 'SYN-LIC-4', 'status': 'LICENSED', 'valid_from': '2020-01-01', 'valid_to': '2026-06-30', 'terms_ref': 'TEST-ONLY synthetic terms'}],
        'event_mapping': [{'label': 'SYN-AVAIL-DOWN', 'event_class': 'AVAILABILITY_CHANGED', 'availability': 'DECREASED'},
                          {'label': 'SYN-AVAIL-UP', 'event_class': 'AVAILABILITY_CHANGED', 'availability': 'INCREASED'},
                          {'label': 'SYN-VARIANT-NEW', 'event_class': 'VARIANT_INTRODUCED', 'availability': None},
                          {'label': 'SYN-VARIANT-END', 'event_class': 'VARIANT_WITHDRAWN', 'availability': None}],
        'conversions': [{'conversion_id': 'SYN-CONV-1', 'subject_id': 'SYN-RATE-1', 'from_unit': 'SYN-UNIT', 'to_unit': 'SYN-UNIT-2', 'rate_unit': 'SYN-RATE-UNIT',
                         'market': 'SYN-MARKET-1'}],
        'signals': [{'signal_id': 'SYN-SIG-LEVEL', 'type': 'LEVEL_MOVEMENT',
                     'selector': {'observation_class': 'HISTORICAL_MOVEMENT', 'value_basis': 'INDEX', 'market': 'SYN-MARKET-1', 'unit': 'SYN-UNIT'},
                     'params': {'window_days': 90, 'min_points': 2, 'movement_basis': 'RELATIVE', 'threshold': {'num': 1, 'den': 20}},
                     'parameter_owner_ref': 'TEST-ONLY owner'},
                    {'signal_id': 'SYN-SIG-CONV', 'type': 'CONVERSION_MOVEMENT', 'selector': {'conversion_id': 'SYN-CONV-1'},
                     'params': {'window_days': 90, 'min_points': 2, 'movement_basis': 'RELATIVE', 'threshold': {'num': 1, 'den': 50}},
                     'parameter_owner_ref': 'TEST-ONLY owner'},
                    {'signal_id': 'SYN-SIG-AVAIL', 'type': 'AVAILABILITY_CHANGE', 'selector': {}, 'params': {'lookback_days': 30}, 'parameter_owner_ref': 'TEST-ONLY owner'},
                    {'signal_id': 'SYN-SIG-NEW', 'type': 'VARIANT_INTRODUCED', 'selector': {}, 'params': {'lookback_days': 60}, 'parameter_owner_ref': 'TEST-ONLY owner'},
                    {'signal_id': 'SYN-SIG-END', 'type': 'VARIANT_WITHDRAWN', 'selector': {}, 'params': {'lookback_days': 60}, 'parameter_owner_ref': 'TEST-ONLY owner'}],
        'parameters': [{'param_id': 'SYN-P-SOON', 'value': 3, 'owner_ref': 'TEST-ONLY owner'},
                       {'param_id': 'SYN-P-LEAD', 'value': 14, 'owner_ref': 'TEST-ONLY owner'}],
        'freshness_limits': [{'observation_class': 'HISTORICAL_MOVEMENT', 'days': 45, 'owner_ref': 'TEST-ONLY owner'},
                             {'observation_class': 'CURRENT_REFERENCE', 'days': 7, 'owner_ref': 'TEST-ONLY owner'}],
        'required_evidence': [{'evidence_id': 'SYN-REQ-HIST', 'observation_class': 'HISTORICAL_MOVEMENT', 'value_basis': 'INDEX', 'market': 'SYN-MARKET-1',
                               'unit': 'SYN-UNIT'}],
        'decision_table': [
            {'rule_id': 'SYN-R-BUY-SOON', 'intention': 'BUY', 'outcome': 'ACT_NOW', 'rationale_code': 'NEED-BY-SOON', 'basis_class': 'OBSERVED_EVIDENCE_ONLY',
             'predicates': [{'p': 'CONSTRAINT_COMPARE', 'constraint': 'days_to_need_by', 'comparison': 'LE', 'param': 'SYN-P-SOON', 'negate': False}]},
            {'rule_id': 'SYN-R-BUY-DOWN', 'intention': 'BUY', 'outcome': 'WAIT', 'rationale_code': 'LEVEL-DOWN-TIME-LEFT', 'basis_class': 'OWNER_ASSUMPTION',
             'owner_ref': 'TEST-ONLY owner', 'assumption': 'TEST-ONLY: the owner assumes waiting is acceptable after an observed fall when time remains',
             'predicates': [{'p': 'SIGNAL_PRESENT', 'type': 'LEVEL_MOVEMENT', 'evidence_class': 'HISTORICAL_MOVEMENT', 'direction': 'DOWN', 'negate': False},
                            {'p': 'CONSTRAINT_COMPARE', 'constraint': 'days_to_need_by', 'comparison': 'GT', 'param': 'SYN-P-LEAD', 'negate': False}]},
            {'rule_id': 'SYN-R-BUY-UP', 'intention': 'BUY', 'outcome': 'ACT_NOW', 'rationale_code': 'LEVEL-UP', 'basis_class': 'OWNER_ASSUMPTION',
             'owner_ref': 'TEST-ONLY owner', 'assumption': 'TEST-ONLY: the owner assumes acting is acceptable after an observed rise',
             'predicates': [{'p': 'SIGNAL_PRESENT', 'type': 'LEVEL_MOVEMENT', 'evidence_class': None, 'direction': 'UP', 'negate': False}]},
            {'rule_id': 'SYN-R-BUY-QUAL', 'intention': 'BUY', 'outcome': 'NEGOTIATE', 'rationale_code': 'EVIDENCE-QUALIFIED', 'basis_class': 'OWNER_ASSUMPTION',
             'owner_ref': 'TEST-ONLY owner', 'assumption': 'TEST-ONLY: the owner assumes negotiating is the step when the evidence is qualified',
             'predicates': [{'p': 'QUALIFIED', 'negate': False}]},
            {'rule_id': 'SYN-R-BUY-REST', 'intention': 'BUY', 'outcome': 'STAGE', 'rationale_code': 'OTHERWISE-STAGE', 'basis_class': 'OWNER_ASSUMPTION',
             'owner_ref': 'TEST-ONLY owner', 'assumption': 'TEST-ONLY: the owner assumes staging otherwise',
             'predicates': [{'p': 'GAP_PRESENT', 'reason': 'NO_EVIDENCE', 'negate': True}]},
            {'rule_id': 'SYN-R-SELL-UP', 'intention': 'SELL', 'outcome': 'HOLD', 'rationale_code': 'LEVEL-UP-HOLD', 'basis_class': 'OWNER_ASSUMPTION',
             'owner_ref': 'TEST-ONLY owner', 'assumption': 'TEST-ONLY: the owner assumes holding after an observed rise',
             'predicates': [{'p': 'SIGNAL_PRESENT', 'type': 'LEVEL_MOVEMENT', 'evidence_class': None, 'direction': 'UP', 'negate': False}]},
            {'rule_id': 'SYN-R-SELL-END', 'intention': 'SELL', 'outcome': 'ACT_NOW', 'rationale_code': 'VARIANT-ENDED', 'basis_class': 'OWNER_ASSUMPTION',
             'owner_ref': 'TEST-ONLY owner', 'assumption': 'TEST-ONLY: the owner assumes acting after a withdrawal event',
             'predicates': [{'p': 'SIGNAL_PRESENT', 'type': 'VARIANT_WITHDRAWN', 'evidence_class': None, 'direction': None, 'negate': False}]},
        ],
        'hooks': [{'hook_id': 'SYN-HOOK-1', 'port': 'CostValueHookPort'}],
        'provenance': {'author_ref': 'TEST-ONLY author', 'owner_ref': 'TEST-ONLY owner', 'synthetic': True},
    }
    doc.update(override)
    return doc


def pack_bytes(version='1.0.0', **override):
    return canon.dumps(pack(version, **override))
