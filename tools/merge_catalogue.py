#!/usr/bin/env python3
"""Merges the six research CSVs (research/) into one candidate systems catalogue. Python 3 standard library only.
Adds: catalogue_id, tracker_class, source_ids, system_key, confidence_overall (weakest grade named in the original string), confidence_detail (original text),
selection_status and pilot_confirmed. Nothing is inferred beyond the mapping tables below. Usage: merge_catalogue.py <research_dir> <out_csv>"""
import csv, re, sys
src, out = sys.argv[1], sys.argv[2]
FILES = ['project_management', 'accounting_erp', 'estimating', 'programme', 'labour_plant_bank', 'market_data']
CLASS_MAP = {  # research class -> (tracker class id, source ids)
    'project_management': ('Q1', 'SRC-03; SRC-04; SRC-07; SRC-08'), 'accounting_erp': ('Q2', 'SRC-01; SRC-02; SRC-09'), 'estimating': ('Q3', 'SRC-02; SRC-05'),
    'programme': ('Q5', 'SRC-04'), 'labour': ('S1', 'SRC-12'), 'plant_hire': ('S2', 'SRC-13'), 'bank_data': ('S3', 'SRC-14'), 'market_data': ('M', 'SRC-10')}
GRADE_RANK = {'A': 1, 'B': 2, 'C': 3}
def weakest(s):
    g = re.findall(r'(?:^|[;\s(])([ABC])(?=\s*[\(;]|\s*$|\s)', s.strip())
    g = [x for x in g if x in GRADE_RANK]
    return max(g, key=lambda x: GRADE_RANK[x]) if g else ''
rows = []
for f in FILES:
    for r in csv.DictReader(open(f'{src}/{f}.csv', encoding='utf-8-sig', newline='')):
        rows.append(r)
header = ['catalogue_id', 'tracker_class', 'source_ids', 'system_key'] + [k for k in rows[0].keys() if k not in ('confidence',)] + ['confidence_overall', 'confidence_detail', 'selection_status', 'pilot_confirmed']
w = csv.writer(open(out, 'w', newline='', encoding='utf-8'), lineterminator='\n'); w.writerow(header)
for i, r in enumerate(rows, 1):
    cls, sids = CLASS_MAP[r['class']]
    key = re.sub(r'[^a-z0-9]+', '-', r['system'].lower().split('(')[0]).strip('-')
    w.writerow([f'CAT-{i:03d}', cls, sids, key] + [r[k] for k in rows[0].keys() if k != 'confidence'] + [weakest(r['confidence']), r['confidence'], 'candidate only - not selected, not confirmed with any builder', 'no'])
print(len(rows), 'rows written')
