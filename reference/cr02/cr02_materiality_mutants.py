#!/usr/bin/env python3
"""CR-02 Stage 1 -- scoped mutation run over the materiality REFERENCE MODEL.  Each mutant is a one-place textual change to a
temporary COPY of the model; the full test suite is run against it; a mutant is KILLED when the suite fails (non-zero exit).
Usage: python3 -I cr02_materiality_mutants.py [--list]   (CR02_MUT_JOBS=n parallel jobs, default 2)      Exit 0 only if every mutant is killed or is a documented equivalent."""
import os, subprocess, sys, tempfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, 'cr02_materiality_model.py'); TESTS = os.path.join(HERE, 'cr02_materiality_tests.py')
src = open(MODEL, encoding='utf-8').read()

# (id, old, new, count)   count = number of occurrences replaced (None = all, but at least 1)
MUT = [
 ('MU01-abs-ge-to-gt',        "if 'abs_cents' in m and amount_abs >= m['abs_cents']:", "if 'abs_cents' in m and amount_abs > m['abs_cents']:", 1),
 ('MU02-rel-ge-to-gt',        "elif amount_abs * 10000 >= m['rel_bps'] * base:", "elif amount_abs * 10000 > m['rel_bps'] * base:", 1),
 ('MU03-days-ge-to-gt',       "elif abs(d) >= m['delay_days']:", "elif abs(d) > m['delay_days']:", 1),
 ('MU04-days-no-abs',         "elif abs(d) >= m['delay_days']:", "elif d >= m['delay_days']:", 1),
 ('MU05-amount-no-abs',       "_amount_tests(abs(a), record.get('bases'), m, reasons, 'M-ABS', 'M-REL')", "_amount_tests(a, record.get('bases'), m, reasons, 'M-ABS', 'M-REL')", 1),
 ('MU06-rel-wrong-scale',     "elif amount_abs * 10000 >= m['rel_bps'] * base:", "elif amount_abs * 1000 >= m['rel_bps'] * base:", 1),
 ('MU07-base-zero-allowed',   "if not _is_int(base) or base < 1:", "if not _is_int(base) or base < 0:", 1),
 ('MU08-int-accepts-bool',    "return isinstance(x, int) and not isinstance(x, bool)", "return isinstance(x, int)", 1),
 ('MU09-int-accepts-float',   "return isinstance(x, int) and not isinstance(x, bool)", "return isinstance(x, (int, float)) and not isinstance(x, bool)", 1),
 ('MU10-always-ignored',      "if any(c in policy.get('always_material', []) for c in cats):", "if False and any(c in policy.get('always_material', []) for c in cats):", 1),
 ('MU11-unset-not-material',  "reasons.append('M-THRESHOLD-UNSET'); return out()", "return out()", 1),
 ('MU12-unknown-not-material',"reasons.append('M-UNKNOWN-SUBJECT'); return out()", "return out()", 1),
 ('MU13-amount-missing-ignored', "reasons.append('M-AMOUNT-MISSING')", "pass", 1),
 ('MU14-agg-max-not-sum',     "_amount_tests(sum(amts),", "_amount_tests(max(amts),", 1),
 ('MU15-agg-no-abs',          "amts.append(abs(r['amount_cents']))", "amts.append(r['amount_cents'])", 1),
 ('MU16-agg-unknown-ignored', "reasons.append('M-AGG-UNKNOWN')", "pass", 1),
 ('MU17-agg-flag-ignored',    "if group_records and policy.get('aggregate', True) and", "if group_records and True and", 1),
 ('MU18-agg-subject-unchecked', " or r.get('subject') != subject", "", 1),
 ('MU19-digest-no-policy',    "'policy': policy,", "'policy': None,", 1),
 ('MU20-digest-no-group',     "'group': group}", "'group': None}", 1),
 ('MU21-version-unchecked',   "if not isinstance(v, str) or not v.strip():", "if False:", 1),
 ('MU22-aggregate-type-unchecked', "if not isinstance(policy.get('aggregate', True), bool):", "if False:", 1),
 ('MU23-extra-keys-allowed',  "if set(rule) - allowed:", "if False:", 1),
 ('MU24-pairing-unchecked',   "if ('rel_bps' in rule) != ('rel_base' in rule):", "if False:", 1),
 ('MU25-classify-unset-to-set-tighten', "elif sn == 'ok':\n                loose = True", "elif sn == 'ok':\n                tight = True", 1),
 ('MU26-classify-lower-is-loosen', "if n < o: tight = True", "if n < o: loose = True", 1),
 ('MU27-proposer-may-approve',"or who == change['proposer']", "", 1),
 ('MU28-ai-approver-counts',  "or k != 'human'", "", 1),
 ('MU29-loosen-needs-one',    "if len(valid) >= 2 and owners:", "if len(valid) >= 1 and owners:", 1),
 ('MU30-loosen-owner-optional', "if len(valid) >= 2 and owners:", "if len(valid) >= 2:", 1),
 ('MU31-same-version-ok',     "if new['version'] == old['version']:", "if False:", 1),
 ('MU32-tighten-any-approver',"return (True, 'C-OK') if owners else (False, 'C-APPROVAL')", "return (True, 'C-OK') if valid else (False, 'C-APPROVAL')", 1),
 ('MU33-mixed-is-tighten',    "if tight and loose: return 'mixed'", "if tight and loose: return 'tighten'", 1),
 ('MU34-always-removal-tightens', "elif n is None: loose = True", "elif n is None: tight = True", 1),
 ('MU35-agg-off-ignored',     "if o is True and n is False: loose = True", "if o is True and n is False: pass", 1),
 ('MU36-nan-allowed-in-json', "allow_nan=False", "allow_nan=True", 1),
 ('MU37-categories-unchecked',"if not isinstance(cats, list) or not all(isinstance(c, str) for c in cats):", "if False:", 1),
 ('MU38-days-missing-ignored',"reasons.append('M-DAYS-MISSING')", "pass", 1),
 ('MU39-rel-base-unchecked',  "or rule['rel_base'] not in BASES", "", 1),
 ('MU40-abs-zero-allowed',    "if not _is_int(rule['abs_cents']) or rule['abs_cents'] < 1:", "if not _is_int(rule['abs_cents']) or rule['abs_cents'] < 0:", 1),
 ('MU41-reasons-not-deduplicated', "'reasons': sorted(set(reasons))", "'reasons': sorted(reasons)", 1),
 ('MU42-no-NM-BELOW-reason',  "reasons.append('NM-BELOW')", "pass", 1),
 ('MU43-aggregate-default-off', "policy.get('aggregate', True)", "policy.get('aggregate', False)", None),
 ('MU44-nan-error-uncaught',  "except (TypeError, ValueError):", "except TypeError:", 1),
 ('MU45-record-type-unchecked', "if dig is None or not isinstance(record, dict):", "if dig is None:", 1),
 ('MU46-base-change-ignored', "tight = loose = True            # a changed basis", "pass                              # a changed basis", 1),
 ('MU47-mat-from-reasons-list', "mat = any(r.startswith('M-') for r in reasons)", "mat = bool(reasons)", 1),
 ('MU48-all-records-any-truthy', "if set(rule) == {'all_records'} and rule['all_records'] is True:", "if set(rule) == {'all_records'} and rule['all_records']:", 1),
 ('MU49-all-records-extra-keys', "if set(rule) == {'all_records'} and rule['all_records'] is True:", "if rule['all_records'] is True:", 1),
 ('MU50-all-records-wrong-reason', "reasons.append('M-ALL-RECORDS'); return out()", "reasons.append('M-THRESHOLD-UNSET'); return out()", 1),
 ('MU51-all-records-not-material', "reasons.append('M-ALL-RECORDS'); return out()", "return out()", 1),
 ('MU52-window-off-by-one',   "abs(cd - rd) <= win", "abs(cd - rd) < win", 1),
 ('MU53-window-one-sided',    "abs(cd - rd) <= win", "cd - rd <= win", 1),
 ('MU54-window-other-side',   "abs(cd - rd) <= win", "rd - cd <= win", 1),
 ('MU55-subject-filter-dropped', "if c.get('subject') != record.get('subject'):\n            continue", "if False:\n            continue", 1),
 ('MU56-self-not-skipped',    "if c.get('id') is not None and c.get('id') == record.get('id'):", "if False:", 1),
 ('MU57-unplaceable-candidate-ignored', "if not _group_ok(c.get('group'), keys) or cd is None:\n            unknown = True; continue", "if not _group_ok(c.get('group'), keys) or cd is None:\n            continue", 1),
 ('MU58-non-dict-candidate-ignored', "if not isinstance(c, dict):\n            unknown = True; continue", "if not isinstance(c, dict):\n            continue", 1),
 ('MU59-keys-any-not-all',    "all(c['group'][k] == record['group'][k] for k in keys)", "any(c['group'][k] == record['group'][k] for k in keys)", 1),
 ('MU60-project-key-not-required', "if 'project' not in k:\n        return False", "if False:\n        return False", 1),
 ('MU61-window-zero-allowed', "return _is_int(w) and w >= 1", "return _is_int(w) and w >= 0", 1),
 ('MU62-spec-missing-ignored', "extra.append('M-AGG-SPEC-MISSING')", "pass", 1),
 ('MU63-ctx-unknown-ignored', "extra.append('M-AGG-UNKNOWN')", "pass", 1),
 ('MU64-ctx-digest-members-only', "ctx_digest = _digest(record, policy, {'candidates': candidates})", "ctx_digest = _digest(record, policy, {'candidates': None})", 1),
 ('MU65-date-regex-lenient',  "_DATE_RE.fullmatch(s)", "re.match(r'\\d{4}-\\d{2}-\\d{2}', s)", 1),
 ('MU66-group-empty-value-ok', "isinstance(g.get(k), str) and g.get(k) for k in keys", "isinstance(g.get(k), str) for k in keys", 1),
 ('MU67-equivalent-as-loosen', "if {so, sn} == {'unset', 'all'}:\n                equiv = True", "if {so, sn} == {'unset', 'all'}:\n                loose = True", 1),
 ('MU68-window-direction-swapped', "if sn['window_days'] > so['window_days']: tight = True", "if sn['window_days'] > so['window_days']: loose = True", 1),
 ('MU69-more-keys-as-tighten', "if kn > ko: loose = True", "if kn > ko: tight = True", 1),
 ('MU70-spec-change-ignored', "if old.get('aggregate', True) and new.get('aggregate', True):\n        so, sn", "if False and old.get('aggregate', True) and new.get('aggregate', True):\n        so, sn", 1),
 ('MU71-equivalent-needs-two', "if kind in ('tighten', 'equivalent'):", "if kind in ('tighten',):", 1),
 ('MU72-loosen-needs-one-owner', "if kind in ('tighten', 'equivalent'):", "if kind in ('tighten', 'equivalent', 'loosen'):", 1),
 ('MU73-ctx-aggregate-flag-ignored', "and policy.get('aggregate', True)\n    extra, members", "\n    extra, members", 1),
 ('MU74-ctx-measure-unchecked', "('abs_cents' in m or 'rel_bps' in m) and policy.get('aggregate', True)\n    extra", "True and policy.get('aggregate', True)\n    extra", 1),
 ('MU75-spec-removed-as-loosen', "elif sn is None: tight = True", "elif sn is None: loose = True", 1),
 ('MU76-spec-added-as-tighten', "if so is None: loose = True", "if so is None: tight = True", 1),
 ('MU77-all-to-threshold-not-loosen', "elif sn == 'ok':\n                loose = True", "elif sn == 'ok':\n                pass", 1),
 ('MU78-threshold-to-all-not-tighten', "elif so == 'ok':\n                tight = True", "elif so == 'ok':\n                pass", 1),
 ('MU79-calendar-unchecked',  "except ValueError:\n        return None", "except TypeError:\n        return None", 1),
]
# Documented equivalent mutants (cannot change behaviour; reason recorded).  Anything else that survives is a test gap.
EQUIV = {
 'MU47-mat-from-reasons-list': "'material' is computed BEFORE 'NM-BELOW' is appended, and 'reasons' is empty exactly when nothing triggered, so bool(reasons) == any(M-*) at that point.",
}

