#!/usr/bin/env python3
"""Checks the M0 programme tables, the candidate catalogue and the draft translation packs. Python 3 standard library only; read-only.
Usage: python3 -I tools/programme_check.py <package_root>      Exit 0 only if every check passes."""
import csv, hashlib, os, re, sys
ROOT = sys.argv[1]
rd = lambda p: list(csv.DictReader(open(os.path.join(ROOT, p), encoding='utf-8-sig', newline='')))
fails = []; n = 0
def chk(cid, ok, text):
    global n; n += 1
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text)
    if not ok: fails.append(cid)
rtm = rd('data/RTM_v2.1_CANDIDATE.csv')
chk('P01', hashlib.sha256(open(os.path.join(ROOT, 'data/RTM_v2.1_CANDIDATE.csv'), 'rb').read()).hexdigest() == open(os.path.join(ROOT, 'data/INPUT_HASHES.txt')).read().split()[0], 'RTM copy matches its recorded SHA-256')
ms = rd('programme/PROGRAMME_MILESTONES.csv'); edr = rd('programme/ENGINE_HANDOFF_REGISTER.csv'); sr = rd('programme/STATUS_REGISTER.csv')
cap = rd('gap_map/APG_CAPABILITY_GAP_MAP.csv'); bl = rd('gap_map/APG_BUILD_BACKLOG.csv')
chk('P02', [m['milestone_id'] for m in ms] == [f'M{i}' for i in range(13)] and all(m['objective'] and m['acceptance_criteria'] and m['stop_conditions'].startswith('Stop and report if') for m in ms), 'milestones M0 to M12 in order; each has an objective, acceptance criteria and stop conditions')
chk('P03', all(m['status'] in ('Delivered - builder-checked', 'In this delivery', 'Not started') for m in ms), 'no milestone is shown as complete, approved or accepted')
covered = set()
for m in ms: covered |= set(re.findall(r'CAP-\d\d', m['covers_capabilities']))
allcaps = {c['cap_id'] for c in cap}
chk('P04', covered == allcaps, f'every one of the {len(allcaps)} capabilities is assigned to a milestone ' + str(sorted(allcaps - covered)))
chk('P05', set(re.findall(r'CAP-\d\d', ' '.join(m['covers_capabilities'] for m in ms))) <= allcaps, 'milestones cite only capabilities that exist')
ids = [e['edr_id'] for e in edr]
chk('P06', len(ids) >= 27 and ids == [f'EDR-{i:02d}' for i in range(1, len(ids) + 1)], f'{len(ids)} handoff entries, IDs EDR-01 to EDR-{len(ids):02d} in order (27 at M4, more are appended by later milestones)')
req = ['what_apg_needs', 'why_the_engine_is_needed', 'contract_summary', 'contract_test', 'decisions_for_amir', 'owner']
thin = [e['edr_id'] for e in edr if any(len(e[k].strip()) < 25 for k in req) or len(e['port']) < 8 or len(e['title']) < 12 or not re.fullmatch(r'M\d+(; M\d+)*', e['needed_by_milestones'])]
chk('P07', not thin, 'every handoff entry has a port, need, reason, contract, contract test, milestones, decisions and an owner ' + str(thin))
chk('P08', all(e['status'] in ('Open - described only', 'Open - contract test written') and e['evidence_seen'].startswith('No Engine code') for e in edr), 'every handoff entry is open and records that no Engine code was seen')
def clause_ok(tok):
    sec, cl = tok.split(':', 1)
    for r in rtm:
        if r['source_section'] != sec: continue
        c = r['clause'].strip(); sc = (r.get('subclause') or '').strip()
        if c.startswith(cl + '. ') or c.startswith(cl + ' ') or c == cl or sc == cl or sc.startswith(cl + ' '): return True
    return False
bad = [(e['edr_id'], t) for e in edr for t in [x.strip() for x in e['blueprint_refs'].split(';') if x.strip()] if not re.fullmatch(r'\d\d:[0-9.]+', t) or not clause_ok(t)]
chk('P09', not bad, 'every blueprint clause cited by a handoff entry exists in the RTM clause list ' + str(bad))
bad = [(e['edr_id'], c) for e in edr for c in re.findall(r'CAP-\d\d', e['capabilities']) if c not in allcaps] + [(e['edr_id'], b) for e in edr for b in re.findall(r'BL-\d\d', e['backlog_ids']) if b not in {x['backlog_id'] for x in bl}]
chk('P10', not bad, 'capabilities and backlog items cited by handoff entries exist ' + str(bad))
first = {}
for m in ms[1:]:
    for e in re.findall(r'EDR-\d\d', m['handoff_register_entries']): first[e] = m['milestone_id']
