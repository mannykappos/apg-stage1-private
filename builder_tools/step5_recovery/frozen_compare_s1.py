#!/usr/bin/env python3
"""Builder tool (outside the successor tree): authorisation §4.7 frozen-file comparison, from the two ZIPs alone.
Compares every file of the frozen stage 1 ZIP with the immutable M10 archive: identical, changed (must be exactly the manifest's
'changed' section), new (likewise) or missing from stage 1 (must be none).  For every successor tool tools/X_s1.py it checks that
M10's tools/X.py is present and byte-identical (DP-1.2).  Usage: python3 -I frozen_compare_s1.py M10.zip S1.zip OUT.csv
BUILDER-EXECUTED: NOT INDEPENDENT."""
import csv, hashlib, io, sys, zipfile


def files(zp):
    with zipfile.ZipFile(zp) as z:
        return {n.split('/', 1)[1]: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}


def main(m10z, s1z, out):
    m, s = files(m10z), files(s1z)
    with zipfile.ZipFile(s1z) as z:
        man = list(csv.DictReader(io.TextIOWrapper(z.open('APG-M11-S1/programme/APG-M11-S1_MANIFEST.csv'), encoding='utf-8')))
    declared = {r['path'] for r in man if r['section'] == 'changed'}
    rows, problems = [], []
    for p in sorted(set(m) | set(s)):
        st = ('identical' if m.get(p) == s.get(p) else 'missing_in_s1' if p not in s else 'new' if p not in m else 'changed')
        rows.append([p, st, m.get(p, '-'), s.get(p, '-'), 'yes' if p in declared else 'no'])
        if st in ('changed', 'new') and p not in declared and p != 'programme/APG-M11-S1_MANIFEST.csv':
            problems.append('undeclared %s %s' % (st, p))
        if st == 'missing_in_s1':
            problems.append('missing %s' % p)
        if st == 'identical' and p in declared:
            problems.append('declared but identical %s' % p)
    succ = sorted(p for p in s if p.startswith('tools/') and p.endswith('_s1.py'))
    frozen = []
    for p in succ:
        orig = p[:-6] + '.py'
        ok = orig in m and m.get(orig) == s.get(orig)
        frozen.append((p, orig, ok, orig in m))
        if orig in m and not ok:
            problems.append('M10 original changed %s' % orig)
    with open(out, 'w', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(['path', 'status', 'm10_sha256', 's1_sha256', 'declared_changed_in_manifest'])
        w.writerows(rows)
    c = {}
    for r in rows:
        c[r[1]] = c.get(r[1], 0) + 1
    print('files: %s' % ' '.join('%s=%d' % kv for kv in sorted(c.items())))
    print('successor tools %d; M10 original present %d, all byte-identical: %s; no M10 original (new tool): %s'
          % (len(frozen), sum(1 for f in frozen if f[3]), all(f[2] for f in frozen if f[3]), [f[0] for f in frozen if not f[3]]))
    print('problems %d' % len(problems))
    for x in problems:
        print('  ' + x)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
