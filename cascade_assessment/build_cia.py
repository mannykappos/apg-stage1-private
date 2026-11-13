"""Section 18 cascade impact assessment, data supply design (draft 7) and Data Readiness CR revision 4: the requirement-level tables.
Builder work (Claude): BUILDER-EXECUTED: NOT INDEPENDENT.

From the locked package (the Master RTM and the 19 section documents, v1.0) and the change items defined below, it writes:
  CIA_PROPOSED_TEXT.csv   every paragraph, bullet, table row and acceptance criterion this change request proposes to add, with its
                          proposed ID, its section, the anchor it is inserted after (RTM ID, or paragraph index where the RTM has none)
                          and its text.  No existing locked paragraph is reworded or removed.
  CIA_RTM_IMPACT.csv      every existing RTM row (or unmapped locked paragraph) each change item touches: as an insertion point, or as a
                          dependent requirement reviewed with no text change.
  CIA_COUNTS.txt          per amended section, how many existing RTM rows sit after the first insertion point (their paragraph-index
                          anchors move, their IDs do not); and, per section, the locked paragraphs and table rows the RTM does not map
                          (a pre-existing observation, outside this change request).
It fails if an anchor or a heading named below is not in the locked package, or if a proposed ID is already used.
usage: python3 -I build_cia.py <folder holding the extracted locked package> <output folder>"""
import csv, glob, os, re, sys, collections
import docx

PKG, OUT = sys.argv[1], sys.argv[2]
RTM = os.path.join(PKG, 'MASTER_REQUIREMENTS_TRACEABILITY_MATRIX.csv')
rows = list(csv.DictReader(open(RTM, encoding='utf-8-sig')))
for x in rows:
    m = re.search(r'paragraph_index=(\d+);(?: style=([^;]+);)? text_prefix=(.*)', x['source_anchor'], re.S)
    x['pi'], x['style'], x['prefix'] = int(m.group(1)), (m.group(2) or ''), m.group(3)
byid = {x['requirement_id']: x for x in rows}
bysec = collections.defaultdict(list)
for x in rows:
    bysec[x['source_section']].append(x)
for s in bysec:
    bysec[s].sort(key=lambda x: x['pi'])
docs = {}
for f in sorted(glob.glob(os.path.join(PKG, '*Section_*_v1.0_LOCKED.docx'))):
    docs[re.search(r'Section_(\d+)', f).group(1)] = docx.Document(f)

def para(sec, pi):
    return docs[sec].paragraphs[pi].text

def level(x):
    m = re.match(r'Heading (\d)', x['style'])
    return int(m.group(1)) if m else (1 if x['style'].startswith('Title') else None)

def span(sec, num):
    """RTM rows from heading `num` to the next heading of the same or a higher level"""
    s = bysec[sec]
    for i, h in enumerate(s):
        if level(h) and re.match(r'\s*%s\.?\s' % re.escape(num), h['prefix']):
            end = next((y['pi'] for y in s[i + 1:] if level(y) and level(y) <= level(h)), 10 ** 9)
            return [x for x in s if h['pi'] <= x['pi'] < end]
    sys.exit('heading %s not found in section %s' % (num, sec))

def anchor(sec, a):
    """an RTM ID, or ('p', paragraph index) for a locked paragraph the RTM does not map, or ('t', table, row) for a table row"""
    if isinstance(a, str):
        if a not in byid or byid[a]['source_section'] != sec:
            sys.exit('anchor %s not in section %s' % (a, sec))
        return a, byid[a]['pi'], byid[a]['requirement_summary'][:110]
    if a[0] == 'p':
        t = para(sec, a[1])
        if not t.strip() or any(x['pi'] == a[1] for x in bysec[sec]):
            sys.exit('paragraph %s of section %s is empty or already mapped' % (a[1], sec))
        return 'S%s paragraph %d (no RTM row)' % (sec, a[1]), a[1], t[:110]
    if a[0] == 't':
        tb = docs[sec].tables[a[1]]
        t = ' | '.join(c.text for c in tb.rows[a[2]].cells)
        return 'S%s table %d row %d (no RTM row)' % (sec, a[1] + 1, a[2]), None, t[:110]
    sys.exit('bad anchor %r' % (a,))

