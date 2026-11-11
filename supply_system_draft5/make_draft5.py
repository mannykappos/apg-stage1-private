"""Build DRAFT5.md from DRAFT4.md by replacing numbered lines (builder work, Claude). Each replaced line is checked by its expected start."""
src = open('DRAFT4.md').read().split('\n')
L = {i + 1: s for i, s in enumerate(src)}
R, A = {}, {}

def rep(n, starts, text):
    assert L[n].startswith(starts), (n, L[n][:60])
    R[n] = text

rep(1, '# APG Data Supply System', '# APG Data Supply System (blueprint amendment, draft 5)')
rep(7, 'This is draft 4', L[7].replace('This is draft 4', 'This is draft 5'))
rep(9, 'Five reviews shaped it', 'Four reviews and a note shaped it. Two independent agent checks: the audit of draft 1 (37 problems) and a scoped re-check '
    'of draft 2 (26 points), all fixed in draft 3. Then a GPT design review of draft 3 (30 points) with a note proposing a governance section, and a '
    'Gemini design review (7 points) with five further ideas, answered in draft 4. A third agent check, of what changed in draft 4, found 26 more points '
    '(none blocking), fixed here. The fix lists are in the pack. GPT points 28 and 29 said material was missing that is in the pack; Gemini\'s five '
    'ideas widen the scope and are listed separately, not designed in.')
rep(20, '2. **A core way in', '2. **A core way in for every entity.** Each entity (revision 3\'s 99, plus one this draft adds) has at least one designed '
    'Level 1 way in: an import template, document or email capture, an entry screen, a setup question, or a record APG calculates. None of these needs '
    'the builder\'s software. Every field the contracts name for a supplied record is also checked against its own record kind (see "Field-level '
    'coverage"). For 53 of the 100 entities, that way in still has to be built (see the supply plan).')
rep(33, 'So this amendment', 'So this amendment\'s first job is to bring every kind under one intake. Then it adds the front ends and a readiness layer. '
    'Every way in submits through the same stages and records its channel, the person or system, and the time. All kinds share one intake envelope '
    '(the common wrapper every submission carries: who, when, through which channel, for which organisation and project) and the same control '
    'checkpoints (the Section 04 stages below); the processing between the checkpoints is specific to each kind of record (a bank line, a defect photo, '
    'a contract and a forecast line need different validation), as Section 04 already allows.')
rep(41, '| Source authority', '| Source authority | S04 §5 | `source_authority.py`, rows written straight to the store | Setup questions that build the '
    'register and route it for approval, through the intake; authority scoped by organisation, project, record kind, field and effective period; two '
    'sources both claiming authority, or an unapproved or overlapping change of authority, is held for a person to resolve, never settled by picking '
    'one; an approved, dated change takes effect from its date |')
rep(43, '| Entity resolution', '| Entity resolution and reconciliation | S04 §11 | suppliers only (`ingest/entities.py`); other checks inside the '
    'calculations | Resolution of projects, contracts, variations, activities and defects; a match that is uncertain, or material and not made by a '
    'stable ID or an approved cross-reference rule, is held until a person confirms it; confidence alone never makes a link authoritative |')
rep(53, 'In words', 'In words, for readers of an export: the four Level 1 ways to supply data (import templates, document and email capture, entry '
    'screens, setup questions), phone site capture (Level 2) and AUIF integrations (Level 3) all feed one Section 04 intake. Stored records feed the '
    'rules and figures, which no way in changes. APG then calculates its own records from them: findings, baselines and the readiness record that '
    'tells the builder what is missing.')
rep(57, 'There are seven ways in', L[57].replace('and the records APG derives itself', 'and the records APG calculates itself')
    .replace('plus records APG derives', 'plus records APG calculates'))
