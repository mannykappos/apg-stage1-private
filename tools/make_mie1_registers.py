#!/usr/bin/env python3
"""Adds the MIE-1 rows to the programme tables: status rows SR-105 to SR-108, interpretations I-118 to I-124, the Engine handoff entry EDR-37 and the carried-forward items CF-36
(the open release gates) and CF-37 (the three implementation blockers).  Usage: make_mie1_registers.py <programme_dir>   (runs AFTER make_m73_registers.py).  Idempotent; no
existing row is changed.  Nothing here closes a finding, resolves a blocker or settles a decision: the M7.3 release gates stay open, BLK-01 to BLK-03 stay open, and every
interpretation is retained for review."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M = 'MIE-1'
CLAIM = ('Builder-run; no independent review has taken place. Every owner value in the tests (thresholds, windows, parameters, licences, decision rules) is a TEST-ONLY fixture value; '
         'nothing is integrated with the Anchor Engine and no APG finding or recommendation consumes the core.')
STATUS = [
    dict(item_id='SR-105', item='The universal market-intelligence core (mie/core: canonical form, exact values, pack validation mie-pack-1, observations, signals, timing assessment, '
                                'the twelve operations, the outbound ports and their non-production reference implementations), built from MIE1_SPEC v0.3', milestone=M,
         evidence_ladder_status='Local-tested',
         evidence='tests/test_mie_core_*.py (static, pack, observations, signals, timing, replay, tenancy, audit, ports, adversarial); tests/test_mie_flow.py; tests/test_mie_portability.py; '
                  'tools/mie_static.py (8 checks); programme/MIE1_CASE_COVERAGE.csv', claim_limit=CLAIM),
    dict(item_id='SR-106', item='The construction pack (mie/packs/construction.py: BUY only, CONTEXT_ONLY, structure only), the M6 mapping (mie/adapters/m6.py) and the Builder Zero run',
         milestone=M, evidence_ladder_status='Local-tested',
         evidence='tests/test_mie_construction.py; tests/helpers_mie_construction.py; regression/mie1/golden_mie1.json; tools/run_golden_mie1.py',
         claim_limit=CLAIM + ' The completed construction pack in the tests is a TEST-ONLY completion: the base pack carries no owner value, and the real values are the policy owner\'s.'),
    dict(item_id='SR-107', item='Mutation run over the core logic and package sabotage checks for the MIE-1 sabotage catalogue (SB-01 to SB-60), run fresh by the build', milestone=M,
         evidence_ladder_status='Local-tested', evidence='tools/mie_mutants.py; tools/sabotage_mie1.py; logs/mie1/', claim_limit=CLAIM),
    dict(item_id='SR-108', item='Specified elsewhere and NOT implemented in MIE-1: (1) PSA02-D2 specification_ref and methodology_ref on observations, and their mismatch rejection; '
                                '(2) DECLARATION_CHANGED and pack re-attestation; (3) the P1 normal form (not approved; OD-06)', milestone=M,
         evidence_ladder_status='Not implemented', evidence='None - no code, no test',
         claim_limit='Not implemented. Each depends on a decision that is still open; nothing in MIE-1 approximates them.'),
]
INTERP = [
    ('I-118', 'How the core is deployed', 'The core is an in-process library: the host constructs the Engine with its own implementations of the outbound ports (context, stores, audit '
              'append and query, approvals, hooks, limits). The core reads nothing else. mie/core/reference.py holds non-production in-memory ports for tests; '
              'mie/adapters/apg_host.py lets APG\'s verified context be the core\'s tenant context.',
     'MIE1_SPEC 9 and 10; MIE-R-45; MIE-OQ-25', 'If the core must run as a separate service, the twelve operations need a transport and the ports a remote form; the core logic is unchanged.'),
    ('I-119', 'Who can see, withdraw and activate a pack', 'The pack registry is platform-wide: any verified tenant may read a registered pack by its exact pin. Activation is per tenant and needs an '
              'approval reference that the ApprovalVerifierPort verifies for that tenant and that exact pin; an approver who is the pack\'s author is refused. Only the publishing tenant can '
              'withdraw a pack; to any other tenant a withdrawal attempt looks like a missing pack (NOT_FOUND).',
     'MIE1_SPEC 6.6, 9; MIE-R-33, 34', 'If packs must be private to a tenant, get_pack and register_pack would be scoped by tenant; the tests in test_mie_core_pack.py would change.'),
    ('I-120', 'PACK_INCOMPLETE and NOT_FOUND for a subject the pack does not declare', 'assess_timing (OP-09) refuses a subject the active pack does not declare with PACK_INCOMPLETE: the '
              'pack cannot yet assess it. get_signals (OP-08) refuses it with NOT_FOUND, because its error list has no PACK_INCOMPLETE.',
     'MIE1_PORTS OP-08, OP-09; MIE1_ERROR_VOCABULARY', 'If an undeclared subject should be NOT_ASSESSED with a gap rather than refused, both operations change and AU-11 would be re-run.'),
    ('I-121', 'The M6 mapping (blocker BLK-02)', 'Derived by reading M6 and M3 source, read only: market_observation material_ref, obs_date, value_scaled (kept exactly as {mantissa, '
              'exponent 0} in its stored unit), unit_text, kind_text (index -> HISTORICAL_MOVEMENT, INDEX), source_label_text, geography_text and provenance.received_at map to subject, as_of, '
              'value, unit, class and basis, source, market and retrieved_at; fx_rate maps to the subject FX:<pair> with the rate parsed exactly from its decimal text, class CURRENT_REFERENCE. '
              'Records M4 or M6 would not use are not submitted and are reported; a conflict marker is submitted as each contender so that the core reports the conflict.',
     'MIE-R-47, 49; MIE-L-16; BLK-02; mie/adapters/m6.py', 'If the review of the mapping finds a different reading (for example of the index unit or the FX class), only the adapter and the '
              'pack inputs change; the core does not.'),
    ('I-122', 'What MIE-1 leaves out', 'PSA02-D2 (specification_ref and methodology_ref and their mismatch rejection), DECLARATION_CHANGED with re-attestation, and the P1 normal form are not '
              'implemented: each rests on a decision that is still open. No placeholder code stands in for them.',
     'PSA02-D2; OD-06; PH-04; PH-10; PH-15', 'If any is decided, it is a later, separately authorised change to the pack schema, the observation schema or both.'),
    ('I-123', 'Evidence that counts as usable for a subject', 'A subject\'s usable evidence includes the series of the conversions the pack declares for it. So a material with no index '
              'evidence of its own but a current conversion series is assessed (not NOT_ASSESSED for NO_EVIDENCE), and the result is QUALIFIED with the missing required evidence '
              'listed. In the Builder Zero run this is MAT-PBOARD: a CONTEXT_ONLY date rule fires (ACT_NOW, influence NONE) while its own index evidence is NO_EVIDENCE.',
     'MIE1_SPEC 5, 6.4; MIE-R-24, 27', 'If only the subject\'s own series should count, signals.assess_evidence would count usable evidence for the subject alone and MAT-PBOARD would be '
              'NOT_ASSESSED with NO_EVIDENCE; the golden file would change.'),
    ('I-124', 'The retrieval date of an observation from the M6 feed', 'The M6 MarketFeedPort reports no retrieval date for an observation, so the M6 feed adapter asserts one from the '
              'integrator\'s clock (an adapter-side callable). The core checks only that it is not earlier than as_of (MIE-L-18).',
     'MIE-L-18; MIE-R-66', 'If a retrieval date must come from the feed, the M6 port would need a field, which is an M6 change and not made here.'),
]
EDR = dict(edr_id='EDR-37', port='MIE host ports (TenantContextPort, ObservationStorePort, PackRegistryPort, ResultStorePort, AuditLogPort, AuditQueryPort, ApprovalVerifierPort, '
                                 'CostValueHookPort, LimitsConfig)',
           title='Implement the market-intelligence core\'s outbound ports in the Anchor Engine, including an atomic audit append and state commit',
           what_apg_needs='The core calls only these ports. Stores are tenant-scoped, append-only or immutable, and return copies; the pack registry binds an id and version to one hash; '
                          'the audit log is a per-tenant hash chain with a separate read-and-verify query port; approvals are verified per tenant and exact pin and refuse the author; '
                          'limits are host-configured with no defaults. The core orders every operation as validate, compute, append the audit event, commit, return; making the append and '
                          'the commit atomic is the host\'s (BLK-01, MIE-OQ-23).',
           why_the_engine_is_needed='Persistence, identity, approvals and audit storage are the Engine\'s. The reference ports in mie/core/reference.py are in memory and not for production.',
           contract_summary='mie/core/ports.py (PT-01 to PT-10 without PT-06); the contract tests CT-01 to CT-13 in tests/test_mie_core_ports.py, test_mie_core_tenancy.py and test_mie_core_audit.py',
           contract_test='tests/test_mie_core_ports.py; tests/test_mie_core_audit.py (failure injection); tests/test_mie_core_tenancy.py',
           blueprint_refs='MIE1_SPEC 9, 10; MIE1_PORTS.csv', capabilities='', needed_by_milestones='Any use of the core outside tests',
           decisions_for_amir='How the Engine makes the audit append and the state commit atomic (BLK-01); whether the pack registry is platform-wide (I-119); where the ingestion driver and '
                              'the feed adapter run (MIE-OQ-25).', owner='Amir (engine, database, environment)',
           status='Open - ports defined; reference ports pass the contract tests; no Engine implementation', evidence_seen='No Engine code, repository or environment seen; no implementation exists')
CF = [
    dict(cf_id='CF-36', audit_section='', topic='Release gates carried from M7.3 into MIE-1',
         what_remains_open='M7.3: final release acceptance is pending, because the full sabotage and mutation suites were not independently completed. EDR-36: the real Anchor Engine store\'s '
                           'support for the atomic guard contract is not verified. The delivered M9.4 ZIP was not available, so the M9.4 comparison is unverified. MIE-1 itself has not been '
                           'independently audited.',
         what_this_package_shows='The product owner authorised MIE-1 development with these gates open. MIE-1 changes no APG application file and no existing test (tools/run_regression_mie1.py '
                                 'R01 to R03), so the M7.3 evidence still applies to the APG files unchanged.',
         linked_records='CF-35; EDR-36; SR-103; SR-104; SR-105 to SR-108', who_must_act='Auditor: complete the M7.3 suites and audit MIE-1; product owner: supply the M9.4 ZIP; Amir: EDR-36',
         status='Open - release gates'),
    dict(cf_id='CF-37', audit_section='', topic='The MIE-1 implementation blockers BLK-01 to BLK-03',
         what_remains_open='BLK-01 (the audit append and the state commit are not atomic): the core implements the ordered sequence; atomicity is a host property, now EDR-37; the explicit '
                           'decision and its review are outstanding. BLK-02 (the M6 mapping): derived from source in this build (I-121); its independent review is outstanding. BLK-03 '
                           '(the Section 08 cascade impact assessment): not performed; the construction pack is CONTEXT_ONLY and no APG finding or recommendation consumes a signal.',
         what_this_package_shows='The product owner authorised implementation with the blockers open. None is resolved or decided here.',
         linked_records='EDR-37; I-121; MIE-OQ-23; MIE-OQ-12', who_must_act='Product owner and independent reviewer', status='Open - blocking release, not development'),
]

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e, status=M7.RETAINED)
                                                                 for i, t, b, r, e in INTERP])
    M7.add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', [EDR])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