if '--list' in sys.argv:
    for m in MUT: print(m[0])
    sys.exit(0)
from concurrent.futures import ThreadPoolExecutor
JOBS = int(os.environ.get('CR02_MUT_JOBS', '2'))
tmp = tempfile.mkdtemp(prefix='cr02_mut_')
killed = survived = equiv = ncrash = 0; unexplained = []

def run_one(item):
    mid, old, new, cnt = item
    n = src.count(old)
    if n < 1: return (mid, 'ERROR', 'pattern not found')
    mutated = src.replace(old, new) if cnt is None else src.replace(old, new, cnt)
    if mutated == src: return (mid, 'ERROR', 'no change')
    p = os.path.join(tmp, mid + '.py'); open(p, 'w', encoding='utf-8').write(mutated)
    env = dict(os.environ, CR02_MODEL_PATH=p)
    try:
        r = subprocess.run([sys.executable, '-I', TESTS, '--quiet', '--failfast'], env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return (mid, 'TIMEOUT', '')
    if r.returncode != 0:
        return (mid, 'KILLED', 'crash' if 'Traceback' in r.stderr else '')
    return (mid, 'SURVIVED', '')

try:
    ids = [m[0] for m in MUT]
    if len(set(ids)) != len(ids): print('ERROR duplicate mutant ids'); sys.exit(2)
    with ThreadPoolExecutor(max_workers=JOBS) as ex:
        results = list(ex.map(run_one, MUT))
    for mid, st, info in results:
        if st == 'ERROR':
            print(f'ERROR {mid}: {info}'); sys.exit(2)
        if st == 'TIMEOUT':
            survived += 1; unexplained.append(mid); print(f'TIMEOUT   {mid}')
        elif st == 'KILLED':
            killed += 1; ncrash += info == 'crash'
            print(f'KILLED    {mid}' + ('  (by uncaught exception, not by an assertion)' if info == 'crash' else ''))
        elif mid in EQUIV:
            equiv += 1; print(f'EQUIVALENT {mid}  -- {EQUIV[mid]}')
        else:
            survived += 1; unexplained.append(mid); print(f'SURVIVED  {mid}')
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print(f'mutants {len(MUT)}  killed {killed} (of which {ncrash} by uncaught exception)  documented-equivalent {equiv}  unexplained survivors {len(unexplained)}')
if unexplained:
    print('UNEXPLAINED:', unexplained); sys.exit(1)
print('MUTATION RUN OK')
