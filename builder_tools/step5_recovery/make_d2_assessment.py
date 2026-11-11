#!/usr/bin/env python3
"""Builder tool (outside the successor tree): write programme/D2_HISTORICAL_MUTATION_ASSESSMENT.csv into an APG-M11-S1 tree.
The read-only historical-log assessment of D-2 (T_tooling.md T-0, "(R5) D-2: crash and timeout classifications, and the historical-log
assessment"; T_D6.csv row "D-2 (R5)"; decision DP-2.2 (b): a successor rerun's result supersedes the historical one for successor claims
only, and no M10 log or count is edited).  It reads M10's recorded mutation logs, runs nothing, and records per log: the mutants and kills
it records, the kills attributed to a timeout, to a crash, and to any token that is not a file of the tool's test list, the crash-kill
candidates (m8), and what the log cannot show.
Usage: python3 -I make_d2_assessment.py M10_TREE OUT_CSV          BUILDER-EXECUTED: NOT INDEPENDENT."""
import ast, csv, hashlib, importlib.util, os, re, sys

HEADER = ['family', 'log', 'log_sha256', 'tool_basis', 'mutants_recorded', 'kills', 'kills_by_timeout', 'kills_by_crash',
          'kills_by_token_not_in_test_list', 'crash_kill_candidates', 'source', 'cannot_show']
SHORT = lambda f: f.replace('test_det_', '').replace('test_fin_', '').replace('.py', '')   # tools/mut_runner.py's attribution name


def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load(root, name):
    s = importlib.util.spec_from_file_location('d2_' + name, os.path.join(root, 'tools', name + '.py'))
    m = importlib.util.module_from_spec(s)
    saved = sys.argv
    sys.argv = [name]
    try:
        s.loader.exec_module(m)
    finally:
        sys.argv = saved
    return m


def test_lists(root):
    sys.path.insert(0, root)
    out = {}
    for t in ('m5', 'm6', 'm7', 'm91'):
        out[t] = {SHORT(x) for x in load(root, t + '_mutants').ALL_TESTS}
    out['m73_store'] = {SHORT(x) for x in load(root, 'm73_store_mutants').TESTS}
    out['f67'] = {SHORT(x) for x in load(root, 'f67_mutants').TESTS}
    for t in ('f671', 'f672', 'f673', 'f674'):
        out[t] = {SHORT(x) for x in load(root, t + '_mutants').F.TESTS}
    out['mie'] = {SHORT(x) for x in load(root, 'mie_mutants').ALL_TESTS}
    out['mie11'] = {SHORT(x) for x in load(root, 'mie11_mutants').M.ALL_TESTS}
    m8 = load(root, 'm8_mutants')
    out['m8'] = set(m8.TIER1) | set(m8.TIER2)
    return out


KILL = re.compile(r'^KILLED\s+(\S+)\s+\(by (.+)\)\s*$')
SUMMARY = re.compile(r'^mutants (\d+)\s+killed (\d+) \(first failing test file: (\{.*?\})\)')
M8KILL = re.compile(r'^(\S+)\s+KILLED\s+\d+s (tier \d+: .*)$')
M8SUM = re.compile(r'^mutants (\d+): killed (\d+), documented equivalent (\d+), survived (\d+), timeout (\d+)')


