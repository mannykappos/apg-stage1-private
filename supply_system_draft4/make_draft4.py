"""Build DRAFT4.md from DRAFT3_EXPORT.md: replace numbered lines and insert new sections (builder work, Claude)."""
src = open('DRAFT3_EXPORT.md').read().split('\n')
L = {i + 1: s for i, s in enumerate(src)}
R = {}   # line number -> replacement text ('' deletes the line)
A = {}   # line number -> text inserted after that line

R[1] = '# APG Data Supply System (blueprint amendment, draft 4)'
R[7] = L[7].replace('This is draft 3', 'This is draft 4')
R[9] = ('Five reviews shaped it. Two independent agent checks: the audit of draft 1 (37 problems) and a scoped re-check of draft 2 (26 points), all fixed '
        'in draft 3. Then a GPT design review of draft 3 (30 points) with a note proposing a governance section, and a Gemini design review (7 points) with '
        'five further ideas. Draft 4 fixes or answers every point from all five; the fix list is in the pack. Two GPT points (28, 29) said material was missing '
        'that is in the pack. The five further ideas widen the scope and are listed separately, not designed in.')
R[20] = ('2. **A core way in for every entity and every field.** Each entity (revision 3\'s 99, plus one this draft adds) has at least one designed Level 1 '
         'way in: an import template, document or email capture, an entry screen, a setup question, or a record APG calculates. None of these needs the '
         'builder\'s software. Every field a current rule or M4 figure reads is checked separately (see "Field-level coverage"). For 53 of the 100 '
         'entities, that way in still has to be built (see the supply plan).')
R[33] = (L[33] + ' All kinds share one intake envelope and the same control checkpoints; the processing between the checkpoints is specific to each kind of '
         'record (a bank line, a defect photo, a contract and a forecast line need different validation), as Section 04 already allows.')
R[37] = ('| Source registration and authentication | S04 §3, §4, §6, §16 | tenant scope in code; no builder channels | Per channel: signed-in users for '
         'screens; email sender verification, with the tenant never taken from the address alone (a verified sender does not make an attached document '
         'genuine or authorised: S04 §5 and §12 still apply); phone enrolment and identified users on shared site phones; tenant isolation tested on each '
         'new path |')
R[38] = ('| File handling | S04 §18 | `ingest/filestore.py`: a scan-gated import path (test double), for the reference intake only; the det and mkt intakes '
         'read files directly | Scanning of every upload, email attachment and photo before it is read, on every path; safe parsing in isolation; size, '
         'archive and resource limits; malformed or unsupported files rejected with a reason |')
R[41] = ('| Source authority | S04 §5 | `source_authority.py`, rows written straight to the store | Setup questions that build the register and route it for '
         'approval, through the intake; authority scoped by organisation, project, record kind, field and effective period; two sources both claiming '
         'authority, or a change of authority mid-project, is held for a person to resolve, never settled by picking one |')
R[43] = ('| Entity resolution and reconciliation | S04 §11 | suppliers only (`ingest/entities.py`); other checks inside the calculations | Resolution of '
         'projects, contracts, variations, activities and defects; an uncertain or material match is held until a person confirms it and never becomes '
         'an authoritative link on confidence alone |')
R[61] = L[61].replace('Jobpac report.', 'Jobpac report. A blank template the builder fills by hand is a fallback, not effortless capture.')
A[65] = ('- Real builder files have several worksheets, inconsistent headers, formulas, merged cells, subtotals and odd date formats. Each file family is '
         'supported only once real pilot files prove it; an unsupported layout is shown as unsupported, never half-imported. Programme files (XER, MS '
         'Project XML) keep their activities, relationships and calendars; they are not flattened into a table.')
R[70] = ('- The builder uploads a file or forwards an email. The sender is verified and the organisation is never taken from the address alone (S04 §6). '
         'The original message and attachment are kept. Every file is scanned and safely parsed before it is read. Who sent it and whether the document '
         'is genuine and authorised are separate questions: the second is settled by verification and the authority register, not by the sender.')
R[71] = (L[71] + ' Verification can be done in batches (for example a page of extracted invoice values), but each value keeps its own confirmation and '
         'provenance; batching never weakens the rule.')
R[72] = ('- "Partly" here means only the verification control exists, with a stand-in parser for quotes. It is not linked to the intake and cannot verify '
         'dates yet. Finished capture needs an inbox, the verification screen, the link into the intake and real extraction, which needs the Engine and a '
         'vendor (EDR-22) not yet chosen. Without extraction, a person keys every value, so finished document capture waits for the vendor (see release A).')
R[76] = ('- One general form engine, not 47 separate screens: forms are generated from each entity\'s field definitions, so a new entity needs no new screen '
         'code. Each kind of record still gets its own task-shaped layout (the questions, evidence and approval steps of a variation differ from a delay '
         'or a forecast line), so the user sees the job they are doing, not a database table. It depends on the field-level schema register, a next step '
         'from revision 3, for each entity it serves.')
