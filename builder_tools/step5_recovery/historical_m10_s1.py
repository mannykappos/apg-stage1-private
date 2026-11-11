#!/usr/bin/env python3
"""Builder tool (outside the successor tree): authorisation §4.8, first bullet: the historical checks run against the immutable M10 archive.
The checks are the 100 rows of the adopted exclusion list (W1_EXCLUSION_LIST_v3.csv, W-1B): 97 rows with a command (their distinct
commands are run once each) and 3 built-in coverage checks (evaluated from the M10 wrapper's own definitions, the way the successor reads
them, without running the wrapper).  For one Python: verifies the archive's SHA-256, extracts it, runs each command from the package root
as the inventory did (PYTHON -I, the same environment), and compares the exit code and last line with those the list records.  Afterwards
the extraction is compared with the archive: any file a check changed, added or removed is listed.
Usage: python3 -I historical_m10_s1.py M10.zip EXCLUSIONS.csv PYTHON OUT
BUILDER-EXECUTED: NOT INDEPENDENT."""
import csv, hashlib, json, os, subprocess, sys, time, zipfile

M10_SHA256 = 'bd5c592a198581808237e5a5e563aa15c3be977d3f3e0d68511499d755435192'
EXCL_SHA256 = '266eea0dd870452921a19b52bff2c64eb9aa0b42a5f579ecffba33da9a28e479'
ENV = {'PATH': '/opt/node22/bin:/usr/bin:/bin', 'TMPDIR': '/tmp', 'PYTHONDONTWRITEBYTECODE': '1', 'HOME': '/tmp'}
COVERAGE = r'''
import sys, types
root, name = sys.argv[1], sys.argv[2]
path = root + '/tools/' + name + '.py'
lines = open(path, encoding='utf-8').read().split('\n')
mod = types.ModuleType(name + '_definitions'); mod.__file__ = path
exec(compile('\n'.join(lines[:lines.index('def main():')]) + '\n', path, 'exec'), mod.__dict__)
mod.ROOT = root
ok, detail = mod.coverage()
print(detail)
sys.exit(0 if ok else 1)
'''


def files(zp):
    with zipfile.ZipFile(zp) as z:
        return {n.split('/', 1)[1]: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}


def tree(root):
    out = {}
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x != '__pycache__']
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root)] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return out


def main(zp, excl, py, out):
    out = os.path.abspath(out)   # the checks run with the extraction as their working directory
    for p, want in ((zp, M10_SHA256), (excl, EXCL_SHA256)):
        if hashlib.sha256(open(p, 'rb').read()).hexdigest() != want:
            print('REFUSED: %s is not the expected file' % p)
            return 2
    os.makedirs(os.path.join(out, 'logs'))
    with zipfile.ZipFile(zp) as z:
        z.extractall(os.path.join(out, 'x'))
    root = os.path.join(out, 'x', 'APG_M10')
    want = files(zp)
    if tree(root) != want:
        print('EXTRACTION DIFFERS FROM THE ARCHIVE')
        return 2
    rows = list(csv.DictReader(open(excl, encoding='utf-8', newline='')))
    results, done = [], {}
    for i, r in enumerate(rows, 1):
        key = r['command'] if r['command'] != '(built in)' else 'coverage:' + r['wrapper']
        if key not in done:
            log = os.path.join(out, 'logs', 'H%03d.txt' % (len(done) + 1))
            cmd = ([py, '-I', '-c', COVERAGE, root, r['wrapper']] if r['command'] == '(built in)' else [py, '-I'] + r['command'].split())
            t0 = time.time()
            with open(log, 'wb') as fh:
                p = subprocess.run(cmd, cwd=root, env=ENV, stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
            data = open(log, 'rb').read()
            last = (data.decode('utf-8', 'replace').strip().splitlines() or [''])[-1][:300]
            done[key] = (p.returncode, last, os.path.relpath(log, out), hashlib.sha256(data).hexdigest(), round(time.time() - t0))
            print('%s exit=%d %ds | %s' % (key[:70], p.returncode, done[key][4], last[:100]), flush=True)
        ex, last, log, lsha, secs = done[key]
        rec_exit = r['exit_on_clean_m10']
        same_exit = (str(ex) == rec_exit) if rec_exit != '-' else (ex != 0)
        same_last = last == r['last_line_on_clean_m10'][:300]
        results.append([r['wrapper'], r['group_id'], r['command'], rec_exit, ex, same_exit, r['last_line_on_clean_m10'], last, same_last,
                        log, lsha, secs])
    with open(os.path.join(out, 'historical_checks.csv'), 'w', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(['wrapper', 'group_id', 'command', 'recorded_exit', 'exit', 'exit_as_recorded', 'recorded_last_line', 'last_line',
                    'last_line_as_recorded', 'log', 'log_sha256', 'seconds'])
        w.writerows(results)
    after = tree(root)
    diff = sorted(set(after) ^ set(want)) + sorted(k for k in set(after) & set(want) if after[k] != want[k])
    summary = {'python': py, 'rows': len(results), 'distinct_commands_run': len(done),
               'exit_as_recorded': sum(1 for x in results if x[5]), 'last_line_as_recorded': sum(1 for x in results if x[8]),
               'archive_files_changed_by_the_checks': diff}
    json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
    print(json.dumps({k: (v if k != 'archive_files_changed_by_the_checks' else len(v)) for k, v in summary.items()}))
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:5]))