# ---------------------------------------------------------------------------------------------------------------------------------
# The proposed additions.  (section, inserted after, proposed ID, kind, text, change item)
SEV_BASIS = 'the current approved contract value (original contract value plus approved variations)'
ADD = [
    # Section 01: discovery
    ('01', 'APG-S01-L0089', 'APG-S01-DS001', 'heading 2', '3.7 Data supply readiness', 'C16'),
    ('01', 'APG-S01-L0089', 'APG-S01-DS002', 'bullet', 'Which systems the pilot builders use for each kind of data, with a sample export from each, to confirm the systems survey of the data readiness change request.', 'C16'),
    ('01', 'APG-S01-L0089', 'APG-S01-DS003', 'bullet', 'For each file the first release relies on, whether the pilot builder can actually produce it; where it cannot, the readiness record shows the gap and its fallback.', 'C16'),
    ('01', 'APG-S01-L0089', 'APG-S01-DS004', 'bullet', 'What site staff record today, on what device, and whether site capture must work offline; this is an early gate, and if a first-pilot insight depends on site facts recorded as they happen, that capture is brought forward.', 'C16'),
    ('01', 'APG-S01-L0089', 'APG-S01-DS005', 'bullet', 'How often each kind of data changes, which sets the case for each integration.', 'C16'),
    ('01', 'APG-S01-L0089', 'APG-S01-DS006', 'bullet', 'Whether users and roles come from the Anchor platform, and how organisations, legal entities and projects are represented in its tenant model.', 'C16'),
    # Section 02: functional requirements register (table)
    ('02', ('t', 2, 25), 'PG-FR-026', 'table row', 'For each insight, tell the builder what data it needs, what is missing, who usually holds it and how to supply it; whenever a check or figure cannot be fully done, say what is missing, why it matters and what the builder is to do.', 'C07, C08'),
    ('02', ('t', 2, 25), 'PG-FR-027', 'table row', 'Provide, for every data entity Profit Guardian needs, at least one way to supply it that does not depend on the builder\'s software; adding a way in never changes a detection rule or financial figure.', 'C01'),
    # Section 03: domain model
    ('03', ('t', 0, 20), 'APG-S03-DS001', 'table rows', 'Variation and instruction | Client variation, site instruction or direction, with its commercial states (Section 11 §8) and the cost incurred against it. ; Programme activity and progress | Activity, relationship, calendar and progress record of an approved programme version (Section 07 §3). ; Payment claim and certificate | Progress claim, payment schedule or certificate and its states (Section 11 §5). ; Labour record and rate | Timesheet entry, work allocation and labour rate, subject to Section 09 §14. ; Document | Original file or message kept as evidence, with its hash. ; Policy and settings record | Versioned, approved configuration: source registry entry, source authority rule, cost-code map, financial policy and rule settings. ; Readiness record | Per insight and project, the state of each input and each data gap (Section 04 §14.1). ; Data gap | A missing, unverified, conflicting, stale or non-authoritative input, with its identity and lifecycle (Section 04 §14.1).', 'C05'),
    ('03', 'APG-S03-C0012', 'APG-S03-DS002', 'paragraph', 'The controlled entity register, an annex to this section, lists every entity Profit Guardian needs, its blueprint basis, its required field groups, its ways in and their state; it is a data inventory, mapped to existing Anchor entities in Section 01 discovery, not a database schema. A field register gives each entity\'s fields; it becomes the validated schema register before any entry screen is generated from it.', 'C05, C06'),
    ('03', ('t', 1, 14), 'APG-S03-DS003', 'table rows', 'channel | The way in that supplied the record (import file, document or email, entry screen, setup question, site capture, integration). ; supplied_by | The person or system that supplied it, and its trust level. ; verified_by / verified_at | The person who verified a material value and when, where verification is required. ; retrospective | Set when the record was entered after the event it describes.', 'C20'),
    ('03', 'APG-S03-L0072', 'APG-S03-DS004', 'bullet', 'Cost of extra work, attributed to the instruction or variation it was incurred for.', 'C13'),
    # Section 04: ingestion
    ('04', 'APG-S04-L0122', 'APG-S04-DS001', 'heading 2', '14.1 Data readiness — mandatory', 'C07'),
    ('04', 'APG-S04-L0122', 'APG-S04-DS002', 'paragraph', 'Maintain a readiness record for each insight (detection rule, financial figure, market figure and any later insight) and project. It states the insight\'s state from its own gate (eligible, qualified, blocked or unavailable) and, for each input, how far it has reached: capture available, validation available, authority established, reconciliation available, decision-eligible. An insight is never shown as eligible while an input it needs is missing, unverified, conflicting, stale or not authoritative.', 'C07'),
    ('04', 'APG-S04-L0122', 'APG-S04-DS003', 'bullet', 'For each gap, record the entity and field, the period, the source, the reason (missing, unverified, conflicting, stale, not authoritative, or the underlying record does not exist), the likely holder, the action owner, the approver where one is needed, and the way in that supplies it, saying plainly when that way in is not built.', 'C07'),
    ('04', 'APG-S04-L0122', 'APG-S04-DS004', 'bullet', 'Give each gap a stable identity (entity, field, period and source) and a lifecycle: open, assigned, awaiting evidence, resolved, suppressed, reopened, superseded. A gap found again updates its existing record and nudge; suppression windows and re-notification rules follow Section 06 §9.1.', 'C07'),
    ('04', 'APG-S04-L0122', 'APG-S04-DS005', 'bullet', 'Reassess readiness at setup, after each intake batch or material change of state, on a schedule, and whenever a record is corrected, quarantined, superseded or revoked. Raise a shared missing setting once, with the projects it affects.', 'C07'),
    ('04', 'APG-S04-L0122', 'APG-S04-DS006', 'bullet', 'An insight may set a tighter freshness limit than its source\'s default for the inputs it depends on; an overall fresh status never hides a stale critical input. Starting thresholds are owner-approved parameters, each with a documented owner and rationale (Section 16 §5), reviewed in the pilot.', 'C09'),
    ('04', 'APG-S04-L0122', 'APG-S04-DS007', 'bullet', 'Show gaps with their factors side by side, as Section 10 §4 requires for findings: the amount affected, urgency, confidence in that amount, whether the person can act now, and what depends on it. A gap is never called a loss or confirmed leakage; any amount comes from a traceable Section 05 calculation or is labelled an estimate.', 'C07'),
    ('04', 'APG-S04-L0122', 'APG-S04-DS008', 'heading 2', '14.2 Telling the builder what is needed — mandatory', 'C08'),
    ('04', 'APG-S04-L0122', 'APG-S04-DS009', 'paragraph', 'Whenever a rule, figure or other insight cannot fully do a check or produce a figure, it must say so: what is missing, why it matters, what is to be done and by whom. No case may be silent, and nothing may be shown as complete when it is not. Each such message is proven by a test when it is built. A list of the messages, generated by scanning the code, is kept as a controlled artefact and fails when the code gives a message it does not cover.', 'C08'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS010', 'heading 2', '18.1 Ways of supplying data — mandatory', 'C01'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS011', 'paragraph', 'Every fact a person or system supplies, through any way in (import file, document or email, entry screen, setup question, site capture, integration), enters through the intake this section defines, with the same envelope (organisation, project, channel, the person or system, and the time) and the same control checkpoints; nothing writes a supplied fact to the store directly. Records Profit Guardian calculates are written by their calculation runs, with the run recorded (Section 03 §14.3).', 'C01'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS012', 'bullet', 'Every entity in the controlled entity register has at least one Level 1 way in that needs no particular builder software: an import template, document or email capture, an entry screen, a setup question, or a record Profit Guardian calculates. Site capture (Level 2) and integrations (Level 3) reduce effort; neither is ever the only way in.', 'C01'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS013', 'bullet', 'Adding a way in, or a builder changing systems, may change the intake; it must not change any detection rule or financial figure, its logic or its test results. Teaching a rule or figure to use data it does not read today is a change to that rule under its own change request. Where two ways in supply the same field, the Source Authority Register decides which governs, never the most recent arrival.', 'C01'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS014', 'bullet', 'A way in that is not built is never offered to the builder as available.', 'C01'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS015', 'bullet', 'For each kind of record, name its supplier, checker, corrector, approver and the owner accountable if it stays missing; one person may hold several of these roles, and they stay distinct in the record.', 'C20'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS016', 'heading 2', '18.2 Channel controls — mandatory', 'C03'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS017', 'bullet', 'Email capture verifies the sender and never takes the organisation from the address alone; a verified sender does not make a document genuine or authorised (§5 and §12 still apply). Original messages and attachments are kept.', 'C03'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS018', 'bullet', 'Every uploaded file, attachment and photo is scanned and parsed in isolation within size, archive and resource limits before it is read; a malformed or unsupported file is rejected with a reason.', 'C03'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS019', 'bullet', 'Entry screens and setup questions carry the signed-in person, pass the same validation as an imported row, and need approval where the register requires. They never edit a held record: correcting a quarantined or pending record goes through the review workflow (§9, §13).', 'C03'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS020', 'bullet', 'Where a person keys a material value from a document, a second person with the verifier role confirms it before it counts. Each value keeps its own confirmation and provenance, also when confirmation is done in batches.', 'C19'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS021', 'bullet', 'Site capture devices are enrolled to the organisation; on a shared device the signed-in user is recorded; the time is checked against the server; each record says how its place was established. Site capture\'s privacy requirements follow Section 09 §14 and are settled before it is built.', 'C15'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS022', 'bullet', 'A record entered after the event it describes is marked retrospective. A backdated entry never rewrites a result already shown: the earlier result and the records it used stay on record, and the affected insight is reassessed and labelled.', 'C20'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS023', 'heading 2', '18.3 Setup questions — mandatory', 'C04'),
    ('04', 'APG-S04-L0148', 'APG-S04-DS024', 'paragraph', 'Policies, maps, rates and settings the builder sets (the source registry, the Source Authority Register, the cost-code map, users and roles where the platform does not supply them, the financial policy with its status maps, and the rule settings) are supplied through setup questions, versioned, submitted through the intake, and take effect only after approval by the required role. Onboarding asks only what the insights the builder switches on need. A record whose cost code is not mapped yet completes intake and is held only from the figures that need the code.', 'C04'),
]
DSAC = [
    'Every fact a person or system supplies enters through the Section 04 intake; nothing writes a supplied fact to the store directly. Records APG calculates are written by its calculation runs, with the run recorded.',
    'Two inputs that describe the same source fact (the same values, units, currency, date and time and tax basis) and meet the same authority and verification conditions, supplied through any two ways in, are mapped to identical field values and give the same rule outcome; only the provenance differs. Shown by a test.',
    'Adding a way in changes no detection rule or financial figure logic and no rule test result. Changes to the intake code are allowed. (The one-off move of today\'s 24 kinds onto the reconciled intake is governed by its own change request.)',
    'Every value records its channel, the person or system that supplied it, and the time.',
    'No manual way in (templates, documents, entry screens, site capture, setup answers) bypasses validation, approval or audit (§18). Setup answers are versioned and take effect only after approval by the required role.',
    'Every way in meets PG-DI-AC-01 to 18, including tenant isolation tested on that path (PG-DI-AC-14), human verification of extracted values (PG-DI-AC-07) and quarantine isolation (PG-DI-AC-03 to 05).',
    'Every uploaded file, email attachment and photo is scanned and parsed in isolation within size, archive and resource limits before it is read; a malformed or unsupported file is rejected with a reason.',
    'A held record is corrected only through the review queue, never by an entry form.',
    'The readiness record is reassessed at setup, after each intake batch or material state change, on its schedule, and when a record is corrected, quarantined, superseded or revoked; an insight is never shown as eligible while an input it needs is missing, unverified or stale.',
    'Each data gap has a stable identity (entity, field, period, source) and moves through open, assigned, awaiting evidence, resolved, suppressed, reopened and superseded; a gap found again updates its existing nudge instead of creating a new one; suppression windows and re-notification rules are defined and tested (Section 06 §9.1).',
    'A way in that is not built is never offered to the builder as available.',
    'Every field a current rule or figure reads, including setting fields, has at least one built way in that carries it, with its authority and verification requirement met; and each way in, when built, carries every field of the entities it serves. Shown by a generated field-coverage report that fails on a gap; a first-release gate.',
    'A partly failed or failed intake (a batch with rejected rows, an unreadable document, a stopped feed, an unmatched record) is shown as such, with its count and reasons, and never as a successful intake.',
    'Whenever a rule or figure cannot fully do a check or a figure, it says so: what is missing, why it matters and what the builder is to do. No case is silent, and nothing is shown as complete when it is not. Each message is proven by a test when it is built; a list generated by scanning the code holds every message the scan finds and fails if the code gives one it does not cover.',
]
DSAC_ITEM = ['C01', 'C01', 'C01', 'C20', 'C04', 'C01', 'C03', 'C03', 'C07', 'C07', 'C01', 'C06', 'C03', 'C08']
for i, t in enumerate(DSAC):
    ADD.append(('04', 'PG-DI-AC-18', 'PG-DS-AC-%02d' % (i + 1), 'acceptance criterion', t, DSAC_ITEM[i]))
