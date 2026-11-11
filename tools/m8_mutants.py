#!/usr/bin/env python3
"""Mutation testing of the APG-M8 adapter (apg_auif/).  Each mutant removes or bends ONE safety check (a tenant check, a lineage check, a gate rule, the reference form
check, the AUIF hash checks, ...).  A mutant is applied to a private copy of apg_auif/ (with an unchanged copy of apg/ and of the AUIF ZIP), and the M8 tests are run against
that copy (APG_ROOT); the AUIF tree used is the one this tool verified first (APG_AUIF_ROOT).

  tier 1  the fast M8 test files (everything except path equivalence), stopping at the first failure
  tier 2  only for a mutant tier 1 did not kill: the path-equivalence file
A mutant is KILLED when a tier fails; SURVIVED when both pass (EQUIVALENT instead when it is one of the documented equivalents below); TIMEOUT when a tier ran out of time - a timeout is NEITHER a kill NOR a survival: rerun it with
--timeout larger.  A control run on the unmutated copy must pass first, or nothing is reported.
Usage: python3 -I tools/m8_mutants.py --list | [--batch K/N] [--only ID,ID] [--jobs J] [--timeout SECONDS]"""
import os, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from apg_auif import dependency                                    # noqa: E402

TIER1 = ['test_m8_dependency', 'test_m8_dev01', 'test_m8_conformance', 'test_m8_integrity', 'test_m8_no_fallback', 'test_m8_events', 'test_m8_delivery_rules',
         'test_m8_findings', 'test_m8_corpus', 'test_m8_layout_config', 'test_m8_boundary', 'test_m8_lineage', 'test_m8_definitions', 'test_m8r1_empty_source']
TIER2 = ['test_m8_path_equivalence']

