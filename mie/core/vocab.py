"""The closed, versioned vocabularies of the core (MIE1_SPEC sections 3.3, 5.1, 6.1, 9.3; MIE1_SIGNAL_VOCABULARY.csv, MIE1_OUTCOME_AND_EVENT_VOCABULARY.csv,
MIE1_ERROR_VOCABULARY.csv).  A pack may choose from these; it cannot add to them or change a meaning.  Any change here is a core change with a new version."""

CORE_VERSION = 'mie-core-1.0.0'
PACK_SCHEMA = 'mie-pack-1'
VERSIONS = {
    'core': CORE_VERSION,
    'pack_schema': PACK_SCHEMA,
    'signal_vocabulary': 'mie-signal-1',
    'outcome_vocabulary': 'mie-outcome-1',
    'event_class_vocabulary': 'mie-event-1',
    'error_vocabulary': 'mie-error-1',
    'neutrality_deny_list': 'mie-deny-1',
}

# signals (SIG-01..08)
MARKET_SIGNALS = ('LEVEL_MOVEMENT', 'CONVERSION_MOVEMENT', 'AVAILABILITY_CHANGE', 'VARIANT_INTRODUCED', 'VARIANT_WITHDRAWN')
DATA_SIGNALS = ('DATA_STALE', 'DATA_MISSING', 'DATA_CONFLICT')
SIGNALS = MARKET_SIGNALS + DATA_SIGNALS
MOVEMENT_SIGNALS = ('LEVEL_MOVEMENT', 'CONVERSION_MOVEMENT')
EVENT_SIGNALS = ('AVAILABILITY_CHANGE', 'VARIANT_INTRODUCED', 'VARIANT_WITHDRAWN')
DIRECTIONS = ('UP', 'DOWN', 'UNCHANGED')
AVAILABILITY = ('INCREASED', 'DECREASED', 'UNAVAILABLE', 'RESTORED')

# events (EVC-01..03) and the signal each feeds
EVENT_CLASSES = ('AVAILABILITY_CHANGED', 'VARIANT_INTRODUCED', 'VARIANT_WITHDRAWN')
EVENT_SIGNAL = {'AVAILABILITY_CHANGED': 'AVAILABILITY_CHANGE', 'VARIANT_INTRODUCED': 'VARIANT_INTRODUCED', 'VARIANT_WITHDRAWN': 'VARIANT_WITHDRAWN'}

# intentions and outcomes (OUT-01..09)
INTENTIONS = ('BUY', 'SELL')
OUTCOMES = {'BUY': ('ACT_NOW', 'WAIT', 'STAGE', 'NEGOTIATE', 'NOT_ASSESSED'), 'SELL': ('ACT_NOW', 'HOLD', 'WAIT', 'NOT_ASSESSED')}
ALL_OUTCOMES = tuple(sorted(set(OUTCOMES['BUY']) | set(OUTCOMES['SELL'])))

# observations
OBSERVATION_CLASSES = ('HISTORICAL_MOVEMENT', 'CURRENT_REFERENCE', 'COUNTERPARTY_OFFER')
VALUE_BASES = ('ASKING', 'OFFER', 'INDEX', 'COMPLETED_TRANSACTION')
VALUE_DOMAINS = ('POSITIVE', 'NON_NEGATIVE', 'SIGNED')
MOVEMENT_BASES = ('ABSOLUTE', 'RELATIVE')
LICENCE_STATUSES = ('LICENSED', 'UNLICENSED', 'UNKNOWN')
EVIDENCE_GROUPS = ('historical_movement', 'current_reference', 'counterparty_offer', 'scenarios')
GROUP_OF_CLASS = {'HISTORICAL_MOVEMENT': 'historical_movement', 'CURRENT_REFERENCE': 'current_reference', 'COUNTERPARTY_OFFER': 'counterparty_offer'}

