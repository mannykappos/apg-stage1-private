#!/usr/bin/env python3
"""Package-level sabotage for MIE-1: one corruption per entry of the MIE-1 sabotage catalogue (spec/MIE1_SPEC_v0.3/MIE1_SABOTAGE_CATALOGUE.csv, SB-01 to SB-60).  Each corruption
is applied to a COPY of this package and the named check must then FAIL; a corruption that the check does not notice is a gap.  The check is a test file (run with
tools/run_m2_tests.py), the static checks (tools/mie_static.py) or a step of tools/run_regression_mie1.py.
Usage: python3 -I tools/sabotage_mie1.py [--list] [--only SB-nn]   (from the package root; works in temporary folders; changes nothing here)"""
import csv, os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
E, S, O, P, T, C, V = ('mie/core/engine.py', 'mie/core/signals.py', 'mie/core/observations.py', 'mie/core/pack.py', 'mie/core/timing.py', 'mie/core/canon.py',
                       'mie/core/values.py')
PK, OB, SG, TM, RP, TN, AU, AD, ST, FL, CO, BD = ('test_mie_core_pack.py', 'test_mie_core_observations.py', 'test_mie_core_signals.py', 'test_mie_core_timing.py',
                                                 'test_mie_core_replay.py', 'test_mie_core_tenancy.py', 'test_mie_core_audit.py', 'test_mie_core_adversarial.py',
                                                 'STATIC', 'test_mie_flow.py', 'test_mie_construction.py', 'test_mie_core_boundaries.py')