EQUIVALENT = {   # mutants no test can kill, with the reason; reported as EQUIVALENT when they survive, never counted as killed
    'MD-02': 'Every core file is also in AUIF\'s manifest, whose tree hash is pinned (MD-03 keeps that comparison): the core cannot change while the pinned manifest check passes '
             'without a SHA-256 collision. The core-tree comparison is a second, deliberate line of defence.',
    'MI-39': 'M8-R1: AUIF reports empty (NO_DATA) only when the first page brings no data, so an empty report always has no delivery, no invalid or ambiguous object, no failure '
             'and no refusal: read_nothing is then true as well. The explicit empty test is kept so that the reason names NO_DATA and the rule does not depend on that coincidence.',
    'MI-36': 'The adapter skips a blank delivery by the same test the M3 parser uses for a blank row (every cell empty after stripping), so the number of parsed rows always equals '
             'the number of non-blank deliveries; the check guards against a future change of either rule.',
}
I, M, G, A, P, C, D, L = ('apg_auif/%s.py' % x for x in ('intake', 'module', 'gate', 'assess', 'pack', 'client', 'dependency', 'lineage'))
MUTANTS = [
    # intake.py: per-delivery integrity checks
    ('MI-01', I, "if obj.get('tenant_id') != t or ob.get('tenant_id') != t:", "if False:"),
    ('MI-02', I, "if obj.get('validation_state') != 'VALID':", "if False:"),
    ('MI-03', I, "if obj.get('canonical_type') != ent['concept'] or obj.get('canonical_model_version') != ent['model_version']:", "if False:"),
    ('MI-04', I, "    if got != want:", "    if False:"),
    ('MI-05', I, "if probs or not (pk and fp and so and osv):", "if not (pk and fp and so and osv):"),
    ('MI-06', I, "if (pk.get('ref'), pk.get('version'), pk.get('hash')) != (pin['id'], pin['version'], pin['hash']) or", "if (pk.get('ref'), pk.get('version')) != (pin['id'], pin['version']) or"),
    ('MI-07', I, "if fp.get('hash') != ob.get('schema_fingerprint') or ob.get('schema_fingerprint') not in integ['fingerprints']:", "if False:"),
    ('MI-08', I, "if osv.get('ref') != ob.get('observation_id') or so.get('ref')", "if False and so.get('ref')"),
    ('MI-09', I, "if not isinstance(mv, dict) or {k: mv.get(k) for k in ('id', 'version', 'hash')} != batch.expect['manifest_ref']:", "if not isinstance(mv, dict):"),
    ('MI-10', I, "if ob.get('ordering_state') != 'IN_ORDER':", "if False:"),
    ('MI-11', I, "    if missing:\n", "    if False:\n"),
    ('MI-12', I, "if any(not isinstance(attrs.get(n), str) for n in names if n in attrs):", "if False:"),
    ('MI-13', I, "if _sha(rec) != ob.get('payload_hash'):", "if False:"),
    ('MI-14', I, "if (ob.get('source_object') or {}).get('object_id') != sid:", "if False:"),
    # intake.py: batch checks
    ('MI-15', I, "if r.get('not_allowed'):", "if False:"),
    ('MI-16', I, "if r.get('failed'):", "if False:"),
    ('MI-17', I, "if r.get('invalid'):", "if False:"),
    ('MI-18', I, "if r.get('ambiguous'):", "if False:"),
    ('MI-19', I, "if not r.get('failed') and not r.get('not_allowed') and r.get('complete') is not True:", "if False:"),      # M8.1: re-anchored on rev14's completeness rule
    ('MI-20', I, "if r.get('delivered') != len(batch.deliveries):", "if False:"),
    ('MI-21', I, "    for e in batch.errors:\n        if e.get('kind') == NOTICE and batch.mode == 'events':", "    for e in []:\n        if e.get('kind') == NOTICE and batch.mode == 'events':"),      # M8.1: re-anchored
    ('MI-22', I, "        if s.get('state') != 'ACTIVE':", "        if False:"),
    ('MI-23', I, "if now is None or now['state'] != 'ACTIVE':", "if now is None:"),
    ('MI-24', I, "elif now['manifest_ref'] != batch.expect['manifest_ref']:", "elif False:"),
    ('MI-25', I, "    bad += list(batch.refusals)\n", "\n"),
    ('MI-26', I, "            elif st in PENDING_STATES:\n                outstanding[eid] = st", "            elif False:\n                outstanding[eid] = st"),
    ('MI-27', I, "            if st == 'IN_ORDER':\n                outstanding.pop(eid, None)", "            if False:\n                outstanding.pop(eid, None)"),
    ('MI-28', I, "    if bad:\n        return _blocked(bnd, batch, bad, outstanding, now)", "    if False:\n        return _blocked(bnd, batch, bad, outstanding, now)"),
    ('MI-29', I, "            clean, claims = tenancy.screen_payload(ctx, r.raw, scoped._audit)", "            clean, claims = r.raw, []"),
    ('MI-30', I, "    if c.get('rejected'):", "    if False:"),
    ('MI-31', I, "    if c.get('stale'):", "    if False:"),
    ('MI-32', I, "    if inv:\n", "    if False:\n"),
    ('MI-33', I, "    prior = scoped.get('ingest_receipt', rkey)", "    prior = None"),
    ('MI-34', I, "'translation_pack_hash': pk['hash'],", ""),
    ('MI-35', I, "        _write(bnd, batch, ops, 'applied' if not reasons else 'applied_with_reasons', reasons, outstanding, now, rkey)",
     "        _write(bnd, batch, ops, 'applied', [], outstanding, now, rkey)"),
    ('MI-36', I, "    if len(nonblank) != len(parse.rows):", "    if False:"),
    ('MI-37', I, "        decision, detail = pipeline.decide(existing, ch, rev)", "        decision, detail = 'new', ''"),
    # M8-R1 (finding M8-F7): an empty source is not current data
    ('MI-38', I, "            if r.get('empty') or read_nothing:", "            if False:"),
    ('MI-39', I, "            if r.get('empty') or read_nothing:", "            if read_nothing:"),
    ('MI-40', I, "            if r.get('empty') or read_nothing:", "            if r.get('empty'):"),
    ('MI-41', I, "            read_nothing = not batch.deliveries and not r.get('invalid') and not r.get('ambiguous') and", "            read_nothing = not batch.deliveries and"),
    ('MI-42', I, "not r.get('failed') and not r.get('not_allowed') and \\\n", "\\\n"),      # M8.1: re-anchored (the line now continues)
    # APG-M8.1 (AUIF rev14): composite identities, the rev14 sync report, the event notices
    ('MI-43', I, ".replace('|', '\\\\|') for v in vals)", " for v in vals)"),
    ('MI-44', C, "            ident.setdefault(e, nk[0] if len(nk) == 1 else list(nk))", "            ident.setdefault(e, nk[0])"),
    ('MI-45', I, "for k, code in (('refused', 'RECORD_REFUSED'), ('conflict', 'CANONICAL_CONFLICT'), ('module_failed', 'ADAPTER_ERROR')):", "for k, code in (('conflict', 'CANONICAL_CONFLICT'), ('module_failed', 'ADAPTER_ERROR')):"),
    ('MI-46', I, "        if e.get('kind') == NOTICE and batch.mode == 'events':\n            continue", "        if e.get('kind') == NOTICE and batch.mode == 'events':\n            pass"),
    ('MI-47', I, "        mismatch = notice_problems(batch, report or [])", "        mismatch = []"),
    ('MI-48', I, "                outstanding[str(e.get('event_id'))] = 'NOT_APPLIED'", "                pass"),
    ('MI-49', I, "r.get('complete') is not True:", "r.get('complete') is False:"),
    ('MI-50', I, "                not r.get('refused') and not r.get('conflict')", "                not r.get('conflict')"),
    ('MI-51', I, "        if st in ('QUEUED_AWAITING_PREDECESSOR', 'DEFERRED', 'RECONCILIATION_PENDING') and told.get(eid) != st:", "        if False:"),
    ('MI-52', I, "        if got.get(eid) != st:\n            out.append(('EVENT_NOTICE_MISMATCH'", "        if False:\n            out.append(('EVENT_NOTICE_MISMATCH'"),
    # module.py
    ('MM-01', M, "            if t not in self.bindings:\n                self.unbound_refusals", "            if False:\n                self.unbound_refusals"),
    ('MM-02', M, "                b.refusals.append(('LINEAGE_INCOMPLETE', 'canonical object %s arrived without its observation'", "                (('LINEAGE_INCOMPLETE', 'canonical object %s arrived without its observation'"),
    ('MM-03', M, "                    if b is not None:\n                        b.refusals.append(('ADAPTER_ERROR',", "                    if False:\n                        b.refusals.append(('ADAPTER_ERROR',"),
    ('MM-04', M, "            if b is not None and iid == b.integration_id:\n                b.errors.append(dict(error))\n                return",
     "            if b is not None and iid == b.integration_id:\n                return"),
    ('MM-05', M, "            bnd.record_state(state)", "            pass"),
    ('MM-06', M, "                return self._alert(ctx.tenant_id, None, 'UNSOLICITED_DELIVERY', 'canonical object %s arrived with no import open'",
     "                return (ctx.tenant_id, None, 'UNSOLICITED_DELIVERY', 'canonical object %s arrived with no import open'"),
    # gate.py
    ('MG-01', G, "        elif st['state'] != 'ACTIVE':", "        elif False:"),
    ('MG-02', G, "            reasons.append(_r('NOT_IMPORTED', scope, 'no import of this record type has been applied'))\n            continue",
     "            continue"),
    ('MG-03', G, "        if p['status'] not in ('applied', 'applied_with_reasons') or p['reasons']:", "        if p['status'] not in ('applied', 'applied_with_reasons'):"),
    ('MG-04', G, "        if st is not None and p['manifest_ref'] != st['manifest_ref']:", "        if False:"),
    ('MG-05', G, "        if any(i not in seq for i in scope_ids) or a['seq'] > floor:", "        if False:"),
    ('MG-06', G, "    if module is not None and getattr(module, 'handler_errors', None):", "    if False:"),
    ('MG-07', G, "        for code, detail in record_reasons(r):", "        for code, detail in []:"),
    ('MG-08', G, "        if st is None:\n            reasons.append(_r('NO_STATE'", "        if False:\n            reasons.append(_r('NO_STATE'"),
    # assess.py
    ('MA-01', A, "    if g['status'] != G.CAN:\n        return _refused", "    if False:\n        return _refused"),
    ('MA-02', A, "    if g2 != g:", "    if False:"),
    # pack.py (the reference form; the contract form from APG-M8.1)
    ('MP-01', P, "    if want_prefix is None or not ref.startswith(want_prefix) or '.' in ref[len(want_prefix):] or not ref[len(want_prefix):]:", "    if want_prefix is None:"),
    ('MP-02', P, "    return '%s.%s' % (concept, attr)", "    return '%s.%s' % (concept[len(DEF.PREFIX):], attr)"),      # M8.1: the contract form; the mutant restores the ended deviation form
    ('MP-03', P, "        elif m['kind'] == 'ENTITY' and not m['canonical_ref'].startswith(DEF.PREFIX):", "        elif False:"),
    # client.py
    ('MC-01', C, "        if bad:\n            raise ValueError('pack %s is not in the contract reference form", "        if False:\n            raise ValueError('pack %s is not in the contract reference form"),
    ('MC-02', C, "        page = max(1, min(200, (MAX_KEYS - 3) // max(1, ncols)))", "        page = 200"),
    ('MC-03', C, "        if raised is not None:\n            b.refusals.append(('AUIF_RAISED', 'AUIF raised %s: %s' % (type(raised).__name__, str(raised)[:120])))\n            rep = None",
     "        if raised is not None:\n            rep = None"),
    ('MC-04', C, "        if scoped.ctx.tenant_id != tenant:", "        if False:"),
    # dependency.py
    ('MD-01', D, "    if got != ZIP_SHA256:", "    if False:"),
    ('MD-02', D, "    if r2.returncode != 0 or core != CORE_TREE_SHA256:", "    if r2.returncode != 0:"),
    ('MD-03', D, "    if r.returncode != 0 or not man.get('ok') or man.get('tree_sha256') != TREE_SHA256 or man.get('files_checked') != FILES:", "    if r.returncode != 0:"),
    # lineage.py (the checker the no-laundering test relies on)
    ('ML-01', L, "        if prov.get(f) in (None, '', [], {}):", "        if False:"),
    ('ML-02', L, "    return ['%s: input kind %s is UNTRACED' % (where, kind)], 'untraced'", "    return [], 'untraced'"),
    ('ML-03', L, "    if not isinstance(prov, dict) or prov.get('path') != 'auif':", "    if not isinstance(prov, dict):"),
    ('ML-04', L, "    out += ['%s: %s' % (where, p) for p in pr]", "    out += []"),
]


