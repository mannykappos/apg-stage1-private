#!/usr/bin/env python3
"""Sabotage of the APG-M8 package: each case damages ONE thing in a private copy of the whole package - the AUIF dependency, the configuration, the declarations, an earlier
release's file, the package contents, or the data AUIF delivers - and runs the ONE check that must catch it.  CAUGHT = that check failed (exit code not 0).  A case
whose check passes is MISSED.  A time-out is INCOMPLETE (neither).  The copy is removed afterwards; the package itself is never touched.
Usage: python3 -I tools/sabotage_m8.py --list | [--only ID[,ID]] [--timeout SECONDS]"""
import json, os, shutil, subprocess, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True


def _edit(path, fn, binary=False):
    mode = 'b' if binary else ''
    data = open(path, 'r' + mode, **({} if binary else {'encoding': 'utf-8'})).read()
    open(path, 'w' + mode, **({} if binary else {'encoding': 'utf-8'})).write(fn(data))


def flip_zip(r):
    p = os.path.join(r, 'third_party', 'auif_rev14', 'AUIF_Independent_Build_v1.0_rev14.zip')      # APG-M8.1: rev14
    b = bytearray(open(p, 'rb').read())
    b[1000] ^= 1
    open(p, 'wb').write(bytes(b))


def sidecar(r):
    _edit(os.path.join(r, 'third_party', 'auif_rev14', 'AUIF_Independent_Build_v1.0_rev14.zip.sha256'), lambda s: '0' * 64 + s[64:])


def pack_deviation_form(r):
    p = os.path.join(r, 'auif_m8', 'packs', 'apg-m8-bz-master.json')
    d = json.load(open(p))
    m = next(x for x in d['mappings'] if x['kind'] == 'FIELD')
    m['canonical_ref'] = m['canonical_ref'][len('module.apg.'):]                         # APG-M8.1: back to the ended DEV-M8-01 form
    open(p, 'w').write(json.dumps(d, indent=1, sort_keys=True) + '\n')


def lock_definition(r):
    _edit(os.path.join(r, 'auif_m8', 'definitions', 'construction_definitions.json'), lambda s: s.replace('"status": "PROPOSED"', '"status": "LOCKED"', 1))


def pack_fingerprint(r):
    p = os.path.join(r, 'auif_m8', 'packs', 'apg-m8-bz-master.json')
    d = json.load(open(p))
    d['schema_expectations']['compatible_fingerprints'] = ['0' * 64]
    open(p, 'w').write(json.dumps(d, indent=1, sort_keys=True) + '\n')


def edit_r2_code(r):
    _edit(os.path.join(r, 'apg', 'ingest', 'pipeline.py'), lambda s: s + '\n# changed\n')


def edit_r2_test(r):
    _edit(os.path.join(r, 'tests', 'test_ingest_pipeline.py'), lambda s: s + '\n# changed\n')


def add_file(r):
    open(os.path.join(r, 'apg', 'extra_module.py'), 'w').write('X = 1\n')


def undeclare_golden(r):
    p = os.path.join(r, 'auif_m8', 'PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json')
    d = json.load(open(p))
    d['golden']['M3'] = []
    open(p, 'w').write(json.dumps(d, indent=1) + '\n')


def move_corpus_case(r):
    p = os.path.join(r, 'auif_m8', 'PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json')
    d = json.load(open(p))
    d['corpus']['same'].append('R01')
    del d['corpus']['differs']['R01']
    open(p, 'w').write(json.dumps(d, indent=1) + '\n')


def edit_register_row(r):
    _edit(os.path.join(r, 'programme', 'FINDINGS_REGISTER.csv'), lambda s: s.replace('Open - not corrected', 'Closed', 1))


def change_builder_zero_value(r):
    _edit(os.path.join(r, 'builder_zero', 'zero_one', 'SRC-01_accounting', 'ap_invoices.csv'), lambda s: s.replace('INV-0002,', 'INV-0002X,', 1))


def drop_lineage(r):
    _edit(os.path.join(r, 'apg_auif', 'intake.py'), lambda s: s.replace("'batch_id': batch.batch_id}", "}", 1))


def gate_ignores_state(r):
    _edit(os.path.join(r, 'apg_auif', 'gate.py'), lambda s: s.replace("elif st['state'] != 'ACTIVE':", "elif False:", 1))


def gate_accepts_empty_source(r):
    _edit(os.path.join(r, 'apg_auif', 'intake.py'), lambda s: s.replace("            if r.get('empty') or read_nothing:", "            if False:", 1))


