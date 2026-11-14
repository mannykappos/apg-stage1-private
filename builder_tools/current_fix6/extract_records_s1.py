#!/usr/bin/env python3
"""Builder tool (packaging, step 7): copy the per-test evidence records out of the T-set logs into the package's evidence folders,
so a reviewer can read them without searching the logs.

- P_IDENTITY lines (process ids, start times, group ids, CLEANUP lines and the cleaning supervisor; I.3, B.5, row 121) go to
  OUT/identity/<python>_identity_records.txt.
- P_PROBE lines (AM-5(e), finding 13's path classes; row 75) go to OUT/audit/<python>_finding13_probes.txt.

Each output names its source log and that log's SHA-256 as the run index recorded it, and checks that the log on disk still has
that hash. Lines are copied unchanged and in log order; nothing is added or dropped. A hash mismatch stops the tool (exit 2).
Usage: python3 -I -S extract_records_s1.py RUN_SETS_DIR OUT_DIR          BUILDER-EXECUTED: NOT INDEPENDENT."""
import csv, hashlib, os, sys

RS, OUT = sys.argv[1], sys.argv[2]
KINDS = (('P_IDENTITY ', 'identity', 'identity_records'), ('P_PROBE ', 'audit', 'finding13_probes'))
for py in ('py313', 'py312'):
    d = os.path.join(RS, py + '_T')
    rows = list(csv.DictReader(open(os.path.join(d, 'run_index.csv'))))
    for prefix, sub, name in KINDS:
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
        out, total = [], 0
        for r in rows:
            p = os.path.join(d, r['log'])
            data = open(p, 'rb').read()
            if hashlib.sha256(data).hexdigest() != r['log_sha256']:
                print('STOP: hash of', p, 'differs from the run index'); sys.exit(2)
            lines = [l for l in data.decode('utf-8').splitlines() if l.startswith(prefix)]
            if lines:
                out.append('## source %s_T/%s  sha256 %s  (%s, %d lines)' % (py, r['log'], r['log_sha256'], r['order'], len(lines)))
                out.extend(lines)
                total += len(lines)
        head = ['BUILDER-EXECUTED: NOT INDEPENDENT. %s lines copied unchanged, in log order, from the %s T-set logs of freeze a7f599f9'
                % (prefix.strip(), py), 'by extract_records_s1.py. Total: %d lines.' % total, '']
        open(os.path.join(OUT, sub, '%s_%s.txt' % (py, name)), 'w').write('\n'.join(head + out) + '\n')
        print(py, prefix.strip(), total)
