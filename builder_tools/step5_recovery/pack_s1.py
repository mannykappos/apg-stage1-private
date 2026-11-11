#!/usr/bin/env python3
"""Builder tool: build the stage 1 delivery ZIP (deterministic: sorted names, fixed timestamps) with a SHA256SUMS file inside.
Every run set's extraction directory (`x/`) is left out: each was checked file by file against its ZIP after the set
(`tree_after.txt`), so it holds nothing the ZIP does not.
Usage: python3 -I pack_s1.py JU1E_DIR OUT.zip      BUILDER-EXECUTED: NOT INDEPENDENT."""
import hashlib, os, sys, zipfile

J = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
TOP = 'APG-M11-S1_STAGE1_PACKAGE'
S1 = os.path.join(J, 'd14', 's1')
PARTS = [  # (source dir or file, path in the package)
    (os.path.join(S1, 'freeze', 'APG-M11-S1.zip'), 'freeze/APG-M11-S1.zip'),
    (os.path.join(S1, 'evidence'), 'evidence'),
    (os.path.join(S1, 'tools'), 'builder_tools'),
    (os.path.join(J, 'd14', 'p1m1'), 'p1m1'),
    (os.path.join(J, 'd14', 'tools_tests', 'test_d14_record_postgresql.py'), 'p1m1/tools_tests/test_d14_record_postgresql.py'),
    (os.path.join(J, 'd14', 'decisions'), 'decisions'),
    (os.path.join(J, 'rec'), 'records'),
    (os.path.join(S1, 'README_PACKAGE.md'), 'README.md'),
    (os.path.join(S1, 'GPT_REVIEW_PROMPT_STAGE1.md'), 'GPT_REVIEW_PROMPT_STAGE1.md'),
]


def walk(src, dst):
    if os.path.isfile(src):
        yield src, dst
        return
    for d, ds, fs in os.walk(src):
        rel = os.path.relpath(d, src)
        parts = [] if rel == '.' else rel.split(os.sep)
        # leave out extraction directories of run sets and caches
        if 'x' in parts or '__pycache__' in parts:
            ds[:] = []
            continue
        ds[:] = sorted(x for x in ds if x not in ('x', '__pycache__'))
        for f in sorted(fs):
            yield os.path.join(d, f), '/'.join([dst] + parts + [f])


files = sorted((dst, src) for s, t in PARTS for src, dst in walk(s, t))
assert len({d for d, _ in files}) == len(files)
sums = []
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    for dst, src in files:
        data = open(src, 'rb').read()
        sums.append('%s  %s' % (hashlib.sha256(data).hexdigest(), dst))
        zi = zipfile.ZipInfo(TOP + '/' + dst, (2026, 11, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, data)
    zi = zipfile.ZipInfo(TOP + '/SHA256SUMS', (2026, 11, 1, 0, 0, 0))
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    z.writestr(zi, '\n'.join(sums) + '\n')
print('files', len(files), 'zip', OUT, hashlib.sha256(open(OUT, 'rb').read()).hexdigest())
