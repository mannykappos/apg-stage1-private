#!/usr/bin/env python3
"""Builder tool (outside the successor tree): freeze an APG-M11-S1 git tree as one deterministic ZIP.
Every file git tracks at HEAD, under the folder APG-M11-S1/, sorted, with a fixed timestamp (1980-01-01) and fixed permissions, so the
same commit always gives the same bytes.  Refuses a tree with uncommitted changes.  Prints the commit, the file count and the ZIP SHA-256.
Usage: python3 -I freeze_s1.py TREE OUT.zip
BUILDER-EXECUTED: NOT INDEPENDENT."""
import hashlib, subprocess, sys, zipfile


def main(tree, out):
    git = lambda *a: subprocess.run(['git', '-C', tree] + list(a), capture_output=True, text=True, check=True).stdout
    if git('status', '--porcelain', '--untracked-files=all').strip():
        print('REFUSED: the tree has uncommitted or untracked changes')
        return 2
    head = git('rev-parse', 'HEAD').strip()
    files = sorted(git('ls-files', '-z').split('\0')[:-1])
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in files:
            data = subprocess.run(['git', '-C', tree, 'show', 'HEAD:' + f], capture_output=True, check=True).stdout
            info = zipfile.ZipInfo('APG-M11-S1/' + f, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 3
            z.writestr(info, data)
    h = hashlib.sha256(open(out, 'rb').read()).hexdigest()
    print('commit %s  files %d  zip_sha256 %s' % (head, len(files), h))
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:3]))
