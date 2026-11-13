#!/usr/bin/env python3
"""Builder tool (outside the tree), new in the 2026-11-11 recovery (the c9b324eb-era commands for these two records were not kept as a
tool): the two m2 records beside compare_pass2_s1.py's m2 steps, each on a fresh extraction of the freeze, one Python per call.
  list    NEW.zip PY OUT   amendment 5 AM5-1 A (i): the literal output of M10's tools/m2_mutants.py --list (PY -I, cwd = the root),
                           written to OUT/m2_logs/m10_script_list.txt with its command and exit; checks exit 0, 199 ids, RI10 at 51
  equiv1  NEW.zip PY OUT   AM5-3 option B: M10's own run_one on the ids of M10's EQUIV, one at a time (builder_tools s14_diag.py, run
                           from the root as PY -I), written to OUT/m2_logs/equiv_1worker.txt.  A survivor supports the allowance; any
                           other result (a kill by tests or contracts, a timeout, an error) is reported as a stop (exit 1)
Environment for each child: PATH LANG LC_ALL TZ TMPDIR only, as compare_pass2_s1.run.      BUILDER-EXECUTED: NOT INDEPENDENT."""
import hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
M10_M2 = 'fe1fd878fee975dff6dfdbdf27a7124665228a6efef624c396b40f7d68cd157b'


def extract(zp, dest):
    with zipfile.ZipFile(zp) as z:
        z.extractall(dest)
    return os.path.join(dest, 'APG-M11-S1')


def run(py, root, args, tmp, timeout):
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp}
    p = subprocess.run([py, '-I'] + args, cwd=root, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr, ' '.join([py, '-I'] + args)


def main(mode, zp, py, out):
    d = os.path.join(out, 'm2_logs')
    os.makedirs(d, exist_ok=True)
    zsha = hashlib.sha256(open(zp, 'rb').read()).hexdigest()
    tmp = tempfile.mkdtemp(prefix='s1_m2x_')
    try:
        root = extract(zp, os.path.join(tmp, 'x'))
        msha = hashlib.sha256(open(os.path.join(root, 'tools', 'm2_mutants.py'), 'rb').read()).hexdigest()
        t = tempfile.mkdtemp(prefix='s1_m2x_t_', dir=tmp)
        if mode == 'list':
            code, text, cmd = run(py, root, ['tools/m2_mutants.py', '--list'], t, 600)
            with open(os.path.join(d, 'm10_script_list.txt'), 'w') as fh:
                fh.write('# %s (fresh extraction of %s, cwd = root; tools/m2_mutants.py %s)\n# exit %d\n%s' % (cmd, zsha[:16] + '...', msha, code, text))
            ids = [l for l in text.splitlines() if l.strip()]
            pos = ids.index('RI10-query-crosses-tenants') + 1 if 'RI10-query-crosses-tenants' in ids else None
            ok = code == 0 and len(ids) == 199 and pos == 51 and msha == M10_M2
            print('m10 --list: exit %d, %d ids, RI10 at %s, m2_mutants.py %s: %s' % (code, len(ids), pos, 'as expected' if msha == M10_M2 else 'DIFFERENT', 'OK' if ok else 'NOT AS EXPECTED'))
            return 0 if ok else 1
        if mode == 'equiv1':
            code, text, cmd = run(py, root, [os.path.join(HERE, 's14_diag.py')], t, 3 * 3600)
            with open(os.path.join(d, 'equiv_1worker.txt'), 'w') as fh:
                fh.write('# %s (fresh extraction of %s, cwd = root; tools/m2_mutants.py %s)\n# exit %d\n%s' % (cmd, zsha[:16] + '...', msha, code, text))
            last = json.loads(text.strip().splitlines()[-1]) if code == 0 else {}
            res = [(r['id'], r['result'][1], r['result'][2], r['seconds']) for r in last.get('results', [])]
            for r in res:
                print('%s %s %s %.1f s' % r)
            ok = code == 0 and msha == M10_M2 and len(res) == 3 and all(r[1] == 'SURVIVED' for r in res)
            print('AM5-3 B: %s' % ('every EQUIV id SURVIVED (supports the allowance)' if ok else 'STOP: not every EQUIV id survived'))
            return 0 if ok else 1
        print(__doc__)
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:5]))