rep(86, '- The detection-rule settings ship', '- The detection-rule thresholds and windows ship pre-set to defaults you approve, so a builder sees results without '
    'tuning them; the builder\'s approver accepts the defaults at onboarding (PG-DS-AC-05) and may later adjust them within the allowed ranges (S06 §5.1 '
    'requires thresholds to be configurable within approved boundaries). Two settings have no sensible default and the builder supplies them when the '
    'rule is switched on: R04B\'s instruction types (the builder\'s own notice categories) and R07\'s pairs of comparable items (declared by a person). '
    'Defaults are allowed here and not for the M6 supplements because a threshold is a choice of sensitivity, while a quote tier or landed cost is a fact '
    'from a real quote. The defaults stay general rather than tied to one state\'s contract forms, because APG is meant for builders in more than one '
    'state and contract forms differ; a builder adjusts them to its own contracts.')
rep(89, '**Records APG calculates', '**Records APG calculates (11 entities; 7 built or partly built, 4 not).** Baselines, assessments (calculation runs), '
    'scenarios, findings, alerts, deadlines and the readiness record, calculated from stored records by APG and recorded with their calculation run '
    '(Section 03). Five more entities list an APG-calculated path but are records a person confirms: retention events, root-cause hypotheses, quality '
    'cost, outcomes and prevention opportunities. APG may propose a value for those, but a person records or confirms it through an entry screen and the '
    'intake, with its own approval, so the entry screen is their minimum way in. The source registry (E02) is a setup question with a calculated '
    'alternative. "Partly" mostly means the code calculates the record but does not store it as its own; the exception is the provenance fields, '
    'stored on other records.')
rep(100, 'This is a change from revision 3', L[100].replace('Both design reviews agreed with Level 2, provided site needs are tested early:',
    'GPT\'s review agreed with Level 2, provided site needs are tested early (Gemini\'s did not discuss phone capture):'))
rep(116, '1. Only Level 1', '1. Only Level 1 ways in count: import template, document capture, entry screen, setup question, record APG calculates.')
rep(117, '2. A value Section 04', L[117].replace('An APG record takes "APG derives" only where the register lists it',
    'An APG record takes "APG calculates" only where the register lists it'))
rep(118, '3. Otherwise', L[118].replace('setup, APG derives.', 'setup, APG calculates.'))
rep(139, 'A way in for an entity', 'A way in for an entity does not prove a way in for every field a rule reads. `build_field_coverage.py` checks every '
    'field that revision 3\'s 39 contract rows name, against the record kind it belongs to (`FIELD_COVERAGE.csv`): 87 distinct kind-and-field pairs. '
    'Each is a field of its own kind in revision 3\'s field register, which lists what the synthetic stage 1 templates accept. A few contract entries '
    'use plain words (such as "amount" or "delta"); each is matched to its named field. The one field read on every record, the project, is checked '
    'on each kind the M4 figures read; credit notes, order amendments and bank lines reach their project through a linked record, and the funding '
    'facility is organisation-level. The other named items are not template fields, and each has a supplier: retention events will be recorded by a '
    'person through the release A entry form (today the code writes them directly); duplicate and reconciliation states are set by the intake; invoice '
    'lines and the carrying components are calculated; R04B\'s instruction types are a detection-rule setting (N01). The check finds no gap, and fails if '
    'one appears.')
rep(141, 'Its limits', 'Its limits: it does not check the contracts\' configuration column (the financial-policy fields in E90 and the detection-rule '
    'settings in N01, which come through setup); fields the contracts do not name (for example the link from a bank line to its retention event); the '
    'fields of retention events, which have no definition yet; or each field\'s authority and verification requirement. The field register is an '
    'inventory of the synthetic templates, not yet a validated schema register. The entry screens and document capture will be generated from the same '
    'field definitions once the schema register exists, and the check then runs for each way in as it is built (PG-DS-AC-12).')
rep(162, '3. **Nudges', L[162].replace('A nudge links straight to the form that fixes it, after sign-in.',
    'A nudge links straight to the way in that fixes it (a form, an upload or the review queue), after sign-in.'))
rep(175, '**Release A is not complete until two gates', '**Release A is not complete until three gates are passed:** the M6 input contracts are '
    'written and approved, and their fields checked like the rest; the intake migration (item 1) has passed as its own milestone; and the field-coverage '
    'report passes for release A, now including the setting fields and the retention-event fields (PG-DS-AC-12). Release A is also delivered '
    'progressively: the first pilot project gets the data its first chosen insights need, then the forms and document types grow. No builder is asked '
    'to populate all 100 entities.')