def assess(path, tests):
    """Return (mutants, kills, timeout, crash, not_in_list, crash_candidates, source) from one log."""
    lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
    per = [KILL.match(l) for l in lines if KILL.match(l)]
    sums = [SUMMARY.match(l) for l in lines if SUMMARY.match(l)]
    if any(M8KILL.match(l) for l in lines) or any(M8SUM.match(l) for l in lines):
        kills = [M8KILL.match(l) for l in lines if M8KILL.match(l)]
        sm = [M8SUM.match(l) for l in lines if M8SUM.match(l)]
        n = sum(int(x.group(1)) for x in sm) if sm else ''
        cand = [k for k in kills if not re.match(r'^tier \d+: (FAIL|ERROR): ', k.group(2))]
        bad = 0
        for k in kills:
            m = re.search(r'\(tests_m8\.(\w+)\.', k.group(2))
            if m and m.group(1) not in tests:
                bad += 1
        timeouts = sum(int(x.group(5)) for x in sm) if sm else sum(1 for l in lines if re.match(r'^\S+\s+TIMEOUT\b', l))
        return n, len(kills), 0, 0, bad, len(cand), 'per-mutant tier lines; TIMEOUT counted apart (%d, not kills under M10)' % timeouts
    if per:
        toks = [k.group(2).strip() for k in per]
        n = sum(int(s.group(1)) for s in sums) if sums else ''
        t = sum(1 for x in toks if x.startswith('timeout'))
        c = sum(1 for x in toks if x == 'crash')
        bad = None if tests is None else sum(1 for x in toks if not x.startswith('timeout') and x != 'crash' and x not in tests)
        return n, len(toks), t, c, bad, '', 'per-mutant KILLED lines'
    if sums:
        n = k = t = c = 0
        bad = 0 if tests is not None else None
        for s in sums:
            d = ast.literal_eval(s.group(3))
            n += int(s.group(1)); k += int(s.group(2))
            t += sum(v for kk, v in d.items() if kk.startswith('timeout'))
            c += d.get('crash', 0)
            if bad is not None:
                bad += sum(v for kk, v in d.items() if not kk.startswith('timeout') and kk != 'crash' and kk not in tests)
        return n, k, t, c, bad, '', 'summary line(s) only (first failing test file counts)'
    return '', 0, 0, 0, 0, '', 'no kill line and no summary line'


FAMILIES = [
    ('m2', [], None, 'tools/m2_mutants.py', "no recorded log in M10's logs/ or regression/; a crash of either child is recorded as 'tests' or 'contracts' "
     "(m2_mutants.py:243,245), so failure and crash could not be told apart from such a log"),
    ('m3', [], None, 'tools/m3_mutants.py', "no recorded log in M10; the attribution is the pattern's short name for any non-zero exit (m3_mutants.py:125,127), so "
     "failure and crash could not be told apart"),
    ('m4', [], None, 'tools/m4_mutants.py', 'no recorded log in M10'),
]