# (catalogue id, what is done, file, old text, new text, the check that must fail)
CASES = [
    ('SB-01', 'a default freshness limit is used when none is supplied', S, "        return v, 'request'\n    return None, None", "        return v, 'request'\n    return 45, 'default'", SG),
    ('SB-02', 'a float in a pack is accepted', P, "    if floats:\n        _bad(", "    if False:\n        _bad(", PK),
    ('SB-03', 'an UNKNOWN licence is treated as LICENSED', O, "    if lic['status'] != 'LICENSED':", "    if lic['status'] not in ('LICENSED', 'UNKNOWN'):", OB),
    ('SB-04', 'an observation dated after the evaluation date is used', S, "        if o['as_of'] > evaluation_date:\n", "        if False:\n", SG),
    ('SB-05', 'a conflict is resolved silently (no conflict is ever found)', S, "        if len(vals) > 1:\n            out[k] = sorted(ids)", "        if False:\n            out[k] = sorted(ids)", SG),
    ('SB-06', 'zero is substituted for a missing need-by date', T, "        if days is None:\n            raise Indeterminate('CONSTRAINT_MISSING')", "        if days is None:\n            days = 0", TM),
    ('SB-07', 'get_result drops the tenant check and finds a record of any tenant', E, "            body = self.results.get(tenant, result_id)\n            if body is None:\n                raise MieError('NOT_FOUND')\n            return _Done(body",
     "            body = self.results.get(tenant, result_id) or next((v for (t, k), v in getattr(self.results, 'd', {}).items() if k == result_id), None)\n            if body is None:\n                raise MieError('NOT_FOUND')\n            return _Done(body", TN),
    ('SB-08', 'the pack hash is not verified', E, "        if e['pin']['pack_hash'] != pin['pack_hash']:\n            raise MieError('PACK_HASH_MISMATCH')", "        if False:\n            raise MieError('PACK_HASH_MISMATCH')", PK),
    ('SB-09', 'a pack key that overrides a core invariant is not recognised', P, "        if k is not None and k in OVERRIDE_KEYS:", "        if False:", PK),
    ('SB-10', 'a SELL intention is evaluated under a BUY-only pack', E, "            if intention not in doc['allowed_intentions']:", "            if False:", CO),
    ('SB-11', 'the wall clock is read inside assessment', T, "def build(doc, pin, request, observations, ev, approval_ref):\n", "def build(doc, pin, request, observations, ev, approval_ref):\n    import datetime\n    _ = datetime.date.today()\n", ST),
    ('SB-12', 'a signal carries a predicted level', S, "                  'crosses_zero': (si < 0 < ei) or (ei < 0 < si)}", "                  'crosses_zero': (si < 0 < ei) or (ei < 0 < si), 'predicted_level': e_val}", ST),
    ('SB-13', 'stale required evidence counts as current', S, "    if V.days(latest, evaluation_date) > limit:\n        return 'STALE_EVIDENCE', ids", "    if False:\n        return 'STALE_EVIDENCE', ids", SG),
    ('SB-14', 'an audit-sink failure is ignored and the result returned', E, "        except AuditFailure:\n            raise MieError('AUDIT_UNAVAILABLE')\n        if done.commit:", "        except AuditFailure:\n            pass\n        if done.commit:", AU),
    ('SB-15', 'replay reads the latest data instead of the stored evidence', E, "            obs = {}\n            for oid in stored['evidence_set']:", "            obs = self.obs.for_subjects(tenant, [stored['request']['subject_id']])\n            for oid in []:", RP),
    ('SB-16', 'a domain term is added to a core file', 'mie/core/vocab.py', "CORE_VERSION = ", "FIELD_NOTE = 'construction'\nCORE_VERSION = ", ST),
    ('SB-17', 'a built-in bias towards rising levels', S, "        direction = 'UP' if r >= T else", "        direction = 'UP' if r >= T - Fraction(1, 100) else", SG),
    ('SB-18', 'a scenario is generated from history', T, "for s in request['scenarios']]", "for s in request['scenarios'] + ([{'scenario_id': 'GEN', 'label': 'FROM-HISTORY'}] if ev['signals'] else [])]", TM),
    ('SB-19', 'decision rules are evaluated in an order other than the pack\'s', T, "    for i, rule in enumerate(table):", "    for i, rule in sorted(enumerate(table), key=lambda x: x[1]['rule_id'], reverse=True):", TM),
    ('SB-20', 'another tenant\'s record gives a different error from a missing one', E, "            body = self.results.get(tenant, result_id)\n            if body is None:\n                raise MieError('NOT_FOUND')\n            return _Done(body",
     "            body = self.results.get(tenant, result_id)\n            if body is None:\n                raise MieError('NOT_FOUND' if not any(k == result_id for (t, k) in getattr(self.results, 'd', {})) else 'REQUEST_MALFORMED')\n            return _Done(body", TN),
    ('SB-21', 'a published pack is replaced in place', E, "                    raise MieError('PACK_VERSION_CONFLICT'",
     "                    self.registry.packs[(pin['pack_id'], pin['pack_version'])] = {'pin': pin, 'bytes': canon.dumps(doc), 'publisher': tenant}\n                    return _Done({'pin': pin, 'registered': 'now'}, {'pack': pin})\n                    raise MieError('PACK_VERSION_CONFLICT'", PK),
    ('SB-22', 'identifiers are matched without regard to case', P, "    if sid in subjects:\n        return sid\n", "    if sid in subjects:\n        return sid\n    for s in subjects:\n        if s.casefold() == sid.casefold():\n            return s\n", PK),
    ('SB-23', 'the canonical form keeps the key order it was given', C, "sorted(v, key=lambda k: k.encode('utf-8'))", "list(v)", PK),
    ('SB-24', 'an APG module is imported into the core', C, "import hashlib, json, unicodedata", "import hashlib, json, unicodedata\nimport apg", ST),
    ('SB-25', 'asking, offer and index values are merged into one series', S, "    return (o['subject_id'], o['market'], o['unit'], o['observation_class'], o['value_basis'])", "    return (o['subject_id'], o['market'], o['unit'], o['observation_class'], 'ANY')", TM),
    ('SB-26', 'an observation outside its licence window is used', S, " or not (L['valid_from'] <= evaluation_date <= L['valid_to']):", ":", OB),
    ('SB-27', 'an APG finding module imports the core', 'apg/det/findings.py', "KIND = 'finding'", "import mie\nKIND = 'finding'", ST),
    ('SB-28', 'a pack is activated without verifying the approval reference', E, "            if not self.approvals.verify(tenant, approval_ref, e['pin'], doc):", "            if False:", PK),
    ('SB-29', 'a result is returned after a store failure', E, "                self._try_append(tenant, op, 'FAILED', 'STORE_UNAVAILABLE', refs, must=False)\n                raise MieError('STORE_UNAVAILABLE')\n        return",
     "                self._try_append(tenant, op, 'FAILED', 'STORE_UNAVAILABLE', refs, must=False)\n        return", AU),
    ('SB-30', 'free text in an assumption changes the outcome', T, "        return {'outcome': rule['outcome'],", "        return {'outcome': 'WAIT' if 'WAIT' in (rule.get('assumption') or '') and 'WAIT' in Y.OUTCOMES[intention] else rule['outcome'],", AD),
    ('SB-31', 'a scenario value is merged into the current-reference group', T, "    evidence['scenarios'] = [", "    evidence['current_reference'] = evidence['current_reference'] + [dict(s) for s in request['scenarios']]\n    evidence['scenarios'] = [", TM),
    ('SB-32', 'one tenant\'s activation (and so its licences) is used for another', E, "        acts = self.registry.activations(tenant, pin)\n        if not acts:\n            raise MieError('PACK_NOT_ACTIVE')",
     "        acts = self.registry.activations(tenant, pin) or [a for v in getattr(self.registry, 'acts', {}).values() for a in v]\n        if not acts:\n            raise MieError('PACK_NOT_ACTIVE')", TN),
    ('SB-33', 'list_audit appends its own access event before it reads', E, "            cutoff = self.audit_query.last_seq(tenant)", "            self.audit.append(tenant, {'operation': 'list_audit', 'outcome': 'OK', 'code': None, 'correlation_id': None, 'refs': {}})\n            cutoff = self.audit_query.last_seq(tenant)", AU),
    ('SB-34', 'list_audit reads every tenant\'s events', E, "            events = self.audit_query.read(tenant, from_seq, cutoff, limit)",
     "            events = [x for t in sorted(getattr(self.audit_query, 'chains', {})) for x in self.audit_query.read(t, from_seq, 10 ** 9, limit)]", AU),
    ('SB-35', 'list_audit answers when the audit sink is down', E, "        except AuditFailure:\n            raise MieError('AUDIT_UNAVAILABLE')\n        except Exception:\n            self._try_append(tenant, 'list_audit'",
     "        except AuditFailure:\n            return {'events': [], 'cutoff_seq': None, 'chain': None}\n        except Exception:\n            self._try_append(tenant, 'list_audit'", AU),
    ('SB-36', 'state is committed before the audit event is appended', E, "        refs.update(done.refs)\n        try:", "        refs.update(done.refs)\n        if done.commit:\n            done.commit()\n            done.commit = lambda: None\n        try:", AU),
    ('SB-37', 'a refusal for an unverifiable context is written into a guessed tenant\'s chain', E, "        except ContextInvalid:\n            raise MieError('TENANT_CONTEXT_INVALID')",
     "        except ContextInvalid:\n            self._try_append('T-A', 'context', 'REFUSED', 'TENANT_CONTEXT_INVALID', {}, must=False)\n            raise MieError('TENANT_CONTEXT_INVALID')", TN),
    ('SB-38', 'a read operation skips the audit append', E, "            self._append(tenant, op, 'ACCEPTED' if done.commit else 'OK', None, refs)", "            if done.commit or op != 'get_signals':\n                self._append(tenant, op, 'ACCEPTED' if done.commit else 'OK', None, refs)", AU),
    ('SB-39', 'the assumption label is applied only to WAIT and HOLD', T, "    labelled = rule is not None and rule['basis_class'] == 'OWNER_ASSUMPTION'", "    labelled = rule is not None and rule['basis_class'] == 'OWNER_ASSUMPTION' and decision['outcome'] in ('WAIT', 'HOLD')", TM),
    ('SB-40', 'an unlabelled market-signal rule is accepted for ACT_NOW', P, "    for r in table[first:]:\n        if not owner_labelled(r):", "    for r in table[first:]:\n        if not owner_labelled(r) and r['outcome'] != 'ACT_NOW':", PK),
    ('SB-41', 'an OBSERVED_EVIDENCE_ONLY rule is allowed after a signal-influenced rule', P, "    for r in table[first:]:", "    for r in [x for x in table[first:] if signal_influenced(x)]:", PK),
    ('SB-42', 'the relative ratio uses the signed start as denominator', S, "        r = Fraction(d, abs(si))", "        r = Fraction(d, si)", SG),
    ('SB-43', 'a zero start gives ratio zero and UNCHANGED instead of ZERO_BASE', S, "        if si == 0:\n            return _na(subject, cfg, typ, 'ZERO_BASE', **common)",
     "        if si == 0:\n            return _base({'status': 'ASSESSED', 'reason': None, **common, 'difference': V.decimal_out(d, exp), 'ratio': {'num': 0, 'den': 1}, 'direction': 'UNCHANGED', 'crosses_zero': False}, subject, cfg, typ)", SG),
    ('SB-44', 'a movement across zero is not flagged', S, "'crosses_zero': (si < 0 < ei) or (ei < 0 < si)", "'crosses_zero': False", SG),
    ('SB-45', 'a value outside the unit\'s domain is accepted', O, "        if not V.in_domain(item['value'], dom):", "        if False:", OB),
    ('SB-46', 'the core calls an observation source during assessment', E, "            obs = self._evidence(tenant, doc, sid, lim)\n            body, rid",
     "            obs = self._evidence(tenant, doc, sid, lim)\n            if getattr(self, 'source', None) is not None:\n                self.source.fetch(tenant, sid, evaluation_date)\n            body, rid", ST),
    ('SB-47', 'submit_observations skips validation for adapter-validated items', O, "    extra = sorted(set(item) - set(REQUIRED) - set(OPTIONAL))",
     "    if isinstance(item.get('adapter_notes'), dict) and item['adapter_notes'].get('pre_validated') is True:\n        obs = {k: item[k] for k in STORED if item.get(k) is not None}\n        return {'status': 'ACCEPTED', 'observation_id': observation_id(obs)}, obs\n    extra = sorted(set(item) - set(REQUIRED) - set(OPTIONAL))", OB),
    ('SB-48', 'a licence status asserted by the feed grants use', O, "    if lic['status'] != 'LICENSED':", "    if lic['status'] != 'LICENSED' and item.get('feed_licence_status') != 'LICENSED':", FL),
    ('SB-49', 'a blocker the product owner must decide is recorded as decided', 'programme/CARRIED_FORWARD_REGISTER.csv', 'the explicit decision and its review are outstanding', 'decided by the builder', 'R05'),
    ('SB-50', 'downstream NOT_ASSESSED rules are exempt from the owner label', P, "    for r in table[first:]:\n        if not owner_labelled(r):", "    for r in table[first:]:\n        if not owner_labelled(r) and r['outcome'] != 'NOT_ASSESSED':", PK),
    ('SB-51', 'a downstream rule whose own outcome is NOT_ASSESSED is exempt', P, "    for r in table[first:]:\n        if not owner_labelled(r):", "    for r in table[first:]:\n        if not owner_labelled(r) and not (r['outcome'] == 'NOT_ASSESSED' and not signal_influenced(r)):", PK),
    ('SB-52', 'the basis class is checked but not the owner reference or the assumption', P, "    return rule['basis_class'] == 'OWNER_ASSUMPTION' and isinstance(rule.get('owner_ref'), str)", "    return rule['basis_class'] == 'OWNER_ASSUMPTION' or isinstance(rule.get('owner_ref'), str)", PK),
    ('SB-53', 'register_pack stores a pack that validate_pack refuses', E, "            doc, pin = P.validate(pack_bytes, lim)\n            e = self.registry.get(",
     "            doc = canon.loads(pack_bytes)\n            pin = {'pack_id': doc['pack_id'], 'pack_version': doc['pack_version'], 'pack_hash': canon.digest(doc)}\n            e = self.registry.get(", PK),
    ('SB-54', 'a downstream rule is NONE when the earlier signal-influenced rule is NOT_ASSESSED', T, "    first = P.first_influenced(table)", "    first = next((i for i, r in enumerate(table) if P.signal_influenced(r) and r['outcome'] != 'NOT_ASSESSED'), None)", TM),
    ('SB-55', 'the valid owner-labelled sequence after a signal-influenced NOT_ASSESSED rule is refused', P, "    first = first_influenced(table)\n    if first is None:\n        return",
     "    first = first_influenced(table)\n    if first is None:\n        return\n    if table[first]['outcome'] == 'NOT_ASSESSED' and len(table) > first + 1:\n        _bad('PACK_RULE_POLICY_VIOLATION', 'over-refusal')", PK),
    ('SB-56', 'an unlabelled DIRECT or PRECEDENCE result is emitted instead of failing closed', T, "        if cls != 'NONE' and not P.owner_labelled(rule):", "        if False:", TM),
    ('SB-57', 'NO_RULE_MATCHED is given the PRECEDENCE class', T, "    return {'outcome': 'NOT_ASSESSED', 'reason': 'NO_RULE_MATCHED', 'rule': None, 'influence_class': 'NONE',",
     "    return {'outcome': 'NOT_ASSESSED', 'reason': 'NO_RULE_MATCHED', 'rule': None, 'influence_class': 'PRECEDENCE' if first is not None else 'NONE',", TM),
    ('SB-58', 'a negated SIGNAL_NOT_ASSESSED predicate is not treated as signal-influenced', P, "    return p['p'] in ('SIGNAL_PRESENT', 'SIGNAL_NOT_ASSESSED') and p['type'] in Y.MARKET_SIGNALS",
     "    return p['p'] in ('SIGNAL_PRESENT', 'SIGNAL_NOT_ASSESSED') and p['type'] in Y.MARKET_SIGNALS and not (p['p'] == 'SIGNAL_NOT_ASSESSED' and p['negate'])", PK),
    ('SB-59', 'rule order is validated as sorted, not as submitted', P, "    for i, r in enumerate(table or []):", "    for i, r in enumerate(sorted(table or [], key=lambda r: r['rule_id'])):", PK),
    ('SB-60', 'an implementation blocker is marked resolved', 'programme/CARRIED_FORWARD_REGISTER.csv', 'Open - blocking release, not development', 'Resolved', 'R05'),
]
SKIP_TOP = {'logs'}


