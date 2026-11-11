#!/usr/bin/env python3
"""Builder tool (outside the frozen tree): the corrective pass 2 comparisons, each on fresh extractions, one Python per call.
  golden  NEW.zip M10.zip PY OUT   E.2: M10's six golden runners on the M10 archive and on the stage 1 tree: full output and exit identical
                                   (the extraction root in the text replaced by <ROOT> on both sides; the raw outputs are kept)
  pairs   NEW.zip PY OUT           E.2: the 15 M10 runners beside their successors on the new tree, verdict by verdict (case or plant)
  b6      NEW.zip OLD.zip PY OUT   B.6: the 5 fault runners' plants and controls, new freeze against the superseded freeze
  k2      NEW.zip OLD.zip PY OUT   K.2: the 11 case runners' 386 case verdicts and causes, with status and exit, new against superseded
  m2      NEW.zip PY OUT           E.2 m2, under amendment 4 AM4-1 option A, in one process (exceeds the 2-hour job limit; superseded by:)
  m2h     NEW.zip PY OUT A B       AM4-1 harness: M10's run_one over MUT[A:B], 4 workers, M10 order; saves OUT/m2_logs/harness_A_B.json
  m2w     NEW.zip PY OUT           M10's m2_mutants.py as written (the AM4-1 'also recorded' run)
  m2s     NEW.zip PY OUT           the successor m2_mutants_s1 as written
  m2c     NEW.zip OUT              the AM4-1 comparison from the saved m2h, m2w and m2s outputs (runs nothing)
Every run: PYTHON -I (M10) or PYTHON -I -S (stage 1), from the extraction root, environment PATH LANG LC_ALL TZ TMPDIR only.
Writes OUT/<mode>.txt (the summary; its last line 'RESULT <mode> SAME' or 'RESULT <mode> DIFFERENT n') and OUT/<mode>_logs/.
Any difference outside a stated allowance is a stop-rule event (paper H).      BUILDER-EXECUTED: NOT INDEPENDENT."""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, zipfile

GOLDEN = ['run_golden', 'run_golden_det', 'run_golden_fin', 'run_golden_m3', 'run_golden_mie1', 'run_golden_mkt']
PAIRS = ['run_contracts', 'run_det_corpus', 'run_fin_corpus', 'run_guard_contract', 'run_ingest_corpus', 'run_m3_contracts',
         'run_m5_contracts', 'run_m6_contracts', 'run_m91_contracts', 'run_mkt_corpus', 'run_history_contract', 'run_faults',
         'run_m3_faults', 'run_m5_faults', 'run_m6_faults']
CASE_RUNNERS = ['run_contracts_s1', 'run_det_corpus_s1', 'run_fin_corpus_s1', 'run_guard_contract_s1', 'run_history_contract_s1',
                'run_ingest_corpus_s1', 'run_m3_contracts_s1', 'run_m5_contracts_s1', 'run_m6_contracts_s1', 'run_m91_contracts_s1',
                'run_mkt_corpus_s1']
FAULT_RUNNERS = ['run_faults_s1', 'run_history_contract_s1', 'run_m3_faults_s1', 'run_m5_faults_s1', 'run_m6_faults_s1']
M2 = {'m10_sha256': 'fe1fd878fee975dff6dfdbdf27a7124665228a6efef624c396b40f7d68cd157b', 'ids': 199, 'invalid': 'RI10-query-crosses-tenants',
      'invalid_position': 51, 'common_sha256': 'd5da4f9a3e083a30952c46b65491f907df832f7183710be088df08b15016694c',
      's1_ids_sha256': '649e0e48d843bf4e792727b5b7789ff9a9a0d3ddb346f36dc51693d652f3384e'}
AM53_IDS = ('CA01-float-allowed', 'RI13-input-aliased')     # amendment 5 AM5-3 A1: the owner-selected ids (AM5-4 allowance paragraph)
HIST_CANDIDATE = ('import tools.evkit as _E\nimport tools.run_history_contract_s1 as _S\n'
                  '_H = _E.load_m10_prefix("run_history_contract", "if opt(\'--factory\'):", _S.M10_SHA256)\n'
                  'F = _H.env_for(_H.InMemoryRecordStore)     # the reference store, as M10 runs it\n')