mism = [e['edr_id'] for e in edr if first.get(e['edr_id']) != e['needed_by_milestones'].split(';')[0].strip()]
chk('P11', not mism and set(first) == set(ids), 'each handoff entry is first described in the milestone its record names, and every entry is assigned once ' + str(mism))
chk('P12', all(e['contract_test'] for e in edr) and len({e['port'] for e in edr}) == len(edr), 'each entry names a contract test; port names are unique')
claim = re.compile(r'\b(is built|are built|has been built|implemented in|tested in production|verified|operational|production[- ]ready|approved by|accepted|closed)\b', re.I)
txt = [(e['edr_id'], k) for e in edr for k in ('what_apg_needs', 'why_the_engine_is_needed', 'contract_summary', 'status') if claim.search(e[k])]
chk('P13', not txt, 'no handoff entry claims anything is built, verified, approved or closed ' + str(txt))
ladder = {'Specified', 'Implemented', 'Local-tested', 'Integration-tested', 'Staging-verified', 'Operationally verified', 'Accepted', 'Closed', 'Research record'}
chk('P14', all(s['evidence_ladder_status'] in ladder and s['evidence_ladder_status'] in ('Specified', 'Local-tested', 'Research record') for s in sr) and all(s['claim_limit'] for s in sr), 'status register: every row is on the ladder, none above Local-tested, each with a claim limit')
# catalogue
cat = rd('catalogue/CANDIDATE_SYSTEMS_CATALOGUE.csv'); res = {}
for f in os.listdir(os.path.join(ROOT, 'research')):
    if f.endswith('.csv'):
        for r in csv.DictReader(open(os.path.join(ROOT, 'research', f), encoding='utf-8-sig', newline='')): res[(r['class'], r['system'])] = r
chk('C01', len(cat) == len(res) == 56 and len({c['catalogue_id'] for c in cat}) == 56, f'catalogue has {len(cat)} rows, one per research row, unique IDs')
diff = [c['catalogue_id'] for c in cat if any(res[(c['class'], c['system'])][k] != c[k] for k in res[(c['class'], c['system'])] if k != 'confidence')]
chk('C02', not diff and all(res[(c['class'], c['system'])]['confidence'] == c['confidence_detail'] for c in cat), 'every catalogue cell equals the research cell it came from; original confidence text kept in full ' + str(diff[:3]))
def weakest(s):
    g = set(re.findall(r'(?<![A-Za-z])([ABC])(?![A-Za-z])', s)); return max(g) if g else ''
chk('C03', all(c['confidence_overall'] == weakest(c['confidence_detail']) and c['confidence_overall'] in 'ABC' and c['confidence_overall'] for c in cat), 'confidence_overall is the weakest grade named in the original text on every row')
chk('C04', all(c['selection_status'].startswith('candidate only') and c['pilot_confirmed'] == 'no' for c in cat), 'no system is shown as selected or confirmed with a builder')
chk('C05', all(re.match(r'https?://', c['api_docs_url'].split()[0]) or c['api_docs_url'].lower().startswith(('none', 'not', 'no ', 'unconfirmed', 'n/a')) for c in cat) and all(c['retrieved_on'] == '2026-10-13' for c in cat), 'every row has a documentation URL or an explicit statement that none was found; retrieval date recorded')
tp = rd('catalogue/TRANSLATION_PACK_DRAFTS.csv'); byid = {c['catalogue_id']: c for c in cat}
bad = [(t['catalogue_id'], t['vendor_entity_named_in_catalogue']) for t in tp if t['catalogue_id'] not in byid or t['vendor_entity_named_in_catalogue'].lower() not in byid[t['catalogue_id']]['data_entities_exposed'].lower()]
chk('C06', not bad, 'every vendor entity named in a translation-pack draft appears in the catalogue text for that system (nothing invented) ' + str(bad))
bad = [t['catalogue_id'] for t in tp if t['system'] != byid[t['catalogue_id']]['system'].split(' (')[0] and not byid[t['catalogue_id']]['system'].startswith(t['system'])]
chk('C07', not bad, 'system names in translation-pack drafts match the catalogue ' + str(bad))
chk('C08', all(t['status'] == 'draft - unverified' and t['evidence_grade'] in 'ABC' for t in tp), 'every translation-pack row is marked draft - unverified and carries an evidence grade')
chk('C09', all(t['evidence_grade'] == 'A' or t['evidence_grade'] in ('B', 'C') for t in tp) and all(not (t['evidence_grade'] == 'A' and byid[t['catalogue_id']]['confidence_overall'] == 'C') for t in tp), 'a draft row is not graded better than its system overall evidence allows')
print(f'\nchecks {n}  failed {len(fails)}')
if fails: print('FAILED:', fails); sys.exit(1)
print('ALL PROGRAMME CHECKS PASS')