def copy_tree(dest):
    for d in ('apg', 'apg_auif', 'third_party'):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(dest, d), ignore=shutil.ignore_patterns('__pycache__'))


def apply(dest, f, old, new):
    p = os.path.join(dest, f)
    s = open(p, encoding='utf-8').read()
    if s.count(old) != 1:
        raise SystemExit('mutant text occurs %d times in %s: %r' % (s.count(old), f, old[:80]))
    open(p, 'w', encoding='utf-8').write(s.replace(old, new))


def run_tier(dest, mods, env, timeout):
    try:
        r = subprocess.run([sys.executable, '-B', '-W', 'ignore', '-m', 'unittest', '-f'] + ['tests_m8.' + m for m in mods], cwd=ROOT,
                           env=dict(env, APG_ROOT=dest), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', ''
    if r.returncode == 0:
        return 'PASS', ''
    lines = [l for l in r.stderr.splitlines() if l.startswith(('FAIL:', 'ERROR:'))]
    return 'FAIL', (lines[0] if lines else r.stderr.strip().splitlines()[-1:])


def run_one(mutant, env, timeout):
    mid, f, old, new = mutant
    dest = tempfile.mkdtemp(prefix='apg_m8_mut_')
    t = time.time()
    try:
        copy_tree(dest)
        if f:
            apply(dest, f, old, new)
        r1, why = run_tier(dest, TIER1, env, timeout)
        if r1 == 'FAIL':
            return mid, 'KILLED', 'tier 1: ' + str(why)[:150], time.time() - t
        if r1 == 'TIMEOUT':
            return mid, 'TIMEOUT', 'tier 1 ran out of time (neither a kill nor a survival)', time.time() - t
        r2, why = run_tier(dest, TIER2, env, timeout)
        if r2 == 'FAIL':
            return mid, 'KILLED', 'tier 2: ' + str(why)[:150], time.time() - t
        if r2 == 'TIMEOUT':
            return mid, 'TIMEOUT', 'tier 2 ran out of time (neither a kill nor a survival)', time.time() - t
        return mid, ('EQUIVALENT' if mid in EQUIVALENT else 'SURVIVED'), EQUIVALENT.get(mid, '')[:150], time.time() - t
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def main():
    a = sys.argv[1:]
    if '--list' in a:
        for m in MUTANTS:
            print('%-6s %-24s %r -> %r' % (m[0], m[1], m[2][:70], m[3][:50]))
        print('%d mutants' % len(MUTANTS))
        return 0
    sel = MUTANTS
    if '--only' in a:
        ids = set(a[a.index('--only') + 1].split(','))
        sel = [m for m in MUTANTS if m[0] in ids]
    if '--batch' in a:
        k, n = map(int, a[a.index('--batch') + 1].split('/'))
        sel = [m for i, m in enumerate(sel) if i % n == k - 1]
    jobs = int(a[a.index('--jobs') + 1]) if '--jobs' in a else 2
    timeout = int(a[a.index('--timeout') + 1]) if '--timeout' in a else 600
    dep = dependency.ensure()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **{dependency.ENV: dep['root']})
    print('AUIF verified: zip %s core %s' % (dep['zip_sha256'][:16], dep['core_tree_sha256'][:16]), flush=True)
    ctl = run_one(('CONTROL', None, None, None), env, timeout)
    print('CONTROL (unmutated copy): %s %.0fs' % ('passes' if ctl[1] == 'SURVIVED' else ctl[1] + ' ' + ctl[2], ctl[3]), flush=True)
    if ctl[1] != 'SURVIVED':
        return 2
    res = []
    with ThreadPoolExecutor(jobs) as ex:
        for mid, st, why, secs in ex.map(lambda m: run_one(m, env, timeout), sel):
            res.append((mid, st))
            print('%-6s %-8s %5.0fs %s' % (mid, st, secs, why), flush=True)
    after = dependency.reverify(dep['root'])
    cnt = {k: sum(1 for _, s in res if s == k) for k in ('KILLED', 'SURVIVED', 'TIMEOUT', 'EQUIVALENT')}
    print('mutants %d: killed %d, documented equivalent %d, survived %d, timeout %d | AUIF after: %s' % (len(res), cnt['KILLED'], cnt['EQUIVALENT'], cnt['SURVIVED'], cnt['TIMEOUT'],
                                                                                 'unchanged' if after['core_tree_sha256'] == dependency.CORE_TREE_SHA256 else 'CHANGED'))
    return 0 if cnt['SURVIVED'] == 0 and cnt['TIMEOUT'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