def main(argv):
    root, out_csv = argv[:2]
    L = os.path.join(root, 'logs')
    tl = test_lists(root)
    rows = []
    for fam, logs, key, basis, note in FAMILIES:
        rows.append([fam, 'none found', '-', basis, '', 0, 0, 0, 0, '', '-', note])
    m5_note = ("a kill's token is mut_runner's last stdout line, so a crash after it printed a file name cannot be told from a test failure; the child's "
               "exit code and stderr were not recorded")
    plan = []
    for f in sorted(x for x in os.listdir(L) if x.startswith('mutation_run_m5_')):
        plan.append(('m5', f, 'm5', 'tools/m5_mutants.py (top-level M5 log)', m5_note))
    for d in ('m61', 'm62', 'm63', 'm64', 'm65'):
        for f in sorted(os.listdir(os.path.join(L, d))):
            if f.startswith('mutation_run_m5_'):
                plan.append(('m5', '%s/%s' % (d, f), 'm5', 'tools/m5_mutants.py (rerun in %s; the log is a summary only)' % d.upper(),
                             'summary only: the per-mutant attribution is not recorded'))
    plan.append(('m6', 'mutation_run_m6.log', 'm6', 'tools/m6_mutants.py', m5_note))
    for f in ('m7/mutation_first_run_m7.log', 'm7/mutation_run_m7.log'):
        plan.append(('m7', f, 'm7', 'tools/m7_mutants.py (named in the log header)' if open(os.path.join(L, f)).readline().startswith('# tools/m7_mutants.py') else
                     'the log does not name its tool', 'summary counts only: the per-mutant attribution is not recorded'))
    for f in ('m71/mutation_first_run_m71.log', 'm71/mutation_run_m71.log', 'm72/mutation_first_run_lifecycle_m72.log', 'm72/mutation_run_m72.log',
              'm73/mutation_first_run_lifecycle_m73.log', 'm73/mutation_run_m73.log'):
        plan.append(('m7', f, None, 'the log does not name its tool (read from the header, not assumed)',
                     "which test list applies is not decidable from the log, so 'token not in test list' is not decidable; summary counts only"))
    plan.append(('m73_store', 'm73/store_mutation_run_m73.log', 'm73_store', 'tools/m73_store_mutants.py (the log name)', 'summary only'))
    plan.append(('m91', 'm91/mutation_run_m91.log', 'm91', 'tools/m91_mutants.py (the folder; the header holds only a source hash)', m5_note))
    for d in ('m92', 'm93', 'm94'):
        for f in sorted(os.listdir(os.path.join(L, d))):
            if f.startswith('mutation_'):
                plan.append(('m9x', '%s/%s' % (d, f), None, 'the log does not name its tool (read from the header, not assumed)',
                             "which test list applies is not decidable from the log; " + m5_note))
    m8_note = ("a kill whose reason is not 'tier N: FAIL:' or 'tier N: ERROR:' is a crash-kill candidate (m8_mutants.py:155); the child's exit code is not "
               "recorded; a timeout was neither a kill nor a survival under M10 and made the run exit 1")
    for f in (['m8/mutation_batch_%d.log' % i for i in range(1, 5)] + ['m8/mutation_first_pass/mutation_batch_%d.log' % i for i in range(1, 5)]
              + ['m81/mutation_batch_%d.log' % i for i in range(1, 5)] + ['m81/first_pass/mutation_batch_%d.log' % i for i in range(1, 3)]
              + ['m8r1/mutation_batch_%d.log' % i for i in range(1, 5)]):
        plan.append(('m8', f, 'm8', 'tools/m8_mutants.py (the log names AUIF verification and tiers)', m8_note))
    for f, key in (('f67/f67_mutants.log', 'f67'), ('f67/f67_mutants_first_run.log', 'f67'), ('f671/f671_mutants_batches.log', 'f671'),
                   ('f672/f672_mutants_batches.log', 'f672'), ('f673/f673_mutants_batches.log', 'f673'), ('f674/f674_mutants_batches.log', 'f674')):
        plan.append(('f67', f, key, 'tools/%s_mutants.py (the log name)' % key,
                     m5_note + "; f672 to f674 also record 'timeout (also under 300 s)' (f672_mutants.py:34-35), counted as timeout"))
    for f, key in (('mie1/mutation_first_run_summary.txt', 'mie'), ('mie1/mutation_run.txt', 'mie'), ('mie1_1/mutation_first_run_summary.txt', 'mie11'),
                   ('mie1_1/mutation_run.txt', 'mie11')):
        plan.append(('mie', f, key, 'tools/%s_mutants.py (the folder and the summary text)' % key, 'summary only: the per-mutant attribution is not recorded'))
    for fam, rel, key, basis, note in plan:
        p = os.path.join(L, rel)
        n, k, t, c, bad, cand, src = assess(p, tl.get(key) if key else None)
        rows.append([fam, 'logs/' + rel, sha(p), basis, n, k, t, c, 'not decidable' if bad is None else bad, cand, src, note])
    with open(out_csv, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(HEADER)
        w.writerows(rows)
    print('rows %d  timeout kills %d  crash kills %d' % (len(rows), sum(int(r[6]) for r in rows), sum(int(r[7]) for r in rows)))
    for r in rows:
        if int(r[6]) or int(r[7]) or (r[8] not in (0, 'not decidable')) or (r[9] not in ('', 0)):
            print('NOTE', r[1], 'timeout', r[6], 'crash', r[7], 'not_in_list', r[8], 'crash_candidates', r[9])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