ADD += [
    ('04', 'APG-S04-L0175', 'APG-S04-DS025', 'bullet', 'Bring every record kind under this section\'s intake, including the kinds checked today only inside the calculations and the records written straight to the store; take a regression baseline of today\'s rule and figure results first, explain and sign off every difference, and do it under its own change request.', 'C02'),
    ('04', 'APG-S04-L0175', 'APG-S04-DS026', 'bullet', 'Keep the controlled data-supply registers (entity, field, rule input contracts, field coverage, supply routes, messages) current, and regenerate the field-coverage report for each way in as it is built; the report fails on a gap.', 'C06, C21'),
    # Section 05: calculation engine
    ('05', 'APG-S05-L0034', 'APG-S05-DS001', 'bullet', 'Present the authoritative figure first. Beside it, show each item that is not final in its own category (awaiting approval, on hold, disputed, rejected) with its amount and the effect it would have if it went through. These effects are labelled what-if amounts, are never added into the authoritative figure, and are isolated as Section 10 §7.1 requires.', 'C14'),
    ('05', 'APG-S05-L0089', 'APG-S05-DS002', 'bullet', 'Where a cost is attributed to an instruction or variation, it stays in actual cost or commitments exactly once; the attribution groups it and never adds it a second time. A cost not attributed stays with the original scope.', 'C13'),
    # Section 06: intelligence
    ('06', 'APG-S06-C0040', 'APG-S06-DS001', 'paragraph', 'Rule thresholds and windows ship with defaults approved by the product owner; the builder\'s authorised approver accepts them at onboarding and may adjust them within the approved ranges. A setting with no sensible default (the builder\'s own categories, or pairs a person declares) is supplied by the builder when the rule is switched on.', 'C10'),
    ('06', 'APG-S06-C0087', 'APG-S06-DS002', 'paragraph', 'The levels at which findings are graded by severity are set by the builder at setup: for each grade an amount, a percentage of the job, or both; with both set, the grade applies as soon as either is reached. The percentage is of ' + SEV_BASIS + ' [owner to confirm]. No default or suggested levels are supplied. The levels are approved as other settings are (Section 04 §18.3) [approval route: owner decision]. Until they are set and approved, findings still show, marked ungraded, with what to do.', 'C11'),
    # Section 11: commercial
    ('11', ('p', 52), 'APG-S11-DS001', 'paragraph', 'For a rejected variation, the builder records its outcome: disputed, carried at the builder\'s own cost, resubmitted, or withdrawn. Profit Guardian records that outcome and does not judge the dispute (§11); the cost already incurred stays visible.', 'C13'),
    ('11', 'APG-S11-C0055', 'APG-S11-DS002', 'heading 2', '8.2 Extras and variations view — mandatory', 'C13'),
    ('11', 'APG-S11-C0055', 'APG-S11-DS003', 'paragraph', 'Show the original contract scope\'s budget and profit on their own, and each extra or variation separately: its value in each state, its status, the cost incurred against it so far and its effect on the job\'s profit. The two are never blended, and no state is added into another.', 'C13'),
]