R[82] = ('- Onboarding asks only what the first insights the builder wants need. Further settings are asked for when an insight that needs them is switched '
         'on, so nobody configures everything before seeing a result. Settings that affect financial figures keep their approval.')
R[83] = ('- The cost-code map is required before any figure that groups by cost code. APG suggests matches and the builder confirms each one. A record '
         'whose code is not mapped yet still completes intake: it is held as "pending cost-code mapping" only for the figures that need the code, and '
         'listed for the person who owns the mapping.')
R[85] = ('- The detection-rule settings ship pre-set to defaults you approve, so a builder sees results without configuring thresholds; adjusting them is '
         'optional, within the allowed ranges (as S06 §5.1 requires thresholds to be configurable within approved boundaries); the builder\'s approver makes any change. Defaults are not tied to one state\'s contract forms.')
R[88] = ('**Records APG calculates (17 entities list it; 8 built or partly built, 9 not).** Baselines, assessments (calculation runs), scenarios, findings, '
         'alerts and the readiness record, calculated from stored records by APG and recorded with their calculation run (Section 03). These are different '
         'from records a person confirms: retention events, root-cause hypotheses, quality cost, outcomes and prevention opportunities. APG may propose a '
         'value for those, but a person records or confirms it, through an entry screen and the intake, with its own approval; so the entry screen is their '
         'minimum way in. "Partly" mostly means the code calculates the record but does not store it as its own; the exceptions are the provenance fields '
         '(stored on other records) and retention events (stored, but written directly, outside the intake).')
R[95] = ('- The person, time, place and any photo are kept as evidence, subject to Section 09 §14 (labour data privacy and role permissions, as revision 3 '
         'cites it). Each record says how the place was established (entered by the person or taken from the device); the device location is not assumed '
         'reliable; on a shared site phone the signed-in user is recorded, not the device; workers can see what was recorded about them, and a disputed '
         'record goes through the correction route. The detail is left to the cascade impact assessment.')
A[96] = ('- A Level 1 fallback can supply the same fact, but not always at the time it happened. Where timing matters (a delay, an instruction, a defect), a '
         'record entered after the event is marked retrospective, and the readiness record qualifies the insight that uses it.')
R[98] = (L[98] + ' Both design reviews agreed with Level 2, provided site needs are tested early: discovery of site capture, including whether it must work '
         'offline, is an early gate, not a late one.')
R[105] = ('- They remain proposed until the Section 01 discovery. Each is chosen on four tests: the pilot builders actually use the system, it has a usable '
          'API or export, its data quality is good enough, and it saves real manual effort. Popularity alone is not a reason.')
A[133] = ('\n### Field-level coverage\n\n'
          'A way in for an entity does not prove a way in for every field a rule reads. `build_field_coverage.py` checks every field that revision 3\'s 39 '
          'contract rows name (`FIELD_COVERAGE.csv`). Every named field of a supplied record is carried by an existing template today (89 field mentions, '
          '65 distinct field names). The other named items are not template fields, and each has a supplier: retention events are recorded by a person '
          '(release A entry form); duplicate and reconciliation states are set by the intake; invoice lines and the carrying components are calculated; '
          'R04B\'s instruction types are a detection-rule setting (N01). The check finds no gap, and fails if one appears.\n\n'
          'Its limits: it matches the field names the contracts give (a few entries use plain words, such as "amount", that correspond to template '
          'fields); it covers the template path only, because the entry screens and document capture will be generated from the same field definitions '
          'once the schema register exists; and it does not yet check each field\'s authority and verification requirement. PG-DS-AC-12 makes the full '
          'check, for every way in, a release condition.')
R[143] = L[143]
R[145] = ('- For each gap: the entity and field, the period, the reason (nobody supplied it; no built way in yet; the source is not authoritative; it is '
          'unverified or stale; the underlying record does not exist), the likely holder of the information, the action owner who can supply or correct '
          'it, and the approver where one is needed. The builder assigns or confirms those roles; the way in is named, saying plainly when it is not built.')
A[145] = ('- Its scope: each readiness item belongs to a project, the organisation, a supplier, the portfolio or external data. A shared missing setting '
          '(a policy, a labour rate, the authority register) is raised once, with the projects it affects, not once per project.')
R[147] = ('**When it is reassessed:** at setup, after each intake batch or material change of state (not row by row; reassessment is queued and combined '
          'for large batches, but prompt), on a schedule, and whenever a record is corrected, quarantined, superseded or revoked (S06 §10, S04 §14).')