def extract(zp, dest):
    with zipfile.ZipFile(zp) as z:
        z.extractall(dest)
    tops = [d for d in os.listdir(dest) if os.path.isdir(os.path.join(dest, d))]
    assert len(tops) == 1, tops
    return os.path.join(dest, tops[0])


def run(py, root, args, tmp, isolated_site=True, timeout=7200):
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp}
    cmd = [py, '-I'] + (['-S'] if isolated_site else []) + args
    p = subprocess.run(cmd, cwd=root, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr, ' '.join(cmd)


class Out:
    def __init__(self, out, mode):
        self.dir = os.path.join(out, mode + '_logs')
        os.makedirs(self.dir, exist_ok=True)
        self.lines, self.diffs, self.mode, self.path = [], 0, mode, os.path.join(out, mode + '.txt')

    def log(self, name, cmd, code, text):
        p = os.path.join(self.dir, name + '.txt')
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write('# %s\n# exit %d\n%s' % (cmd, code, text))
        return hashlib.sha256(open(p, 'rb').read()).hexdigest()

    def say(self, s):
        self.lines.append(s)
        print(s, flush=True)

    def differ(self, s):
        self.diffs += 1
        self.say('DIFFERENT ' + s)

    def close(self):
        self.say('RESULT %s %s' % (self.mode, 'SAME' if not self.diffs else 'DIFFERENT %d' % self.diffs))
        with open(self.path, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(self.lines) + '\n')
        return 0 if not self.diffs else 1


def result_fields(text):
    m = re.search(r'(?m)^RESULT v=\d+ .*$', text)
    if not m:
        return {}
    return dict(kv.split('=', 1) for kv in m.group(0).split()[1:] if '=' in kv)


def s1_items(text, kind):
    if kind == 'cases':
        return {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(r'(?m)^CASE (\S+) (\S+) cause=(\S+)$', text)}
    return {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(r'(?m)^PLANT (\S+) (\S+) cause=(\S+)$', text)}


def hist_candidate(tmp):
    d = os.path.join(tmp, 'hist_candidate')
    os.makedirs(os.path.join(d, 'hist_ref'), exist_ok=True)
    with open(os.path.join(d, 'hist_ref', '__init__.py'), 'w') as fh:
        fh.write(HIST_CANDIDATE)
    return d


def case_args(tool, tmp):
    return (['--path', hist_candidate(tmp), '--factory', 'hist_ref:F'] if tool == 'run_history_contract_s1' else [])


def mode_golden(new_zip, m10_zip, py, out):
    o = Out(out, 'golden')
    tmp = tempfile.mkdtemp(prefix='s1_cmp_g_')
    try:
        new, m10 = extract(new_zip, os.path.join(tmp, 'new')), extract(m10_zip, os.path.join(tmp, 'm10'))
        for g in GOLDEN:
            res = {}
            for side, root in (('m10', m10), ('s1', new)):
                if not os.path.exists(os.path.join(root, 'tools', g + '.py')):
                    o.differ('%s missing on %s' % (g, side))
                    continue
                t = tempfile.mkdtemp(prefix='s1_cmp_gt_', dir=tmp)
                code, text, cmd = run(py, root, ['tools/%s.py' % g], t, isolated_site=False)
                h = o.log('%s_%s' % (g, side), cmd, code, text)
                res[side] = (code, text.replace(root, '<ROOT>'), h, hashlib.sha256(open(os.path.join(root, 'tools', g + '.py'), 'rb').read()).hexdigest())
            if len(res) == 2:
                same = res['m10'][0] == res['s1'][0] and res['m10'][1] == res['s1'][1]
                o.say('%-18s file m10=%s s1=%s  exit m10=%d s1=%d  output %s  logs %s %s' % (
                    g, res['m10'][3][:12], res['s1'][3][:12], res['m10'][0], res['s1'][0], 'identical' if same else 'DIFFERS',
                    res['m10'][2][:12], res['s1'][2][:12]))
                if not same:
                    o.differ(g)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return o.close()


def m10_verdicts(text):
    """M10's per-case or per-plant verdict lines: PASS/FAIL <id> and CAUGHT/MISSED [faulty store] <id>."""
    v = {}
    section = ''
    for l in text.splitlines():
        if l.startswith('== '):
            section = l
        m = re.match(r'^(PASS|FAIL|CAUGHT|MISSED) (?:faulty store )?(\S+)', l)
        if m:
            v[m.group(2)] = m.group(1)
    return v


def mode_pairs(new_zip, py, out):
    o = Out(out, 'pairs')
    tmp = tempfile.mkdtemp(prefix='s1_cmp_p_')
    try:
        root = extract(new_zip, os.path.join(tmp, 'new'))
        for m in PAIRS:
            t = tempfile.mkdtemp(prefix='s1_cmp_pt_', dir=tmp)
            c10, t10, cmd10 = run(py, root, ['tools/%s.py' % m], t, isolated_site=False)
            o.log(m + '_m10', cmd10, c10, t10)
            mv = m10_verdicts(t10)
            sv = {}
            runs = [('cases', [])] if m not in ('run_faults', 'run_m3_faults', 'run_m5_faults', 'run_m6_faults') else [('sabotage', [])]
            if m == 'run_history_contract':
                runs = [('sabotage', []), ('cases', None)]
            for kind, extra in runs:
                args = case_args(m + '_s1', t) if extra is None else extra
                cs, ts, cmds = run(py, root, ['tools/%s_s1.py' % m] + args, t)
                o.log('%s_s1_%s' % (m, kind), cmds, cs, ts)
                for k, (st, cause) in s1_items(ts, kind).items():
                    sv[k.split('/', 1)[1] if kind == 'cases' else k] = st
                o.say('%-22s s1 %-8s exit=%d status=%s' % (m, kind, cs, result_fields(ts).get('status')))
            o.say('%-22s m10 exit=%d verdicts=%d  s1 verdicts=%d' % (m, c10, len(mv), len(sv)))
            if set(mv) != set(sv):
                o.differ('%s ids: only m10 %s; only s1 %s' % (m, sorted(set(mv) - set(sv)), sorted(set(sv) - set(mv))))
            for k in sorted(set(mv) & set(sv)):
                if mv[k] != sv[k]:
                    o.differ('%s %s m10=%s s1=%s' % (m, k, mv[k], sv[k]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return o.close()


def _both(new_zip, old_zip, tools, kind, py, out, mode):
    o = Out(out, mode)
    tmp = tempfile.mkdtemp(prefix='s1_cmp_%s_' % mode)
    total = 0
    try:
        roots = {'new': extract(new_zip, os.path.join(tmp, 'new')), 'old': extract(old_zip, os.path.join(tmp, 'old'))}
        for tool in tools:
            got = {}
            for side, root in roots.items():
                t = tempfile.mkdtemp(prefix='s1_cmp_t_', dir=tmp)
                args = case_args(tool, t) if kind == 'cases' else []
                code, text, cmd = run(py, root, ['tools/%s.py' % tool] + args, t)
                o.log('%s_%s' % (tool, side), cmd, code, text)
                f = result_fields(text)
                ctl = tuple(sorted(re.findall(r'(?m)^CONTROL (start|end) (\S+) cause=(\S+)', text)))   # B.6: the CONTROL values and causes
                got[side] = (s1_items(text, kind), code, f.get('status'), f.get('control_start'), f.get('control_end'), f.get('v'), ctl)
            n, ol = got['new'], got['old']
            total += len(n[0])
            o.say('%-24s items new=%d old=%d  exit new=%d old=%d  status new=%s old=%s  controls new=%s/%s old=%s/%s  v new=%s old=%s' % (
                tool, len(n[0]), len(ol[0]), n[1], ol[1], n[2], ol[2], n[3], n[4], ol[3], ol[4], n[5], ol[5]))
            if n[0] != ol[0]:
                for k in sorted(set(n[0]) | set(ol[0])):
                    if n[0].get(k) != ol[0].get(k):
                        o.differ('%s %s new=%s old=%s' % (tool, k, n[0].get(k), ol[0].get(k)))
            o.say('%-24s CONTROL lines new=%s old=%s' % (tool, list(n[6]), list(ol[6])))
            for i, what in ((1, 'exit'), (2, 'status'), (3, 'control_start'), (4, 'control_end'), (6, 'CONTROL values and causes')):
                if n[i] != ol[i]:
                    o.differ('%s %s new=%s old=%s' % (tool, what, n[i], ol[i]))
        o.say('items compared: %d' % total)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return o.close()


def mode_m2(new_zip, py, out):
    """Amendment 4, AM4-1 option A: M10's verdicts from M10's own run_one, called by this harness; M10's script also run as written."""
    o = Out(out, 'm2')
    tmp = tempfile.mkdtemp(prefix='s1_cmp_m2_')
    try:
        root = extract(new_zip, os.path.join(tmp, 'new'))
        sha = hashlib.sha256(open(os.path.join(root, 'tools', 'm2_mutants.py'), 'rb').read()).hexdigest()
        o.say('tools/m2_mutants.py %s (expected %s)' % (sha, M2['m10_sha256']))
        if sha != M2['m10_sha256']:
            o.differ('m2_mutants.py hash')
            return o.close()
        harness = r'''
import json, os, shutil, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.getcwd())
import importlib.util
spec = importlib.util.spec_from_file_location('m2_mutants_m10', os.path.join(os.getcwd(), 'tools', 'm2_mutants.py'))
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
tmp = tempfile.mkdtemp(prefix='m2_mut_')
try:
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(lambda m: M.run_one(m, tmp), M.MUT))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print(json.dumps({'ids': [m[0] for m in M.MUT], 'results': res, 'equiv': sorted(k for k, v in M.EQUIV.items() if v)}))
'''
        t = tempfile.mkdtemp(prefix='s1_cmp_m2t_', dir=tmp)
        code, text, cmd = run(py, root, ['-c', harness], t, isolated_site=False, timeout=14400)
        o.log('m10_run_one_harness', cmd, code, text)
        data = json.loads(text.strip().splitlines()[-1])
        ids, equiv = data['ids'], set(data['equiv'])
        m10 = {}
        for mid, st, info in data['results']:
            m10[mid] = ('ERROR', info) if st == 'ERROR' else ('KILLED', info) if st == 'KILLED' else (('EQUIVALENT', '') if mid in equiv else ('SURVIVED', ''))
        sys.path.insert(0, root)
        import tools.evkit as E
        o.say('M10 ids %d; %s at position %d; ERROR ids %s' % (len(ids), M2['invalid'], ids.index(M2['invalid']) + 1,
                                                             sorted(k for k, v in m10.items() if v[0] == 'ERROR')))
        common = [i for i in ids if m10[i][0] != 'ERROR']
        if (len(ids), ids.index(M2['invalid']) + 1, E.sha256_lines(common)) != (M2['ids'], M2['invalid_position'], M2['common_sha256']):
            o.differ('the fixed values: %d ids, position %d, common %s' % (len(ids), ids.index(M2['invalid']) + 1, E.sha256_lines(common)))
        c2, t2, cmd2 = run(py, root, ['tools/m2_mutants.py'], t, isolated_site=False, timeout=14400)
        o.log('m10_script_as_written', cmd2, c2, t2)
        printed = re.findall(r'(?m)^(KILLED|SURVIVED|EQUIVALENT) +(\S+)', t2)
        o.say('M10 script as written: exit %d, %d verdicts printed, then %s' % (c2, len(printed), (re.findall(r'(?m)^ERROR .*$', t2) or ['-'])[0][:100]))
        for st, mid in printed:
            if m10[mid][0] != st:
                o.differ('m10 script and run_one disagree on %s: %s %s' % (mid, st, m10[mid][0]))
        c3, t3, cmd3 = run(py, root, ['tools/m2_mutants_s1.py'], t, timeout=14400)
        o.log('m2_mutants_s1', cmd3, c3, t3)
        f = result_fields(t3)
        s1 = {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(r'(?m)^MUTANT (\S+) (\S+) cause=(\S+)$', t3)}
        o.say('m2_mutants_s1: exit %d status %s ids_sha256 %s (expected %s), %d MUTANT lines' % (c3, f.get('status'), f.get('ids_sha256'),
                                                                                          M2['s1_ids_sha256'], len(s1)))
        if f.get('ids_sha256') != M2['s1_ids_sha256'] or len(s1) != M2['ids']:
            o.differ('successor ids')
        allowed = []
        for mid in ids:
            a, b = m10[mid], s1.get(mid, ('MISSING', '-'))
            if mid == M2['invalid']:
                allowed.append('%s: M10 %s, successor %s %s' % (mid, a[0], b[0], b[1]))
                continue
            if a[0] == b[0]:
                continue
            # AM4-1: only an M10 kill by timeout (M10's run_one does not tell a crash from a test kill, so no allowance is made on
            # that ground: fail closed) against a successor INDETERMINATE.  Mistake 32: the first version did not check M10's info.
            if a[0] == 'KILLED' and a[1] == 'timeout' and b[0] == 'INDETERMINATE' and b[1] in ('timeout', 'crash_no_result', 'crash'):
                allowed.append('%s: M10 KILLED (by %s), successor INDETERMINATE %s (DP-2.1 (a))' % (mid, a[1], b[1]))
                continue
            o.differ('%s M10 %s (%s) successor %s %s' % (mid, a[0], a[1], b[0], b[1]))
        o.say('allowed differences (%d):' % len(allowed))
        for x in allowed:
            o.say('  ' + x)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return o.close()


# --- m2 in steps (added 2026-11-07 after the one-process m2 mode hit the 2-hour job limit; see PASS2_BUILD_LOG.md).
# Same harness and the same comparison as mode_m2; each step is its own process, on its own fresh extraction, and keeps its
# raw output in OUT/m2_logs/.  m2h runs M10's run_one over the slice MUT[a:b], in M10's order, with M10's 4 workers; the
# slices together cover every item exactly once (m2c checks this).  m2w is M10's script as written; m2s is the successor.

HARNESS_SLICE = r'''
import json, os, shutil, sys, tempfile, subprocess
from concurrent.futures import ThreadPoolExecutor
a, b = int(sys.argv[1]), int(sys.argv[2])
sys.path.insert(0, os.getcwd())
import importlib.util
spec = importlib.util.spec_from_file_location('m2_mutants_m10', os.path.join(os.getcwd(), 'tools', 'm2_mutants.py'))
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
tmp = tempfile.mkdtemp(prefix='m2_mut_')
try:
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(lambda m: M.run_one(m, tmp), M.MUT[a:b]))
    du = subprocess.run(['du', '-sb', os.environ['TMPDIR']], capture_output=True, text=True).stdout.split()[0]
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print(json.dumps({'a': a, 'b': b, 'ids': [m[0] for m in M.MUT], 'results': res,
                  'equiv': sorted(k for k, v in M.EQUIV.items() if v), 'tmpdir_bytes_at_end': int(du)}))
'''


def _m2_root(new_zip, tmp, o):
    root = extract(new_zip, os.path.join(tmp, 'new'))
    sha = hashlib.sha256(open(os.path.join(root, 'tools', 'm2_mutants.py'), 'rb').read()).hexdigest()
    o.say('tools/m2_mutants.py %s (expected %s)' % (sha, M2['m10_sha256']))
    if sha != M2['m10_sha256']:
        o.differ('m2_mutants.py hash')
        return None
    return root


def mode_m2_step(step, new_zip, py, out, a=None, b=None):
    name = {'m2h': 'm2h_%03d_%03d' % (a, b) if step == 'm2h' else '', 'm2w': 'm2w', 'm2s': 'm2s'}[step]
    o = Out(out, name)
    os.rmdir(o.dir)                     # Out made OUT/<name>_logs; the m2 steps keep their logs together in OUT/m2_logs
    o.dir = os.path.join(out, 'm2_logs')
    os.makedirs(o.dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='s1_cmp_m2_')
    try:
        root = _m2_root(new_zip, tmp, o)
        if root is None:
            return o.close()
        t = tempfile.mkdtemp(prefix='s1_cmp_m2t_', dir=tmp)
        if step == 'm2h':
            code, text, cmd = run(py, root, ['-c', HARNESS_SLICE, str(a), str(b)], t, isolated_site=False, timeout=7000)
            o.log('harness_%03d_%03d' % (a, b), cmd, code, text)
            data = json.loads(text.strip().splitlines()[-1])
            with open(os.path.join(o.dir, 'harness_%03d_%03d.json' % (a, b)), 'w') as fh:
                json.dump(data, fh)
            o.say('harness slice %d:%d exit %d, %d results, TMPDIR bytes at end %d' % (a, b, code, len(data['results']), data['tmpdir_bytes_at_end']))
        elif step == 'm2w':
            code, text, cmd = run(py, root, ['tools/m2_mutants.py'], t, isolated_site=False, timeout=6 * 3600)
            o.log('m10_script_as_written', cmd, code, text)
            o.say('M10 script as written: exit %d' % code)
        else:
            # the successor as written (default --jobs 2) takes longer than the 2-hour job limit here; it runs detached (S13)
            code, text, cmd = run(py, root, ['tools/m2_mutants_s1.py'], t, timeout=8 * 3600)
            o.log('m2_mutants_s1', cmd, code, text)
            o.say('m2_mutants_s1: exit %d; %s' % (code, (re.findall(r'(?m)^RESULT .*$', text) or ['-'])[0]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return o.close()


def _logged(path):
    text = open(path, encoding='utf-8').read()
    head, _, body = text.partition('\n')
    code = int(body.partition('\n')[0].split()[-1])
    return code, body.partition('\n')[2]


def mode_m2_compare(new_zip, out):
    """The E.2 m2 comparison of mode_m2, made from the saved outputs of the m2h, m2w and m2s steps."""
    o = Out(out, 'm2')
    d = os.path.join(out, 'm2_logs')
    slices = sorted(f for f in os.listdir(d) if re.fullmatch(r'harness_\d{3}_\d{3}\.json', f))
    data = [json.load(open(os.path.join(d, f))) for f in slices]
    ids = data[0]['ids']
    equiv = set(data[0]['equiv'])
    covered = []
    for x in data:
        if x['ids'] != ids or set(x['equiv']) != equiv:
            o.differ('slice %d:%d loaded a different MUT or EQUIV' % (x['a'], x['b']))
        covered += [r[0] for r in x['results']]
    o.say('harness slices: %s; ids covered %d' % (', '.join('%d:%d' % (x['a'], x['b']) for x in data), len(covered)))
    if covered != ids:
        o.differ('the slices do not cover every M10 id exactly once, in M10 order')
    m10 = {}
    for x in data:
        for mid, st, info in x['results']:
            m10[mid] = ('ERROR', info) if st == 'ERROR' else ('KILLED', info) if st == 'KILLED' else (('EQUIVALENT', '') if mid in equiv else ('SURVIVED', ''))
    tmp = tempfile.mkdtemp(prefix='s1_cmp_m2c_')
    try:
        root = extract(new_zip, os.path.join(tmp, 'new'))
        sys.path.insert(0, root)
        import tools.evkit as E
        o.say('M10 ids %d; %s at position %d; ERROR ids %s' % (len(ids), M2['invalid'], ids.index(M2['invalid']) + 1,
                                                             sorted(k for k, v in m10.items() if v[0] == 'ERROR')))
        common = [i for i in ids if m10[i][0] != 'ERROR']
        if (len(ids), ids.index(M2['invalid']) + 1, E.sha256_lines(common)) != (M2['ids'], M2['invalid_position'], M2['common_sha256']):
            o.differ('the fixed values: %d ids, position %d, common %s' % (len(ids), ids.index(M2['invalid']) + 1, E.sha256_lines(common)))
        o.say('M10 run_one: KILLED %d (tests %d, contracts %d, timeout %d), EQUIVALENT %d, SURVIVED %d, ERROR %d' % (
            sum(v[0] == 'KILLED' for v in m10.values()), sum(v == ('KILLED', 'tests') for v in m10.values()),
            sum(v == ('KILLED', 'contracts') for v in m10.values()), sum(v == ('KILLED', 'timeout') for v in m10.values()),
            sum(v[0] == 'EQUIVALENT' for v in m10.values()), sum(v[0] == 'SURVIVED' for v in m10.values()),
            sum(v[0] == 'ERROR' for v in m10.values())))
        w = os.path.join(d, 'm10_script_as_written.txt')
        if os.path.exists(w):
            c2, t2 = _logged(w)
            printed = re.findall(r'(?m)^(KILLED|SURVIVED|EQUIVALENT) +(\S+)', t2)
            o.say('M10 script as written: exit %d, %d verdicts printed, then %s' % (c2, len(printed), (re.findall(r'(?m)^ERROR .*$', t2) or ['-'])[0][:100]))
            for st, mid in printed:
                if m10[mid][0] != st:
                    o.differ('m10 script and run_one disagree on %s: %s %s' % (mid, st, m10[mid][0]))
        else:
            o.say('M10 script as written: NOT RUN (no m10_script_as_written.txt)')
        c3, t3 = _logged(os.path.join(d, 'm2_mutants_s1.txt'))
        f = result_fields(t3)
        s1 = {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(r'(?m)^MUTANT (\S+) (\S+) cause=(\S+)$', t3)}
        o.say('m2_mutants_s1: exit %d status %s ids_sha256 %s (expected %s), %d MUTANT lines' % (c3, f.get('status'), f.get('ids_sha256'),
                                                                                          M2['s1_ids_sha256'], len(s1)))
        if f.get('ids_sha256') != M2['s1_ids_sha256'] or len(s1) != M2['ids']:
            o.differ('successor ids')
        allowed = []
        for mid in ids:
            a, b = m10[mid], s1.get(mid, ('MISSING', '-'))
            if mid == M2['invalid']:
                allowed.append('%s: M10 %s, successor %s %s' % (mid, a[0], b[0], b[1]))
                continue
            if a[0] == b[0]:
                continue
            # AM4-1: only an M10 kill by timeout (M10's run_one does not tell a crash from a test kill, so no allowance is made on
            # that ground: fail closed) against a successor INDETERMINATE.  Mistake 32: the first version did not check M10's info.
            if a[0] == 'KILLED' and a[1] == 'timeout' and b[0] == 'INDETERMINATE' and b[1] in ('timeout', 'crash_no_result', 'crash'):
                allowed.append('%s: M10 KILLED (by %s), successor INDETERMINATE %s (AM4-1 allowance)' % (mid, a[1], b[1]))
                continue
            # Amendment 5, AM5-3 option A1 as AM5-4's "AM5-3 comparison allowance" paragraph limits it (rewritten in the 2026-11-11
            # recovery from that paragraph; the 303b6414-era version was lost): only the selected ids, only M10 KILLED with
            # information timeout against a successor EQUIVALENT.  Every other id or status combination stays a difference (a stop).
            if mid in AM53_IDS and a == ('KILLED', 'timeout') and b[0] == 'EQUIVALENT':
                allowed.append('%s: M10 KILLED (by timeout), successor EQUIVALENT %s (AM5-3 A1 allowance)' % (mid, b[1]))
                continue
            o.differ('%s M10 %s (%s) successor %s %s' % (mid, a[0], a[1], b[0], b[1]))
        o.say('allowed differences (%d):' % len(allowed))
        for x in allowed:
            o.say('  ' + x)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return o.close()


def main(argv):
    mode = argv[0]
    if mode == 'm2h':
        return mode_m2_step('m2h', argv[1], argv[2], argv[3], int(argv[4]), int(argv[5]))
    if mode in ('m2w', 'm2s'):
        return mode_m2_step(mode, argv[1], argv[2], argv[3])
    if mode == 'm2c':
        return mode_m2_compare(argv[1], argv[2])
    if mode == 'golden':
        return mode_golden(argv[1], argv[2], argv[3], argv[4])
    if mode == 'pairs':
        return mode_pairs(argv[1], argv[2], argv[3])
    if mode == 'b6':
        return _both(argv[1], argv[2], FAULT_RUNNERS, 'sabotage', argv[3], argv[4], 'b6')
    if mode == 'k2':
        return _both(argv[1], argv[2], CASE_RUNNERS, 'cases', argv[3], argv[4], 'k2')
    if mode == 'm2':
        return mode_m2(argv[1], argv[2], argv[3])
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