def composite_identity_dropped(r):
    _edit(os.path.join(r, 'apg_auif', 'client.py'), lambda s: s.replace("ident.setdefault(e, nk[0] if len(nk) == 1 else list(nk))", "ident.setdefault(e, nk[0])", 1))


def notices_block_batches(r):
    _edit(os.path.join(r, 'apg_auif', 'intake.py'), lambda s: s.replace("        if e.get('kind') == NOTICE and batch.mode == 'events':\n            continue", "        if False:\n            continue", 1))


T = lambda f: ['tools/run_m8_tests.py', '--file', f]
CASES = [
    ('S01', 'one byte of the AUIF ZIP flipped', flip_zip, T('test_m8_dependency.py')),
    ('S02', 'the AUIF sidecar hash changed', sidecar, T('test_m8_dependency.py')),
    ('S03', 'a stored pack field reference put back in the ended DEV-M8-01 form (the contract form broken)', pack_deviation_form, T('test_m8_dev01.py')),
    ('S04', 'a construction definition marked LOCKED', lock_definition, T('test_m8_layout_config.py')),
    ('S05', 'a stored pack accepts another schema fingerprint', pack_fingerprint, T('test_m8_layout_config.py')),
    ('S06', 'an R2 application file edited', edit_r2_code, T('test_m8_boundary.py')),
    ('S07', 'an existing R2 test edited', edit_r2_test, T('test_m8_boundary.py')),
    ('S08', 'an undeclared file added to the package', add_file, T('test_m8_boundary.py')),
    ('S09', 'the declared golden difference removed from the declaration', undeclare_golden, T('test_m8_path_equivalence.py')),
    ('S10', 'a corpus case declared "same" although AUIF refuses it', move_corpus_case, T('test_m8_corpus.py')),
    ('S11', 'an R2 register row edited', edit_register_row, ['tools/run_regression_m8.py', '--step', 'R03']),
    ('S12', 'a Builder Zero source file changed (R2 data must stay byte-identical)', change_builder_zero_value, ['tools/run_regression_m8.py', '--step', 'R01']),
    ('S13', 'a lineage field no longer written', drop_lineage, T('test_m8_lineage.py')),
    ('S14', 'the gate no longer checks the integration state', gate_ignores_state, T('test_m8_no_fallback.py')),
    ('S15', 'M8-R1: an empty source is accepted as current data again (finding M8-F7)', gate_accepts_empty_source, T('test_m8r1_empty_source.py')),
    ('S16', 'M8.1: a composite key is no longer declared to AUIF as the source identity (only its first field)', composite_identity_dropped, T('test_m8_findings.py')),
    ('S17', 'M8.1: AUIF\'s event notices are treated as integrity failures (applied events would be refused)', notices_block_batches, T('test_m8_events.py')),
]


def run(case, timeout):
    cid, desc, fn, cmd = case
    d = tempfile.mkdtemp(prefix='apg_m8_sab_')
    t = time.time()
    try:
        r = os.path.join(d, 'pkg')
        shutil.copytree(ROOT, r, ignore=shutil.ignore_patterns('__pycache__'))
        fn(r)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        env.pop('APG_AUIF_ROOT', None)
        env.pop('APG_ROOT', None)
        try:
            p = subprocess.run([sys.executable, '-I'] + cmd, cwd=r, env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return cid, 'INCOMPLETE', desc, time.time() - t, 'timed out (neither caught nor missed)'
        out = (p.stdout + p.stderr).strip().splitlines()
        return cid, 'CAUGHT' if p.returncode != 0 else 'MISSED', desc, time.time() - t, (out[-1] if out else '')
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    a = sys.argv[1:]
    if '--list' in a:
        for c in CASES:
            print('%s  %-95s  %s' % (c[0], c[1], ' '.join(c[3])))
        return 0
    sel = CASES
    if '--only' in a:
        ids = set(a[a.index('--only') + 1].split(','))
        sel = [c for c in CASES if c[0] in ids]
    timeout = int(a[a.index('--timeout') + 1]) if '--timeout' in a else 900
    res = []
    for c in sel:
        cid, st, desc, secs, last = run(c, timeout)
        res.append(st)
        print('%s %-10s %5.0fs  %s  [%s]' % (cid, st, secs, desc, last[:140]), flush=True)
    print('sabotage cases %d: caught %d, missed %d, incomplete %d' % (len(res), res.count('CAUGHT'), res.count('MISSED'), res.count('INCOMPLETE')))
    return 0 if res.count('CAUGHT') == len(res) else 1


if __name__ == '__main__':
    sys.exit(main())