def copy(tmp):
    work = os.path.join(tmp, 'pkg')
    shutil.copytree(ROOT, work, ignore=lambda d, names: [n for n in names if n == '__pycache__' or (os.path.abspath(d) == ROOT and n in SKIP_TOP)])
    return work


def check(work, target, env):
    if target == 'STATIC':
        r = subprocess.run([sys.executable, '-I', 'tools/mie_static.py'], cwd=work, env=env, capture_output=True, text=True, timeout=600)
        return r.returncode != 0 and 'failed 0' not in r.stdout, (r.stdout.strip().splitlines() or [''])[-1]
    if target.startswith('R'):
        r = subprocess.run([sys.executable, '-I', 'tools/run_regression_mie1.py', '--step', target], cwd=work, env=env, capture_output=True, text=True, timeout=1800)
        return r.returncode != 0 and ('FAIL ' + target) in r.stdout, (r.stdout.strip().splitlines() or [''])[-1]
    r = subprocess.run([sys.executable, '-I', 'tools/run_m2_tests.py', '-q', target], cwd=work, env=env, capture_output=True, text=True, timeout=1800)
    tail = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith('tests ')]
    return r.returncode != 0 and bool(tail) and 'failures 0  errors 0' not in tail[-1], (tail or ['no test summary'])[-1]