rep(179, '1. **One intake for every kind', '1. **One intake for every kind, as its own gated milestone.** Bring the 24 kinds of the second delivery loop '
    'under the Section 04 intake: reconciliation, authority and resolution beyond suppliers. This is not neutral for the rules: today they use those 24 '
    'kinds whenever the record\'s own checks pass, so reconciling them changes which records the rules and figures may use. It is a separate technical '
    'milestone under its own change request. A regression baseline (a saved copy of today\'s rule and figure results, to compare against) is taken first; '
    'every difference is explained and signed off; nothing in release A relies on the merged intake until it passes; afterwards the rules read the '
    'reconciled state, as they already do for the 11 reference kinds. PG-DS-AC-03 governs new ways in, not this migration. The three records written '
    'directly today (retention events, authority register rows, extracted documents) are not part of this migration: they enter the reference intake as '
    'new record kinds (items 3 and 4), which do not wait for it.')
rep(182, '4. **Retention events', '4. **Retention events and quote readings.** Retention events are recorded through that form and the intake, replacing '
    'today\'s direct write. Quote readings likewise: today\'s verification control is linked into the intake. Until real extraction exists, one person '
    'keys a reading from the attached quote and a second person with the verifier role confirms it, so no material value counts on one person\'s '
    'word (S04 §12 for extracted values, §18 for manual entry).')
rep(186, '**Recommended, for you to decide.**', '**Recommended, for you to decide.** Gemini said the earlier recommendation (every small fact plus '
    'finished document capture) was too much for a first release; GPT kept it as the target but asked for a staged rollout. Claude now recommends a '
    'middle path:')
rep(188, '- **Entry forms only', '- **Entry forms only for the facts the first pilot\'s insights need**, beyond setup and retention, added progressively as '
    'more insights are switched on. The five M6 supplements are asked for only when a builder uses the market insights, and APG does not invent '
    'default values for them, because they are facts from real quotes. Under the middle path, landed-cost components and import checks (E33, E34) get '
    'entry forms; specification requirements, quote tiers and quote terms (E27, E31, E32) come by template or by the person-keyed document upload, '
    'since the register lists no entry screen for them.')
rep(189, '- **Document upload', '- **Document upload, not finished document capture:** upload and email intake with person-keyed, second-person-confirmed '
    'values, used for quote readings, the three M6 supplements above and as evidence attached to records. Because originals are kept, choosing the '
    'middle path moves the document record (E83: the original file and its hash) into release A. Finished capture with real extraction waits until an '
    'extraction vendor is chosen (EDR-22), because without it staff would key every value.')
rep(191, 'Even so, seven release A facts', 'Seven release A facts have no way in other than a file under any option: purchase orders, credit notes, '
    'timesheets, bank transactions and deliveries, which usually come from the accounting, payroll or job system\'s export (Claude\'s judgement, to '
    'confirm with pilot builders), and market observations and FX rates, which are data sources rather than builder records. Their fallback, a template '
    'the builder fills by hand, is available in release A. Under the middle path, other release A facts also come by file until their entry form is '
    'added. Discovery must confirm, for each file, that the pilot builder can really produce it; where it cannot, the readiness record shows the gap and '
    'its fallback.')
rep(197, '**Release B (22 entities).**', L[197].replace('Both reviews flagged them as a main source of profit leakage;',
    'Gemini flagged them as a main source of profit leakage;'))
rep(214, '- **Who does what.**', '- **Who does what.** For each kind of record there is a supplier, a checker, a corrector, an approver and an accountable '
    'owner if it stays missing. They start from defaults and are confirmed progressively, as each kind of record comes into use. In the readiness record '
    'the likely holder is where the information sits, the action owner is the supplier or corrector, and the approver is the approver. One person can '
    'hold several roles; the roles stay distinct in the record (for example, a subcontractor claim entered by an administrator, checked by a contract '
    'administrator, approved by a commercial manager).')