R[153] = ('3. **Nudges that name the period, the field and the fix,** for example: "3 May invoices from Acme Electrical have no cost code. Add the code '
          'on each invoice (assigned cost-code owner)." The responsible role is configurable. Each gap has a stable identity (entity, field, period and '
          'source), and a lifecycle: open, assigned, awaiting evidence, resolved, suppressed, reopened, superseded. A gap found again updates its existing '
          'nudge instead of sending a new one; a suppression window and re-notification rules apply, as S06 §9.1 requires for alerts. A nudge links '
          'straight to the form that fixes it, after sign-in. APG prioritises the gaps worth most, allows bulk correction where it is safe, and never asks '
          'for data it already holds.')
R[159] = ('Release A gives every current detection rule and M4 figure a designed Level 1 way in for every input it reads, with no phone capture and no '
          'integration. For the M6 market figures this holds only as far as their inputs can be inferred, until their contracts are written. It holds by '
          'construction: release A is defined to contain those inputs, so a check of membership could not fail and is not offered as evidence. The field '
          'check above is the real test of the fields; the gap list, `RELEASE_A_COVERAGE.csv`, has one row per contract row:')
A[164] = ('\n**Release A is not complete until two gates are passed:** the M6 input contracts are written and approved, and their fields checked like the '
          'rest; and the intake migration (item 1) has passed as its own milestone. Release A is also delivered progressively: the first pilot project gets '
          'the data its first chosen insights need, then the forms and document types grow. No builder is asked to populate all 100 entities.')
R[168] = ('1. **One intake for every kind, as its own gated milestone.** Bring the 24 kinds of the second delivery loop and the directly written records '
          'under the Section 04 intake: reconciliation, authority and resolution beyond suppliers. This is not neutral for the rules: today they use those '
          '24 kinds whenever the record\'s own checks pass, so reconciling them changes which records the rules and figures may use. It is a separate '
          'technical milestone under its own change request, with a regression baseline of today\'s rule and figure results taken first, every difference '
          'explained and signed off, and nothing in release A relying on the merged intake until it passes; afterwards the rules read the reconciled state, '
          'as they already do for the 11 reference kinds. PG-DS-AC-03 governs new ways in, not this migration. The other release A items do not wait for it.')
R[175] = ('**Recommended, for you to decide.** Both design reviews said the earlier recommendation (every small fact plus finished document capture) is '
          'too much for a first release. Claude now recommends a middle path:')
R[177] = ('- **Entry forms only for the facts the first pilot\'s insights need**, beyond setup and retention, added progressively as more insights are '
          'switched on. The five M6 supplements (specification requirements, quote tiers, quote terms, landed-cost components, import checks) are asked for '
          'only when a builder uses the market insights, and come from real quotes; APG does not invent default values for them, because they are facts '
          'from real quotes.')
R[178] = ('- **Document upload, not finished document capture:** upload and email intake with person-keyed verification, used for quote readings and as '
          'evidence attached to records. Finished capture with real extraction waits until an extraction vendor is chosen (EDR-22), because without it '
          'staff would key every value. Choosing finished capture later moves the document record (E83) into scope.')
R[180] = ('Even so, seven release A facts come only by file: purchase orders, credit notes, timesheets, bank transactions and deliveries, which usually '
          'come from the accounting, payroll or job system\'s export (Claude\'s judgement, to confirm with pilot builders), and market observations and FX '
          'rates, which are data sources rather than builder records. Discovery must confirm, for each, that the pilot builder can really produce the file; '
          'where it cannot, the readiness record shows the gap and its fallback.')
R[186] = (L[186] + ' Subcontractor claims, assessments and payments (E17 to E19) are not in release B by the mechanical rule (no current contract names '
          'them as a limit), so they sit in "later". Both reviews flagged them as a main source of profit leakage; promoting them to the front of release B '
          'is a decision for you (decision 7).')
R[208] = ('| PG-DS-AC-02 | Two inputs are equivalent when, after canonical mapping, they have the same values, units, currency, date and time, tax basis, '
          'authority and verification state. Equivalent inputs supplied through any two ways in give the same field values and the same rule outcome; only '
          'the provenance differs. Shown by a test. |')
R[215] = ('| PG-DS-AC-09 | The readiness record is reassessed at setup, after each intake batch or material state change, on its schedule, and when a '
          'record is corrected, quarantined, superseded or revoked; an insight is never shown as eligible while an input it needs is missing, unverified or '
          'stale. |')
A[217] = ('| PG-DS-AC-12 | Every field a current rule or figure reads has at least one built way in that carries it, with its authority and verification '
          'requirement met; shown by a generated field-coverage report that fails on a gap. |\n'
          '| PG-DS-AC-13 | A partly failed or failed intake (a batch with rejected rows, an unreadable document, a stopped feed, an unmatched record) is '
          'shown as such, with its count and reasons, and never as a successful intake. |')
