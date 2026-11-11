#!/usr/bin/env python3
"""Builder tool: write the stage 1 documents file (authorisation §4.9) from the evidence on disk.
Usage: python3 -I make_s1_documents.py S1_DIR OUT.md      BUILDER-EXECUTED: NOT INDEPENDENT."""
import csv, glob, hashlib, io, json, os, sys, zipfile

S1 = sys.argv[1]
OUT = sys.argv[2]
D14 = os.path.dirname(S1)
ZIP = os.path.join(S1, 'freeze', 'APG-M11-S1.zip')
EV = os.path.join(S1, 'evidence')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def read(p):
    return open(p, encoding='utf-8').read()


z = zipfile.ZipFile(ZIP)
manifest = list(csv.DictReader(io.TextIOWrapper(z.open('APG-M11-S1/programme/APG-M11-S1_MANIFEST.csv'), encoding='utf-8')))
pins = json.load(z.open('APG-M11-S1/tools/expected_counts.json'))
zsha = sha(ZIP)
L = []
w = L.append

w(open(os.path.join(S1, 'tools', 'DOCUMENTS_HEAD.md'), encoding='utf-8').read().replace('{ZIP_SHA256}', zsha)
  .replace('{MANIFEST_SHA256}', hashlib.sha256(z.read('APG-M11-S1/programme/APG-M11-S1_MANIFEST.csv')).hexdigest())
  .replace('{PINS_VERSION}', str(pins['version'])))

# ---- run index
w('\n## 3. The run index (authorisation §4.8: every command, its exit code and its log hash, for each Python)\n')
w('All commands ran from a fresh extraction of the frozen ZIP (`%s`), checked file by file against the ZIP before the set and again after it. '
  'Environment: only PATH, TMPDIR, LANG, LC_ALL and TZ are set (`tools/run_index_s1.py`); each command is `PYTHON -I -S`, run from the extraction root. Logs are in `evidence/<set>/logs/` in the package.\n' % zsha)
for py in ('python3.13', 'python3.12'):
    tag = py.replace('python', 'py').replace('.', '')
    w('\n### %s\n' % py)
    w('| Set | Order | Command | Start (UTC) | Seconds | Exit | Log SHA-256 | Last line (start) |')
    w('|---|---|---|---|---|---|---|---|')
    for part in ('T', 'W', 'M'):
        d = os.path.join(EV, '%s_%s' % (tag, part))
        for r in csv.DictReader(open(os.path.join(d, 'run_index.csv'))):
            cmd = r['command'].replace('/usr/bin/', '').split(' ', 3)
            w('| %s_%s | %s | `%s` | %s | %s | %s | `%s` | %s |' % (tag, part, r['order'], ' '.join(cmd), r['start_utc'], r['seconds'], r['exit'],
                                                                   r['log_sha256'], r['last_line'][:60].replace('|', '/')))
        ta = read(os.path.join(d, 'tree_after.txt')).splitlines()
        w('| %s_%s | after | extraction compared with the ZIP | | | | | %s |' % (tag, part, ta[1]))
    w('')
for py in ('python3.13', 'python3.12'):
    tag = py.replace('python', 'py').replace('.', '')
    w('\n**Wrapper outputs, %s** (each log read with the frozen tree\'s own `evkit.check_output` and `wrapper_verdict`):\n' % py)
    w('```\n' + read(os.path.join(EV, '%s_W' % tag, 'wrapper_check.txt')).strip() + '\n```')
w('\nThe 103 CHECK groups are 102 that start a child (section 5) and 1 the wrapper evaluates itself: `run_f674_all_s1` G10, the built-in coverage check of the whole `tests/` directory (class W, `source=wrapper`; W-1B.3).\n')
for py in ('python3.13', 'python3.12'):
    tag = py.replace('python', 'py').replace('.', '')
    w('\n**M8 mutation run, %s:**\n' % py)
    w('```\n' + read(os.path.join(EV, '%s_M' % tag, 'm8_check.txt')).strip() + '\n```')