# decision table
DECISION_PROFILES = ('CONTEXT_ONLY', 'SIGNAL_RULES')
BASIS_CLASSES = ('OBSERVED_EVIDENCE_ONLY', 'OWNER_ASSUMPTION')
PREDICATES = ('SIGNAL_PRESENT', 'SIGNAL_NOT_ASSESSED', 'GAP_PRESENT', 'CONSTRAINT_COMPARE', 'CONSTRAINT_ABSENT', 'SCENARIO_PRESENT', 'QUALIFIED')
COMPARISONS = ('LT', 'LE', 'EQ', 'GE', 'GT')
CONSTRAINTS = ('days_to_need_by',)
INFLUENCE_CLASSES = ('DIRECT', 'PRECEDENCE', 'NONE')

# audit (AUD-01..05)
AUDIT_OUTCOMES = ('OK', 'ACCEPTED', 'REFUSED', 'FAILED')
AUDIT_READ = 'AUDIT_READ'

# operations (OP-01..12)
OPERATIONS = ('describe', 'validate_pack', 'register_pack', 'get_pack', 'withdraw_pack', 'activate_pack', 'submit_observations', 'get_signals', 'assess_timing',
              'replay_result', 'get_result', 'list_audit')
STATE_CHANGING = ('register_pack', 'withdraw_pack', 'activate_pack', 'submit_observations', 'assess_timing')

# errors (kind ERROR) and reasons (kind REASON)
ERRORS = ('TENANT_CONTEXT_MISSING', 'TENANT_CONTEXT_INVALID', 'NOT_FOUND', 'PACK_MALFORMED', 'PACK_SCHEMA_UNSUPPORTED', 'PACK_CORE_INCOMPATIBLE', 'PACK_INVARIANT_OVERRIDE',
          'PACK_HASH_MISMATCH', 'PACK_VERSION_CONFLICT', 'PACK_NOT_ACTIVE', 'PACK_WITHDRAWN', 'PACK_INCOMPLETE', 'PACK_APPROVAL_MISSING', 'INTENTION_NOT_ALLOWED',
          'OBSERVATION_INVALID', 'LICENCE_NOT_PERMITTED', 'SCENARIO_INVALID', 'REQUEST_MALFORMED', 'LIMIT_NOT_CONFIGURED', 'LIMIT_EXCEEDED', 'AUDIT_UNAVAILABLE',
          'STORE_UNAVAILABLE', 'REPLAY_EVIDENCE_UNAVAILABLE', 'REPLAY_PACK_UNAVAILABLE', 'HOOK_UNAVAILABLE', 'INTERNAL_ERROR_FAIL_CLOSED', 'PACK_RULE_POLICY_VIOLATION')
REASONS = ('PARAMETER_MISSING', 'FRESHNESS_LIMIT_MISSING', 'NO_EVIDENCE', 'INSUFFICIENT_POINTS', 'CONFLICT_IN_EVIDENCE', 'STALE_EVIDENCE', 'LICENCE_EXCLUDED', 'ZERO_BASE',
           'UNIT_MISMATCH', 'NO_TABLE', 'NO_RULE_MATCHED', 'CONSTRAINT_MISSING', 'EXPIRED_EVIDENCE', 'OBSERVATION_AFTER_EVALUATION_DATE', 'VALUE_OUT_OF_DOMAIN')
