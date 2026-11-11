#!/usr/bin/env python3
"""Builder tool (outside the successor tree): the stage 1 evidence run set (authorisation §4.8) on a fresh extraction of the frozen ZIP.
For one Python: extracts the ZIP into OUT/tree, checks every extracted file against the ZIP, runs each command of the set in order from the
package root with a clean environment, keeps each command's combined output as a log, and writes OUT/run_index.csv with one row per
command: order, python, command, start (UTC), seconds, exit code, log file, log SHA-256 and last_line, which is a prefix of at most
300 characters of the log's last line (amendment 5, discrepancy 21: documentation only).  After the set it checks the
extracted tree again: a file the run changed, added or removed is listed in OUT/tree_after.txt.
Usage: python3 -I run_index_s1.py ZIP PYTHON OUT [--only PREFIX]
BUILDER-EXECUTED: NOT INDEPENDENT."""
import csv, datetime, hashlib, os, subprocess, sys, time, zipfile

TESTS_TOOLS = ['test_apg_root', 'test_consumer_exit_codes', 'test_exec_env', 'test_harness_isolation', 'test_mut_runner_output',
               'test_mutant_targets', 'test_mutation_error_shape', 'test_mutation_timeout', 'test_no_timeout_kill', 'test_runner_zero_work']
WRAPPERS = ['run_m4_all', 'run_m3_all', 'run_m6_all', 'run_m7_all', 'run_m71_all', 'run_m72_all', 'run_m73_all', 'run_m91_all',
            'run_m92_all', 'run_m93_all', 'run_m94_all', 'run_f67_all', 'run_f671_all', 'run_f672_all', 'run_f673_all', 'run_f674_all',
            'run_mie1_all', 'run_mie1_1_all', 'run_m8_all']
GUARDED = {'run_m3_all', 'run_m4_all', 'run_m6_all', 'run_m91_all', 'run_m92_all', 'run_m93_all', 'run_m94_all'}   # run all with no option


def commands():
    out = [('T%02d' % i, ['tests_tools/%s.py' % t]) for i, t in enumerate(TESTS_TOOLS, 1)]
    out += [('W%02d' % i, ['tools/%s_s1.py' % w] + ([] if w in GUARDED else ['--all'])) for i, w in enumerate(WRAPPERS, 1)]
    out += [('M01', ['tools/m8_mutants_s1.py', '--jobs', '2'])]
    return out


def zip_files(zp):
    with zipfile.ZipFile(zp) as z:
        return {n.split('/', 1)[1]: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}


def tree_files(root):
    out = {}
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x != '__pycache__']
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root).replace(os.sep, '/')] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return out


def main(zp, py, out, only=None):
    os.makedirs(os.path.join(out, 'logs'))
    with zipfile.ZipFile(zp) as z:
        z.extractall(os.path.join(out, 'x'))
    root = os.path.join(out, 'x', 'APG-M11-S1')
    want = zip_files(zp)
    if tree_files(root) != want:
        print('EXTRACTION DIFFERS FROM THE ZIP')
        return 2
    zsha = hashlib.sha256(open(zp, 'rb').read()).hexdigest()
    env = {'PATH': '/opt/node22/bin:/usr/bin:/bin', 'TMPDIR': '/tmp', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC'}
    rows = []
    for order, args in commands():
        if only and not order.startswith(tuple(only.split(','))):
            continue
        free = os.statvfs(out).f_bavail * os.statvfs(out).f_frsize
        if free < 10 * 1024 ** 3:      # the authorisation's disk floor: stop below 10 GB
            print('STOPPED before %s: free disk %d bytes is below the 10 GB floor' % (order, free), flush=True)
            return 3
        log = os.path.join(out, 'logs', '%s_%s.txt' % (order, os.path.basename(args[0])[:-3]))
        start = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        t0 = time.time()
        with open(log, 'wb') as fh:
            p = subprocess.run([py, '-I', '-S'] + args, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=fh, stderr=subprocess.STDOUT)  # AM-4
        secs = round(time.time() - t0)
        data = open(log, 'rb').read()
        last = (data.decode('utf-8', 'replace').strip().splitlines() or [''])[-1][:300]
        rows.append([order, py, ' '.join([py, '-I', '-S'] + args), start, secs, p.returncode, os.path.relpath(log, out),
                     hashlib.sha256(data).hexdigest(), last])
        print('%s %s exit=%d %ds | %s' % (order, args[0], p.returncode, secs, last[:150]), flush=True)
        with open(os.path.join(out, 'run_index.csv'), 'w', newline='') as fh:
            w = csv.writer(fh, lineterminator='\n')
            w.writerow(['order', 'python', 'command', 'start_utc', 'seconds', 'exit', 'log', 'log_sha256', 'last_line'])
            w.writerows(rows)
    after = tree_files(root)
    diff = sorted(set(after) ^ set(want)) + sorted(k for k in set(after) & set(want) if after[k] != want[k])
    with open(os.path.join(out, 'tree_after.txt'), 'w') as fh:
        fh.write('zip_sha256 %s\nfiles changed, added or removed by the run set: %d\n' % (zsha, len(diff)))
        fh.writelines(d + '\n' for d in diff)
    print('DONE zip %s  tree changes %d' % (zsha, len(diff)))
    return 0


if __name__ == '__main__':
    a = sys.argv[1:]
    sys.exit(main(a[0], a[1], a[2], a[a.index('--only') + 1] if '--only' in a else None))