# ---- historical
w('\n## 4. Historical checks against the immutable M10 archive (authorisation §4.8, first point)\n')
w(read(os.path.join(S1, 'tools', 'DOCUMENTS_HISTORICAL.md')))
for py in ('python3.13', 'python3.12'):
    d = os.path.join(EV, 'historical_' + py.replace('python', 'py').replace('.', ''))
    s = json.load(open(os.path.join(d, 'summary.json')))
    w('\n**%s:** %d rows, %d distinct commands run; exit as recorded %d of %d; last line as recorded %d of %d; archive files changed by the '
      'checks in the extraction: %d.\n' % (py, s['rows'], s['distinct_commands_run'], s['exit_as_recorded'], s['rows'], s['last_line_as_recorded'],
                                           s['rows'], len(s['archive_files_changed_by_the_checks'])))
    rows = list(csv.DictReader(open(os.path.join(d, 'historical_checks.csv'))))
    diff = [r for r in rows if r['exit_as_recorded'] != 'True' or r['last_line_as_recorded'] != 'True']
    if diff:
        w('Rows that differ from the record:\n')
        w('| Wrapper | Group | Command | Recorded exit | Exit | Recorded last line | Last line |')
        w('|---|---|---|---|---|---|---|')
        for r in diff:
            w('| %s | %s | `%s` | %s | %s | %s | %s |' % (r['wrapper'], r['group_id'], r['command'], r['recorded_exit'], r['exit'],
                                                       r['recorded_last_line'][:70].replace('|', '/'), r['last_line'][:70].replace('|', '/')))
    if s['archive_files_changed_by_the_checks']:
        w('\nFiles the checks wrote in the extraction (the archive itself is never written): ' +
          ', '.join('`%s`' % f for f in s['archive_files_changed_by_the_checks'][:40]))

# ---- static
w('\n## 5. The frozen files and the routes (authorisation §4.7)\n')
w('**Frozen-file comparison** (`tools/frozen_compare_s1.py`, from the two ZIPs alone; per-file table `evidence/static_final/frozen_compare.csv`):\n')
w('```\n' + read(os.path.join(EV, 'static_final', 'frozen_compare.txt')).strip() + '\n```')
w('\n**Route proof, children** (every child a wrapper starts, from the pinned plans; `evidence/static_final/route_children.txt`):\n')
w('```\n' + read(os.path.join(EV, 'static_final', 'route_children.txt')).strip() + '\n```')
w(read(os.path.join(S1, 'tools', 'DOCUMENTS_ROUTE.md')))
w('\nRoute scan summary (`evidence/static_final/route_scan.txt`, first line): `%s`\n'
  % read(os.path.join(EV, 'static_final', 'route_scan.txt')).splitlines()[0])

# ---- P1-M1
w('\n## 6. P1-M1 (outside the 89 lines: the D14 record tools)\n')
w(read(os.path.join(S1, 'tools', 'DOCUMENTS_P1M1.md')))

# ---- manifest
w('\n## 7. The stage 1 file manifest (authorisation §4.2, as amended: 89 D1 lines, 1 supplementary line, the change record, and every changed file)\n')
w('The in-tree file is `programme/APG-M11-S1_MANIFEST.csv` (SHA-256 `%s`), written without `--allow-incomplete` and checked again from '
  'the frozen ZIP with no problem. Every line states that no out-of-scope change was made: the frozen-file comparison above finds no changed '
  'or new file the manifest does not declare.\n' % hashlib.sha256(z.read('APG-M11-S1/programme/APG-M11-S1_MANIFEST.csv')).hexdigest())
w('| Section | Path | Status | M10 SHA-256 | Stage 1 SHA-256 | Successor of | Findings and blocks |')
w('|---|---|---|---|---|---|---|')
for r in manifest:
    w('| %s | `%s` | %s | %s | %s | %s | %s |' % (r['section'], r['path'], r['status'], (r['m10_sha256'][:16] + '…') if len(r['m10_sha256']) > 20 else r['m10_sha256'],
                                              (r['s1_sha256'][:16] + '…') if len(r['s1_sha256']) > 20 else r['s1_sha256'], r['successor'], r['detail'].replace('|', '/')))
w('\n(The full hashes are in the CSV itself, inside the ZIP.)\n')
w(read(os.path.join(S1, 'tools', 'DOCUMENTS_SHARED.md')))

w(read(os.path.join(S1, 'tools', 'DOCUMENTS_TAIL.md')))
open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('wrote', OUT, sha(OUT))