COMMON_ERRORS = ('TENANT_CONTEXT_MISSING', 'TENANT_CONTEXT_INVALID', 'AUDIT_UNAVAILABLE', 'INTERNAL_ERROR_FAIL_CLOSED')
OPERATION_ERRORS = {     # MIE1_PORTS.csv: the full error list of each inbound operation
    'describe': COMMON_ERRORS,
    'validate_pack': COMMON_ERRORS + ('REQUEST_MALFORMED', 'PACK_MALFORMED', 'PACK_SCHEMA_UNSUPPORTED', 'PACK_CORE_INCOMPATIBLE', 'PACK_INVARIANT_OVERRIDE',
                                      'PACK_RULE_POLICY_VIOLATION', 'LIMIT_NOT_CONFIGURED', 'LIMIT_EXCEEDED'),
    'register_pack': COMMON_ERRORS + ('REQUEST_MALFORMED', 'PACK_MALFORMED', 'PACK_SCHEMA_UNSUPPORTED', 'PACK_CORE_INCOMPATIBLE', 'PACK_INVARIANT_OVERRIDE',
                                      'PACK_RULE_POLICY_VIOLATION', 'PACK_VERSION_CONFLICT', 'LIMIT_NOT_CONFIGURED', 'LIMIT_EXCEEDED', 'STORE_UNAVAILABLE'),
    'get_pack': COMMON_ERRORS + ('REQUEST_MALFORMED', 'NOT_FOUND', 'PACK_HASH_MISMATCH', 'STORE_UNAVAILABLE'),
    'withdraw_pack': COMMON_ERRORS + ('REQUEST_MALFORMED', 'NOT_FOUND', 'STORE_UNAVAILABLE'),
    'activate_pack': COMMON_ERRORS + ('REQUEST_MALFORMED', 'NOT_FOUND', 'PACK_HASH_MISMATCH', 'PACK_WITHDRAWN', 'PACK_APPROVAL_MISSING', 'STORE_UNAVAILABLE'),
    'submit_observations': COMMON_ERRORS + ('REQUEST_MALFORMED', 'PACK_NOT_ACTIVE', 'PACK_HASH_MISMATCH', 'PACK_WITHDRAWN', 'LIMIT_NOT_CONFIGURED', 'LIMIT_EXCEEDED',
                                            'STORE_UNAVAILABLE'),
    'get_signals': COMMON_ERRORS + ('REQUEST_MALFORMED', 'NOT_FOUND', 'PACK_NOT_ACTIVE', 'PACK_HASH_MISMATCH', 'PACK_WITHDRAWN', 'LIMIT_NOT_CONFIGURED', 'LIMIT_EXCEEDED',
                                    'STORE_UNAVAILABLE'),
    'assess_timing': COMMON_ERRORS + ('REQUEST_MALFORMED', 'INTENTION_NOT_ALLOWED', 'PACK_NOT_ACTIVE', 'PACK_HASH_MISMATCH', 'PACK_WITHDRAWN', 'PACK_INCOMPLETE',
                                      'SCENARIO_INVALID', 'LIMIT_NOT_CONFIGURED', 'LIMIT_EXCEEDED', 'STORE_UNAVAILABLE'),
    'replay_result': COMMON_ERRORS + ('REQUEST_MALFORMED', 'NOT_FOUND', 'REPLAY_EVIDENCE_UNAVAILABLE', 'REPLAY_PACK_UNAVAILABLE', 'STORE_UNAVAILABLE'),
    'get_result': COMMON_ERRORS + ('REQUEST_MALFORMED', 'NOT_FOUND', 'STORE_UNAVAILABLE'),
    'list_audit': COMMON_ERRORS + ('REQUEST_MALFORMED', 'LIMIT_NOT_CONFIGURED', 'LIMIT_EXCEEDED'),
}

# host limits (PT-09): the keys the host must supply; the core ships no value
LIMIT_KEYS = ('max_pack_bytes', 'max_rules', 'max_string_length', 'max_batch_items', 'max_abs_exponent', 'max_mantissa_digits', 'max_series_points', 'max_audit_page',
              'max_scenarios')

# fixed statements
MOVEMENT_STATEMENT = 'Observed movement is not a forecast; a signal states what was observed in the evidence and predicts nothing.'
ADVISORY = 'This record is advisory. It commits nothing, orders nothing and notifies no one; a person decides.'
ASSUMPTION_LABEL = 'Assumption-based: this outcome follows a rule the owner set as an assumption; it is not a forecast and not a tendency of levels.'


class MieError(Exception):
    """An operation-level error from the closed vocabulary.  Never carries a partial result."""
    def __init__(self, code, detail=''):
        assert code in ERRORS, code
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail
