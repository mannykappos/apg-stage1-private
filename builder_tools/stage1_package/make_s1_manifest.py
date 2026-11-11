#!/usr/bin/env python3
"""Builder tool (outside the successor tree): write programme/APG-M11-S1_MANIFEST.csv into an APG-M11-S1 tree.
The stage 1 manifest of the authorisation §4.2 as amended (amendment 1: 89 D1 lines; amendment 2: one supplementary line, the in-tree
machine-readable form at exactly programme/APG-M11-S1_MANIFEST.csv).  Sections, in this order: identity, d1, supplementary, records,
changed.  'changed' is every file of the tree whose hash differs from M10 (or that M10 lacks), except the manifest itself.
Usage: python3 -I make_s1_manifest.py TREE M10_FILES_SHA256 D1_CSV [--check]
  --check: report what the manifest would say and every problem (unaccounted change, missing successor), write nothing.
  --allow-incomplete: write it even with problems (development only; never for the evidence package).
BUILDER-EXECUTED: NOT INDEPENDENT."""
import csv, hashlib, io, os, sys

MANIFEST = 'programme/APG-M11-S1_MANIFEST.csv'
HEADER = ['section', 'path', 'status', 'm10_sha256', 's1_sha256', 'successor', 'detail']
M10_ARCHIVE_SHA256 = 'bd5c592a198581808237e5a5e563aa15c3be977d3f3e0d68511499d755435192'
FINDINGS = set('P1-F5 P1-F6 P1-F7 P1-M1 P2-B8 P2-S3 P3-B03 P3-B04 P3-S01 P4-B13 P4-S14 P4-B15 P4-B17 P5-B06 P5-S07 P5-S08 P7-B2 P7-B3 '
               'E1-C8 E1-RI10 AX-4 T-0'.split())
AMENDMENT1 = {'tools/%s.py' % n for n in ('run_f67_all run_f671_all run_f672_all run_f673_all run_f674_all run_mie1_all run_mie1_1_all run_faults '
                                         'run_m5_faults run_m6_faults run_guard_contract run_history_contract run_m6_contracts run_m91_contracts').split()}
EXCLUDED = {'apg_auif/dependency.py'}   # DP-1.3 (a)
SUPPLEMENTARY = 'tests_m8/test_m8_boundary.py'   # amendment 2
RECORDS = ['programme/CHANGE_RECORD_APG-M11-S1.md']
SKIP_DIRS = {'.git', '__pycache__'}


def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def tree_files(root):
    out = {}
    for d, ds, fs in os.walk(root):
        ds[:] = sorted(x for x in ds if x not in SKIP_DIRS)
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(d, f), root).replace(os.sep, '/')
            out[rel] = sha(os.path.join(d, f))
    return out


def d1_rows(path):
    rows = []
    for r in csv.DictReader(open(path, encoding='utf-8', newline='')):
        if r['file'] in EXCLUDED:
            continue
        if FINDINGS & set(r['findings'].split()) or r['file'] in AMENDMENT1:
            rows.append(r)
    return rows


def main(argv):
    root, m10_list, d1 = argv[:3]
    check = '--check' in argv
    m10 = {}
    for line in open(m10_list, encoding='utf-8'):
        h, p = line.rstrip('\n').split('  ', 1)
        m10[p[2:] if p.startswith('./') else p] = h
    files = tree_files(root)
    files.pop(MANIFEST, None)
    rows = d1_rows(d1)
    problems = []
    if len(rows) != 89:
        problems.append('d1 rows %d, expected 89' % len(rows))
    out = [HEADER, ['identity', '-', '-', M10_ARCHIVE_SHA256, '-', '-', 'stage=APG-M11-S1;base=APG-M10']]
    accounted = {}
    for r in rows:
        p = r['file']
        succ = r['option_b_successor_file'].split(' ')[0] if r['option_b_successor_file'] else ''
        succ = succ if succ and succ in files and succ != p else '-'
        if p not in files:
            problems.append('d1 path missing from the tree: %s' % p)
            continue
        if p in m10:
            status = 'unchanged' if files[p] == m10[p] else 'modified'
            mh = m10[p]
        else:
            status, mh = 'new', '-'
        if status == 'unchanged' and succ == '-':
            problems.append('d1 row not yet done (unchanged, no successor): %s' % p)
        out.append(['d1', p, status, mh, files[p], succ, 'findings=' + ' '.join(r['findings'].split())])
        if status != 'unchanged':
            accounted[p] = 'd1'
        if succ != '-':
            accounted[succ] = 'd1-successor'
    p = SUPPLEMENTARY
    out.append(['supplementary', p, 'modified' if files.get(p) != m10.get(p) else 'unchanged', m10.get(p, '-'), files.get(p, '-'), '-', 'amendment 2'])
    accounted[p] = 'supplementary'
    for p in RECORDS:
        if p in files:
            out.append(['records', p, 'new', '-', files[p], '-', 'stage 1 record'])
            accounted[p] = 'records'
        else:
            problems.append('record missing: %s' % p)
    changed = [(p, h) for p, h in sorted(files.items()) if m10.get(p) != h]
    for p, h in changed:
        out.append(['changed', p, 'modified' if p in m10 else 'new', m10.get(p, '-'), h, '-', '-'])
        if p not in accounted:
            problems.append('changed but not accounted for by any d1, supplementary or records line: %s' % p)
    gone = sorted(set(m10) - set(files))
    for p in gone:
        problems.append('an M10 file is missing from the tree: %s' % p)
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\n').writerows(out)
    if check:
        print('d1 %d  changed %d  problems %d' % (len(rows), len(changed), len(problems)))
        for x in problems:
            print('PROBLEM', x)
        return 1 if problems else 0
    if problems:
        for x in problems:
            print('PROBLEM', x)
        if '--allow-incomplete' not in argv:
            return 1
        print('WRITING AN INCOMPLETE DEVELOPMENT MANIFEST (--allow-incomplete): not stage 1 evidence')
    with open(os.path.join(root, MANIFEST), 'w', encoding='utf-8', newline='') as fh:
        fh.write(buf.getvalue())
    print('wrote %s  d1 %d  changed %d  sha256 %s' % (MANIFEST, len(rows), len(changed), sha(os.path.join(root, MANIFEST))))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