# ---------------------------------------------------------------------------------------------------------------------------------
# Dependents: (change item, section, heading number or list of IDs/anchors, why it was reviewed).  No text change in any of them.
DEP = [
    ('C01', '04', ['3', '6', '8', '9', '16', '17', '18'], 'every way in uses these stages and controls'),
    ('C01', '02', ['4'], 'workflow A (connect, validate, reconcile, flag gaps)'),
    ('C01', '15', ['15.3', '15.4', '15.5', '15.10'], 'identity, authorisation, tenant isolation and integration security on each new channel'),
    ('C01', '16', ['9'], 'integration degradation: a stopped feed falls back to its file'),
    ('C02', '04', ['5', '11', '13'], 'authority, entity resolution and corrections applied to the 24 kinds that today skip them'),
    ('C02', '05', ['13'], 'reproducibility: the regression baseline and explained differences'),
    ('C02', '14', ['14.13'], 'change control and regression protection'),
    ('C02', '17', ['5', '8'], 'financial-core correctness, fixture control and replay tests on the migrated kinds'),
    ('C03', '04', ['12'], 'documents and extracted values'),
    ('C03', '15', ['15.9'], 'AI and extraction trust boundary for document capture'),
    ('C03', '16', ['6'], 'background processing and retries for email and upload intake'),
    ('C04', '04', ['4', '5'], 'source registry and Source Authority Register built through setup questions'),
    ('C04', '05', ['4'], 'canonical calculation inputs: the financial policy and status maps'),
    ('C04', '02', ['3'], 'actors and permissions: who approves each setting'),
    ('C05', '03', ['16'], 'instructions to map the logical model to existing Anchor entities'),
    ('C05', '00', ['00.12'], 'required control artefacts: data dictionary and entity contracts'),
    ('C06', '17', ['3', '4'], 'RTM fields and test classes for the field-coverage gate'),
    ('C07', '04', ['14'], 'freshness, completeness and data quality'),
    ('C07', '06', ['9.1', '10'], 'noise control and reassessment triggers reused for gaps and nudges'),
    ('C07', '10', ['3', '4'], 'eligibility before ranking and separate ranking factors'),
    ('C07', '16', ['5'], 'operational freshness and completeness states'),
    ('C07', '14', ['14.4'], 'phase 1 includes shared data-quality status'),
    ('C08', '05', ['5.2'], 'qualified forecasts expose what is missing'),
    ('C08', '06', ['PG-AI-AC-04', 'PG-AI-AC-07'], 'missing data creates a qualification; findings without an amount'),
    ('C08', '07', ['13'], 'schedule data quality and freshness'),
    ('C08', '08', ['14'], 'procurement finding and source governance'),
    ('C08', '09', ['15'], 'labour data quality and uncertainty'),
    ('C08', '11', ['6'], 'missing claim evidence must be visible'),
    ('C08', '12', ['12.4'], 'cash inputs, provenance and gaps'),
    ('C08', '13', ['13.4'], 'quality evidence and classification'),
    ('C09', '04', ['APG-S04-L0119', 'PG-DI-AC-13'], 'decision-aware freshness thresholds'),
    ('C09', '16', ['APG-S16-L0038'], 'thresholds by decision and data type, with an owner and rationale'),
    ('C09', '08', ['APG-S08-C0079'], 'procurement freshness depends on decision type'),
    ('C10', '06', ['PG-AI-AC-01', 'PG-AI-AC-19'], 'rules configurable, versioned, regression-tested'),
    ('C10', '02', ['3'], 'permission and segregation principles'),
    ('C11', '06', ['5.1', ('p', 85), 'PG-AI-AC-08'], 'severity mapping, thresholds approved, severity kept separate'),
    ('C11', '10', ['PG-RS-AC-02'], 'magnitude, urgency and confidence distinct'),
    ('C11', '02', ['3', ('t', 2, 25)], 'segregation of preparation and approval (PG-FR-025)'),
    ('C13', '11', ['3', '4', '8', '9', '10', '11'], 'baseline, variations, commercial states, leakage, finance link, disputes'),
    ('C13', '03', ['6.1', '6.4'], 'revenue concepts; no mixed-basis calculations'),
    ('C13', '05', ['3.2', '7'], 'forecast final margin; leakage calculations'),
    ('C13', '17', ['APG-S17-C0046', 'APG-S17-L0047'], 'a cost-allocation change triggers the financial-core suite; fixture changes reviewed'),
    ('C14', '05', ['5.1', '5.2', '11'], 'one authoritative forecast; qualified forecasts; scenarios'),
    ('C14', '03', ['5.4'], 'required view metadata'),
    ('C14', '04', ['9'], 'compare authoritative and provisional outcomes without confusing them'),
    ('C14', '10', ['7.1'], 'scenario isolation'),
    ('C15', '09', ['14', 'PG-LR-AC-16'], 'worker privacy and access control for site capture'),
    ('C15', '15', ['15.6'], 'data classification and minimisation of location and photos'),
    ('C16', '01', ['2', '7'], 'discovery gates and exit criteria the new questions join'),
    ('C17', '14', ['14.3', '14.4', '14.5', '14.6'], 'implementation phases the releases map onto'),
    ('C18', '03', ['10.1'], 'retention record'),
    ('C18', '12', ['12.8'], 'retention intelligence'),
    ('C18', '05', ['9'], 'retentions, security and DLP calculations'),
    ('C18', '12', ['APG-S12-L0077'], 'retention needs currency and project or scope'),
    ('C19', '04', ['12', 'PG-DI-AC-07'], 'human verification of document values'),
    ('C19', '15', ['APG-S15-L0105', 'APG-S15-L0106'], 'uploaded documents are untrusted; prompt injection in the threat model'),
    ('C20', '04', ['13'], 'source revisions, conflicts and corrections'),
    ('C20', '05', ['PG-PC-AC-17', 'PG-PC-AC-18'], 'reproduction after corrections; input and rule changes distinguishable'),
    ('C21', '00', ['00.12'], 'control artefacts the registers satisfy'),
    ('C21', '05', ['15'], 'calculation catalogue listing each metric\'s inputs'),
    ('M11', '15', ['15.6', ('p', 71)], 'retention period, archive and deletion per data category (close-out and customer exit)'),
]

