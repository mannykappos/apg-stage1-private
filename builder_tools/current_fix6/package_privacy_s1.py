#!/usr/bin/env python3
"""Builder tool (packaging, step 7; amendment 5 discrepancy 22): mask and search a package folder and its documents file.

mask:   python3 -I package_privacy_s1.py mask PKG_DIR
        In every text file, the workspace path becomes <WORKSPACE> and the session folder id <SESSION-ID>; MASKING.csv in PKG_DIR
        lists each changed file with its SHA-256 before and after. Binary files and ZIPs are not changed.
search: python3 -I package_privacy_s1.py search OUT.txt PATH...
        Searches every file (text and binary) and every member of every ZIP (one level down; a nested ZIP inside a ZIP is reported
        as not searched) for: the user's e-mail address, the account and organisation identifiers, the session id and the remote
        session id, the session folder id, the container id, session links, session-id shapes, the workspace path, and credential
        shapes. The identifier values are read from this process's environment and are never written out; only the kind of hit is.
        Writes OUT.txt (one line per hit: where, which kind) and exits 1 if there is any hit outside the accepted list.
BUILDER-EXECUTED: NOT INDEPENDENT."""
import base64, csv, hashlib, io, os, re, sys, zipfile

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../scratchpad
SID = WS.split('/')[-2] if WS.endswith('/scratchpad') else None
h = lambda b: hashlib.sha256(b).hexdigest()

def mask(pkg):
    rows = []
    for root, ds, fs in os.walk(pkg):
        for f in fs:
            p = os.path.join(root, f)
            if f == 'MASKING.csv':
                continue
            b = open(p, 'rb').read()
            if b'\0' in b or b[:2] == b'PK':
                continue
            try:
                t = b.decode('utf-8')
            except UnicodeDecodeError:
                continue
            n = t.replace(WS, '<WORKSPACE>')
            if SID:
                n = n.replace(SID, '<SESSION-ID>')
            if n != t:
                open(p, 'w', encoding='utf-8').write(n)
                rows.append([os.path.relpath(p, pkg), h(b), h(n.encode())])
    with open(os.path.join(pkg, 'MASKING.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['path', 'sha256_before_masking', 'sha256_after_masking'])
        w.writerows(sorted(rows))
    print('masked', len(rows))

def patterns():
    env = os.environ
    out = []
    for kind, var in (('e-mail address', 'CLAUDE_CODE_USER_EMAIL'), ('account id', 'CLAUDE_CODE_ACCOUNT_UUID'),
                      ('organisation id', 'CLAUDE_CODE_ORGANIZATION_UUID'), ('session id', 'CLAUDE_CODE_SESSION_ID'),
                      ('remote session id', 'CLAUDE_CODE_REMOTE_SESSION_ID'), ('container id', 'CLAUDE_CODE_CONTAINER_ID')):
        v = env.get(var, '')
        if len(v) >= 6:
            out.append((kind, v.encode()))
            if kind == 'e-mail address':
                out.append((kind + ' (base64)', base64.b64encode(v.encode())))
                out.append((kind + ' (local part)', v.split('@')[0].encode()))
    if SID:
        out.append(('session folder id', SID.encode()))
        out.append(('session folder id, first part', SID[:13].encode()))
    j = lambda *a: ''.join(a).encode()   # joined at run time, so that this file does not match itself
    out += [('workspace path', WS.encode()), ('home-claude temp path', j('/tmp/', 'claude-0/')),
            ('session link', j('claude.ai', '/code')), ('session-id shape', j('session', '_01')),
            ('Anthropic key shape', j('sk-', 'ant-')), ('GitHub token shape', j('gh', 'p_')), ('GitHub token shape', j('github', '_pat_')),
            ('AWS key shape', j('AK', 'IA')), ('private key', j('PRIVATE', ' KEY'))]
    return out

def search(outp, paths):
    pats, hits = patterns(), []
    def scan(label, b, depth):
        for kind, p in pats:
            if p in b:
                hits.append((label, kind))
        if b[:2] == b'PK':
            try:
                zf = zipfile.ZipFile(io.BytesIO(b))
            except zipfile.BadZipFile:
                return
            for i in zf.infolist():
                if i.is_dir():
                    continue
                d = zf.read(i)
                if d[:2] == b'PK' and depth >= 1:
                    hits.append((label + '::' + i.filename, 'NOT SEARCHED (a ZIP inside a ZIP)'))
                    continue
                scan(label + '::' + i.filename, d, depth + 1)
    for top in paths:
        if os.path.isfile(top):
            scan(os.path.basename(top), open(top, 'rb').read(), 0)
            continue
        for root, ds, fs in os.walk(top):
            for f in sorted(fs):
                p = os.path.join(root, f)
                scan(os.path.relpath(p, os.path.dirname(top)), open(p, 'rb').read(), 0)
    # Accepted: the immutable M10 baseline file inside the freeze holds the session folder id (which is also the session id) inside
    # two workspace paths (owner, 2026-11-11: "Mask loose, accept in ZIPs").
    accepted = lambda l, k: 'APG-M11-S1/logs/m81/baseline/00_hashes.txt' in l or k.startswith('NOT SEARCHED')
    lines = ['%s | %s | %s' % ('accepted' if accepted(l, k) else 'HIT', l, k) for l, k in sorted(set(hits))]
    bad = [x for x in lines if x.startswith('HIT')]
    open(outp, 'w').write('\n'.join(lines + ['patterns searched: %d kinds; hits outside the accepted list: %d' % (len(pats), len(bad))]) + '\n')
    print('\n'.join(lines[-20:]))
    print('hits outside the accepted list:', len(bad))
    sys.exit(1 if bad else 0)

if sys.argv[1] == 'mask':
    mask(sys.argv[2])
else:
    search(sys.argv[2], sys.argv[3:])