def main():
    ids = [r['mutant_id'] for r in csv.DictReader(open(os.path.join(ROOT, 'spec', 'MIE1_SPEC_v0.3', 'MIE1_SABOTAGE_CATALOGUE.csv'), encoding='utf-8', newline=''))]
    if [c[0] for c in CASES] != ids:
        print('ERROR the cases do not match the catalogue one to one, in order')
        return 2
    if '--list' in sys.argv:
        for c in CASES:
            print(c[0], c[1], '->', c[5])
        return 0
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    bad = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for cid, what, path, old, new, target in CASES:
        if only and cid not in only.split(','):
            continue
        with tempfile.TemporaryDirectory(prefix='mie1_sab_') as tmp:
            work = copy(tmp)
            p = os.path.join(work, path)
            text = open(p, encoding='utf-8').read()
            if text.count(old) != 1:
                print('ERROR', cid, 'the text to corrupt is not in %s exactly once (%d)' % (path, text.count(old)))
                return 2
            open(p, 'w', encoding='utf-8').write(text.replace(old, new, 1))
            caught, detail = check(work, target, env)
            print('%s %s %s -> %s  [%s]' % ('CAUGHT' if caught else 'MISSED', cid, what, target, detail), flush=True)
            if not caught:
                bad.append(cid)
    n = len([c for c in CASES if not only or c[0] in only.split(',')])
    print('sabotage cases %d  missed %d%s' % (n, len(bad), ('  MISSED: %r' % bad) if bad else ''))
    print('EVERY SABOTAGE CASE IS CAUGHT' if not bad else 'SABOTAGE GAPS')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