# ---------------------------------------------------------------------------------------------------------------------------------
os.makedirs(OUT, exist_ok=True)
used = set(byid)
out = []
for sec, after, nid, kind, text, item in ADD:
    if nid in used:
        sys.exit('proposed ID already used: ' + nid)
    used.add(nid)
    a, pi, pref = anchor(sec, after)
    out.append({'proposed ID': nid, 'section': sec, 'inserted after': a, 'which reads': pref, 'kind': kind, 'proposed text': text, 'change item': item})
with open(os.path.join(OUT, 'CIA_PROPOSED_TEXT.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)

imp = []
for sec, after, nid, kind, text, item in ADD:
    a, pi, pref = anchor(sec, after)
    imp.append({'change item': item, 'section': sec, 'RTM ID or source anchor': a, 'relation': 'insertion point (text added after it; its own wording unchanged)', 'text begins': pref})
for item, sec, keys, why in DEP:
    for k in keys:
        if isinstance(k, tuple):
            a, pi, pref = anchor(sec, k)
            imp.append({'change item': item, 'section': sec, 'RTM ID or source anchor': a, 'relation': 'dependent: reviewed, no text change (' + why + ')', 'text begins': pref})
        elif k in byid:
            anchor(sec, k)
            imp.append({'change item': item, 'section': sec, 'RTM ID or source anchor': k, 'relation': 'dependent: reviewed, no text change (' + why + ')', 'text begins': byid[k]['requirement_summary'][:110]})
        else:
            for x in span(sec, k):
                imp.append({'change item': item, 'section': sec, 'RTM ID or source anchor': x['requirement_id'], 'relation': 'dependent: reviewed, no text change (' + why + ')', 'text begins': x['requirement_summary'][:110]})
seen, ded = set(), []
for r in imp:
    key = (r['change item'], r['RTM ID or source anchor'], r['relation'][:9])
    if key not in seen:
        seen.add(key); ded.append(r)
with open(os.path.join(OUT, 'CIA_RTM_IMPACT.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(ded[0]), lineterminator='\n'); w.writeheader(); w.writerows(ded)

# counts
lines = []
amended = sorted({a[0] for a in ADD})
lines.append('Proposed additions: %d (%d new acceptance criteria PG-DS-AC-01 to 14, %d new functional requirements PG-FR-026 and 027)' %
             (len(ADD), sum(1 for a in ADD if a[2].startswith('PG-DS')), sum(1 for a in ADD if a[2].startswith('PG-FR'))))
lines.append('Sections amended (v1.0 -> v1.1): ' + ', '.join(amended))
lines.append('Impact rows: %d (%d insertion points, %d dependent requirements reviewed with no text change), %d distinct RTM IDs or anchors' %
             (len(ded), sum(1 for r in ded if r['relation'].startswith('insertion')), sum(1 for r in ded if r['relation'].startswith('dependent')),
              len({r['RTM ID or source anchor'] for r in ded})))
lines.append('Sections reviewed as dependents only: ' + ', '.join(sorted({r['section'] for r in ded} - set(amended))))
lines.append('')
lines.append('Existing RTM rows whose paragraph-index anchor moves (they sit after the first inserted paragraph; their IDs do not change):')
for sec in amended:
    pis = [anchor(sec, a[1])[1] for a in ADD if a[0] == sec and anchor(sec, a[1])[1] is not None]
    if not pis:
        lines.append('  S%s: none (table rows only)' % sec)
        continue
    first = min(pis)
    lines.append('  S%s: %d of %d rows (after paragraph %d)' % (sec, sum(1 for x in bysec[sec] if x['pi'] > first), len(bysec[sec]), first))
lines.append('')
lines.append('Pre-existing observation (outside this change request): locked paragraphs and table rows the RTM does not map, Sections 00-17')
tp = tt = 0
for sec in sorted(docs):
    if sec == '18':
        continue
    d = docs[sec]; mapped = {x['pi'] for x in bysec[sec]}
    un = [i for i, p in enumerate(d.paragraphs) if p.text.strip() and i not in mapped]
    trows = sum(len(t.rows) - 1 for t in d.tables)
    tp += len(un); tt += trows
    lines.append('  S%s: %d paragraphs not mapped (of %d non-empty), %d table body rows not mapped' % (sec, len(un), sum(1 for p in d.paragraphs if p.text.strip()), trows))
lines.append('  total: %d paragraphs (cover lines and lock-record lines included), %d table body rows' % (tp, tt))
open(os.path.join(OUT, 'CIA_COUNTS.txt'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
