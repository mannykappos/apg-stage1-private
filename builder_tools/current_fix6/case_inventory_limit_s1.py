#!/usr/bin/env python3
"""Builder tool (outside the tree), rewritten in the 2026-11-11 recovery from the format of the c9b324eb record
static/case_inventory_limit.txt (the tool that made it was lost): the 2C demonstration (A.4, I.3; amendment 5 row 37).
On a fresh extraction of the freeze, run_contracts_s1 is run three times (one suite and one case; two suites and one case; two suites).
For each run: the printed case_inventory_sha256 is compared with the hash of the pinned inventories (tools/expected_counts.json,
case_inventories.run_contracts_s1) of every non-empty set of run_contracts' pinned suites, computed as evkit's checker does
(sha256_lines over '<suite>/<case>').  The demonstration holds when, for each run, exactly the true selection's set is accepted.
Each run: PY -I -S from the root, environment PATH LANG LC_ALL TZ TMPDIR only.
Usage: python3 -I case_inventory_limit_s1.py NEW.zip PY OUT.txt        BUILDER-EXECUTED: NOT INDEPENDENT."""
import itertools, json, os, re, shutil, subprocess, sys, tempfile, zipfile

RUNS = [['--suite', 'audit_log', '--only', 'AL-01'], ['--suite', 'record_store', '--suite', 'audit_log', '--only', 'AL-01'],
        ['--suite', 'record_store', '--suite', 'audit_log']]


def main(zp, py, outp):
    tmp = tempfile.mkdtemp(prefix='s1_cil_')
    lines, ok = [], True
    try:
        with zipfile.ZipFile(zp) as z:
            z.extractall(tmp)
        root = os.path.join(tmp, 'APG-M11-S1')
        sys.path.insert(0, root)
        import tools.evkit as E
        pins = json.load(open(os.path.join(root, 'tools', 'expected_counts.json')))['case_inventories']['run_contracts_s1']
        suites = sorted(pins)
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp}

        def h(ss):
            return E.sha256_lines(['%s/%s' % (s, c) for s in ss for c in pins[s]['ids']])
        for args in RUNS:
            p = subprocess.run([py, '-I', '-S', 'tools/run_contracts_s1.py'] + args, cwd=root, env=env, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=1800)
            out = p.stdout + p.stderr
            m = re.search(r'(?m)^RESULT v=\d+ .*$', out)
            f = dict(kv.split('=', 1) for kv in m.group(0).split()[1:] if '=' in kv) if m else {}
            printed = []
            for l in out.splitlines():
                mm = re.match(r'^CASE (\S+?)/\S+ ', l)
                if mm and mm.group(1) not in printed:
                    printed.append(mm.group(1))
            sel = [args[i + 1] for i, a in enumerate(args) if a == '--suite']
            got = f.get('case_inventory_sha256')
            lines.append('run_contracts_s1 %s: exit %d, suites_selected=%s, CASE suites printed %s' % (' '.join(args), p.returncode,
                         f.get('suites_selected'), sorted(printed)))
            same = got == h(sel)
            lines.append('  printed hash = the selected suites %s: %s' % (sel, same))
            accepted = []
            for k in range(1, len(suites) + 1):
                for c in itertools.combinations(suites, k):
                    a = got == h(list(c))
                    if a:
                        accepted.append(sorted(c))
                    lines.append('    hash of the set %-48s %s' % (list(c), 'accepted (the true selection)' if a and sorted(c) == sorted(sel)
                                                                  else 'ACCEPTED (not the selection)' if a else 'rejected'))
            ok = ok and p.returncode == 0 and same and accepted == [sorted(sel)]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    lines.append('RESULT case_inventory_limit %s (python %s)' % ('HOLDS' if ok else 'DOES NOT HOLD', py))
    open(outp, 'w').write('\n'.join(lines) + '\n')
    print(lines[-1])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