rep(217, '- **Access.**', '- **Access.** Organisation, legal entity, project and role boundaries hold on every way in (S04 §6, §16). Sharing information '
    'between related companies or joint ventures is not defined by the blueprint sections in this pack and could conflict with tenant isolation; it '
    'needs its own decision.')
rep(230, '| PG-DS-AC-01', L[230].replace('Records APG derives are written', 'Records APG calculates are written'))
rep(231, '| PG-DS-AC-02', '| PG-DS-AC-02 | Two inputs that describe the same source fact (the same values, units, currency, date and time and tax basis) and '
    'meet the same authority and verification conditions, supplied through any two ways in, are mapped (translated into APG\'s standard fields) to '
    'identical field values and give the same rule outcome; only the provenance differs. Shown by a test. |')
rep(236, '| PG-DS-AC-07', '| PG-DS-AC-07 | Every uploaded file, email attachment and photo is scanned and parsed in isolation within size, archive and '
    'resource limits before it is read; a malformed or unsupported file is rejected with a reason. |')
rep(239, '| PG-DS-AC-10', '| PG-DS-AC-10 | Each data gap has a stable identity (entity, field, period, source) and moves through open, assigned, awaiting '
    'evidence, resolved, suppressed, reopened and superseded; a gap found again updates its existing nudge instead of creating a new one; suppression '
    'windows and re-notification rules are defined and tested (S06 §9.1). |')
rep(241, '| PG-DS-AC-12', '| PG-DS-AC-12 | Every field a current rule or figure reads, including setting fields, has at least one built way in that '
    'carries it, with its authority and verification requirement met; and each way in, when built, carries every field of the entities it serves. Shown '
    'by a generated field-coverage report that fails on a gap; a release A gate. |')
rep(260, '1. **The architecture.**', '1. **The architecture.** One intake, six ways to supply data in three levels plus the records APG calculates, a Level 1 '
    'way in for every entity, and no rule changed by any way in.')
rep(266, '7. **Subcontractor claims.**', '7. **Subcontractor claims.** Promoting subcontractor claims, assessments and payments (E17 to E19) to the front of '
    'release B only gets the data ready early: no current rule reads them, so nothing changes until a rule that uses them exists, such as the '
    'back-to-back claim check below. Claude recommends promoting them together with taking that check forward (decision 8).')
rep(269, '**The cascade impact assessment', L[269].replace('Section 01 (users and roles, if they come from the platform);',
    'Section 01 (users and roles if they come from the platform, and the tenant model for any sharing between related companies); Sections 15 to 17 '
    '(security, reliability and recovery for the new channels);'))
rep(279, '- **A learning cost-code map**', '- **A learning cost-code map** (Gemini): learn from the builder\'s own confirmed mappings to suggest better matches. '
    'Within this design every match is still confirmed by a person; letting confident matches apply on their own would change that rule and S04 §11\'s '
    '"confidence alone" limit, so it belongs to that idea\'s own change request. Learning stays within one builder\'s data, never across builders '
    '(S04 §16).')
rep(281, '**Gaps in the locked blueprint itself:**', '**Possible gap in the locked blueprint:** data retention, archiving and retrieval after project '
    'close-out and when a customer leaves APG (GPT). Not found in the sections in this pack; S04 §6 defers to the platform\'s retention conventions and '
    'S04 §16 covers backups. To confirm against Sections 09 and 15 to 17 before raising a change request.')
rep(283, '**Next:**', '**Next:** your decisions. No further GPT or Gemini round unless a blocking problem appears. Corrections from revision 3\'s GPT '
    'check are folded in first, and the supply plan is regenerated if the registers change. The extraction vendor requirements (EDR-22) and the AUIF '
    'contracts are not in this pack and remain dependencies.')

out = []
for n in range(1, len(src) + 1):
    out.append(R.get(n, L[n]))
    if n in A:
        out.append(A[n])
t = '\n'.join(out)
assert 'APG derives' not in t and 'records APG derives' not in t, [l[:80] for l in out if 'derives' in l]
open('DRAFT5.md', 'w').write(t)
print('ok', len(t))
