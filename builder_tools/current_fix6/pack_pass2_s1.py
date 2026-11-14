#!/usr/bin/env python3
"""Builder tool (packaging, step 7): build the pass 2 recovery package ZIP deterministically (sorted names, fixed timestamps), with a
SHA256SUMS file inside listing every other file.
Usage: python3 -I -S pack_pass2_s1.py PKG_DIR OUT.zip           BUILDER-EXECUTED: NOT INDEPENDENT."""
import hashlib, os, sys, zipfile

SRC, OUT = os.path.abspath(sys.argv[1]), sys.argv[2]
TOP = os.path.basename(SRC)
files = []
for d, ds, fs in os.walk(SRC):
    ds[:] = sorted(x for x in ds if x not in ('x', '__pycache__'))
    for f in sorted(fs):
        if f == 'SHA256SUMS':
            continue
        files.append(os.path.relpath(os.path.join(d, f), SRC).replace(os.sep, '/'))
files.sort()
sums = []
def info(name):
    zi = zipfile.ZipInfo(TOP + '/' + name, (2026, 11, 15, 0, 0, 0))
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    return zi
with zipfile.ZipFile(OUT, 'w') as z:
    for f in files:
        data = open(os.path.join(SRC, f), 'rb').read()
        sums.append('%s  %s' % (hashlib.sha256(data).hexdigest(), f))
        z.writestr(info(f), data)
    text = '\n'.join(sums) + '\n'
    open(os.path.join(SRC, 'SHA256SUMS'), 'w').write(text)
    z.writestr(info('SHA256SUMS'), text)
print('files', len(files) + 1, 'zip', OUT, hashlib.sha256(open(OUT, 'rb').read()).hexdigest())