A[230] = ('- **Adoption.** A complete way in can still fail if it takes too long. The pilot measures completion rates, correction effort, time to supply '
          'and the share of material inputs still missing.')
R[235] = ('2. **Release A scope.** The minimum build (entry forms for setup and retention only); the recommended middle path (entry forms for the first '
          'pilot\'s insights, document upload with person-keyed verification, M6 supplements only when used); or the earlier full option (every small '
          'fact plus finished document capture, which needs the extraction vendor). Claude recommends the middle path.')
A[239] = ('7. **Subcontractor claims.** Promote subcontractor claims, assessments and payments (E17 to E19) to the front of release B. Claude recommends '
          'yes.\n8. **Reviewers\' further ideas.** Which, if any, of the ideas below to take forward as their own change requests.')
R[245] = ('**Ideas raised by the reviewers, not designed here.** These widen the scope (new insights or features), so each would be its own change '
          'request:\n\n'
          '- **Back-to-back claim checks** (Gemini): compare each subcontractor claim with the matching client claim line. A new detection rule; its data '
          'is E13 and E17.\n'
          '- **Statutory declaration gating** (Gemini): hold a subcontractor\'s claim until a verified statutory declaration arrives. A new entity and a '
          'new rule; APG flags, a person decides payment (S10 human approval). The legal requirement differs by state and needs checking.\n'
          '- **One-tap actions in messages without signing in** (Gemini): not recommended. Anyone holding the link could approve or change data, which '
          'breaks the sign-in and approval controls (S04 §6, PG-DS-AC-05). The safe form, a link that opens the exact form after sign-in, is in this '
          'design.\n'
          '- **Adjudication evidence packs** (Gemini): export the full chain of evidence for a disputed claim or variation. A new feature built on the '
          'provenance this design keeps.\n'
          '- **A learning cost-code map** (Gemini): learn from the builder\'s own confirmed mappings to suggest better matches, a person still confirming '
          'low-confidence ones. Allowed within one builder\'s data only, never across builders (S04 §16).\n\n'
          '**Gaps in the locked blueprint itself:** data retention, archiving and retrieval after project close-out and when a customer leaves APG '
          '(GPT). The blueprint sections in this pack do not cover it; it needs its own change request.\n\n'
          '**Next:** a fresh-agent check of what changed in this draft, then your decisions. No further GPT or Gemini round unless a blocking problem '
          'appears. Corrections from revision 3\'s GPT check are folded in first, and the supply plan is regenerated if the registers change.')

R[238] = L[238].replace('PG-DS-AC-01 to 11', 'PG-DS-AC-01 to 13')
R[241] = L[241].replace('PG-DS-AC-01 to 11', 'PG-DS-AC-01 to 13')
GOV = '''## Data supply governance and lifecycle

The ways in are only half the system. The other half is knowing, for every value, who supplied it, whether it can be trusted, which version counts, who must fix a problem and which conclusions change when it changes. Most of this the blueprint already requires; this section ties it to the ways in.

- **Who does what.** For each kind of record the builder names who supplies it, who checks it, who may correct it, who approves it and who is accountable if it stays missing. One person can hold several roles; the roles stay distinct in the record (for example, a subcontractor claim entered by an administrator, checked by a contract administrator, approved by a commercial manager).
- **Data from outside the office.** Much of it starts with subcontractors, suppliers and consultants. In this design it reaches APG through the builder, by document, email, template or entry form; no external portal is designed.
- **Corrections, disputes and versions.** What was received, what changed, who changed it, why, and which version each insight used are all kept (S04 §13). A change to a record an insight used marks that insight for reassessment; an earlier conclusion stays explainable from the records it used at the time.
- **Access.** Organisation, legal entity, project and role boundaries hold on every way in, including information shared between related companies or joint ventures (S04 §6, §16).
- **Failed or incomplete supply.** A partial import, an unreadable document, a stopped feed, an unmatched record, a wrong version or a duplicate batch is shown as exactly that, with counts and reasons, and goes to the review queue (S04 §8, §9, §15; PG-DS-AC-13).
- **The builder's effort.** APG asks for the most valuable gaps first, allows safe bulk correction and never asks again for data it already holds.
- **The evidence trail.** Every conclusion traces back through its calculation and rule version to the verified, reconciled records and to the original documents, files, emails and source records, as they were at the time.
'''

out = []
for n in range(1, len(src) + 1):
    if n == 199:            # before "## What a new way in may and may not change"
        out.append(GOV)
    if n in R:
        if R[n] != '':
            out.append(R[n])
    else:
        out.append(L[n])
    if n in A:
        out.append(A[n])
assert src[198].startswith('## What a new way in'), src[198]
open('DRAFT4.md', 'w').write('\n'.join(out))
print('ok', len('\n'.join(out)))
