#!/usr/bin/env python3
"""CR-02 Stage 1 (A1 Materiality) -- REFERENCE MODEL v0.2 (rev 2).   DRAFT / PROPOSED. Not an implementation.

Purpose: make the proposed materiality rules executable so they can be tested at their boundaries.
It uses SYNTHETIC records and policies only. It is not product code, is not connected to any Anchor
Engine source, and makes no claim about how the product will implement the rules.

Design rules (see the CR-02 Stage 1 rev 2 draft, section 4):
  R1  Money is integer cents. Relative thresholds are integer basis points. No floats anywhere.
  R2  Fail-safe: anything that cannot be assessed is MATERIAL, and the reason is recorded.
  R3  A subject type with NO threshold configured: every record is material  (reason M-THRESHOLD-UNSET = "not configured").
  R3a [rev 2] A subject type with the explicit rule {'all_records': True}: every record is material  (reason M-ALL-RECORDS =
      "intentionally unconditional"). The two are different states: only the first is a configuration gap.
  R4  A category on the always-material list is material whatever the amount.
  R5  Aggregation (no splitting). [rev 2] Related records are those of the SAME subject type with the same value for every key in
      policy['aggregation']['keys'] ('project' is mandatory because every base is project-level) and a date within
      window_days (inclusive) of the assessed record. The assessed record's own project bases are used for the relative test.
      A record or candidate whose group or date cannot be determined makes the assessment material (M-AGG-UNKNOWN).
  R6  Every decision carries the policy version and a digest of its inputs.
  R7  Policy changes: loosening needs more approval than tightening; the proposer never approves; an AI actor never approves.
"""
import datetime, hashlib, json, re

MODEL_VERSION = 'cr02-materiality-0.2'
BASES = ('contract_value', 'forecast_final_cost', 'forecast_margin')
MATERIAL_REASONS = (
    'M-POLICY-INVALID', 'M-UNKNOWN-SUBJECT', 'M-ALWAYS', 'M-ALL-RECORDS', 'M-THRESHOLD-UNSET', 'M-THRESHOLD-INVALID',
    'M-AMOUNT-MISSING', 'M-AMOUNT-INVALID', 'M-DAYS-MISSING', 'M-DAYS-INVALID', 'M-BASE-INVALID',
    'M-ABS', 'M-REL', 'M-DAYS', 'M-AGG', 'M-AGG-UNKNOWN', 'M-AGG-SPEC-MISSING', 'M-INPUT-INVALID')
NOT_MATERIAL_REASONS = ('NM-BELOW',)
_DATE_RE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')   # ASCII digits only, whole string (no trailing newline)


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def _rule_state(rule):
    """-> ('unset'|'all'|'invalid'|'ok', measures dict)."""
    if not isinstance(rule, dict):
        return 'invalid', {}
    allowed = {'abs_cents', 'rel_bps', 'rel_base', 'delay_days', 'all_records'}
    if set(rule) - allowed:
        return 'invalid', {}
    if 'all_records' in rule:
        if set(rule) == {'all_records'} and rule['all_records'] is True:
            return 'all', {}
        return 'invalid', {}
    m = {}
    if 'abs_cents' in rule:
        if not _is_int(rule['abs_cents']) or rule['abs_cents'] < 1:
            return 'invalid', {}
        m['abs_cents'] = rule['abs_cents']
    if ('rel_bps' in rule) != ('rel_base' in rule):
        return 'invalid', {}
    if 'rel_bps' in rule:
        if not _is_int(rule['rel_bps']) or rule['rel_bps'] < 1 or rule['rel_base'] not in BASES:
            return 'invalid', {}
        m['rel_bps'] = rule['rel_bps']
        m['rel_base'] = rule['rel_base']
    if 'delay_days' in rule:
        if not _is_int(rule['delay_days']) or rule['delay_days'] < 1:
            return 'invalid', {}
        m['delay_days'] = rule['delay_days']
    if not m:
        return 'unset', {}
    return 'ok', m


def aggregation_spec_valid(spec):
    if not isinstance(spec, dict) or set(spec) != {'keys', 'window_days'}:
        return False
    k = spec['keys']
    if not isinstance(k, list) or not k or not all(isinstance(x, str) and x for x in k) or len(set(k)) != len(k):
        return False
    if 'project' not in k:
        return False
    w = spec['window_days']
    return _is_int(w) and w >= 1


def policy_valid(policy):
    if not isinstance(policy, dict):
        return False
    v = policy.get('version')
    if not isinstance(v, str) or not v.strip():
        return False
    if not isinstance(policy.get('rules'), dict):
        return False
    am = policy.get('always_material', [])
    if not isinstance(am, list) or not all(isinstance(c, str) and c for c in am):
        return False
    if not isinstance(policy.get('aggregate', True), bool):
        return False
    if 'aggregation' in policy and not aggregation_spec_valid(policy['aggregation']):
        return False
    return True


def _digest(record, policy, group):
    try:
        return hashlib.sha256(_canon({'model': MODEL_VERSION, 'policy': policy, 'record': record, 'group': group}).encode()).hexdigest()
    except (TypeError, ValueError):
        return None


def _amount_tests(amount_abs, bases, m, reasons, tag_abs, tag_rel):
    """Apply absolute and relative tests to an absolute amount (cents)."""
    if 'abs_cents' in m and amount_abs >= m['abs_cents']:
        reasons.append(tag_abs)
    if 'rel_bps' in m:
        base = (bases or {}).get(m['rel_base']) if isinstance(bases, dict) else None
        if not _is_int(base) or base < 1:
            reasons.append('M-BASE-INVALID')
        elif amount_abs * 10000 >= m['rel_bps'] * base:
            reasons.append(tag_rel)


def assess(record, policy, group_records=None):
    """Low-level assessment. `group_records` = the OTHER records of the aggregation group, already selected by the caller
    (use assess_with_context to have the model select them).
    -> {'material': bool, 'reasons': [...], 'rule_version': str|None, 'digest': str|None}"""
    reasons = []
    ver = policy.get('version') if isinstance(policy, dict) and isinstance(policy.get('version'), str) else None
    dig = _digest(record, policy, group_records)

    def out():
        mat = any(r.startswith('M-') for r in reasons)
        if not reasons:
            reasons.append('NM-BELOW')
        return {'material': mat, 'reasons': sorted(set(reasons)), 'rule_version': ver, 'digest': dig}

    if dig is None or not isinstance(record, dict):
        reasons.append('M-INPUT-INVALID'); return out()
    if not policy_valid(policy):
        reasons.append('M-POLICY-INVALID'); return out()
    subject = record.get('subject')
    if not isinstance(subject, str) or subject not in policy['rules']:
        reasons.append('M-UNKNOWN-SUBJECT'); return out()
    cats = record.get('categories', [])
    if not isinstance(cats, list) or not all(isinstance(c, str) for c in cats):
        reasons.append('M-INPUT-INVALID'); return out()
    if any(c in policy.get('always_material', []) for c in cats):
        reasons.append('M-ALWAYS')
    state, m = _rule_state(policy['rules'][subject])
    if state == 'all':
        reasons.append('M-ALL-RECORDS'); return out()
    if state == 'unset':
        reasons.append('M-THRESHOLD-UNSET'); return out()
    if state == 'invalid':
        reasons.append('M-THRESHOLD-INVALID'); return out()
    # amount measure
    if 'abs_cents' in m or 'rel_bps' in m:
        a = record.get('amount_cents')
        if a is None:
            reasons.append('M-AMOUNT-MISSING')
        elif not _is_int(a):
            reasons.append('M-AMOUNT-INVALID')
        else:
            _amount_tests(abs(a), record.get('bases'), m, reasons, 'M-ABS', 'M-REL')
    # delay measure
    if 'delay_days' in m:
        d = record.get('delay_days')
        if d is None:
            reasons.append('M-DAYS-MISSING')
        elif not _is_int(d):
            reasons.append('M-DAYS-INVALID')
        elif abs(d) >= m['delay_days']:
            reasons.append('M-DAYS')
    # aggregation (anti-splitting)
    if group_records and policy.get('aggregate', True) and ('abs_cents' in m or 'rel_bps' in m):
        members = [record] + list(group_records)
        amts = []
        unknown = False
        for r in members:
            if not isinstance(r, dict) or not _is_int(r.get('amount_cents')) or r.get('subject') != subject:
                unknown = True
            else:
                amts.append(abs(r['amount_cents']))
        if unknown:
            reasons.append('M-AGG-UNKNOWN')
        else:
            agg = []
            _amount_tests(sum(amts), record.get('bases'), m, agg, 'M-AGG', 'M-AGG')
            reasons.extend(agg)
    return out()


# ---------------------------------------------------------------- grouping (R5, rev 2)
def _parse_date(s):
    """ISO calendar date YYYY-MM-DD -> proleptic ordinal, else None."""
    if not isinstance(s, str) or not _DATE_RE.fullmatch(s):
        return None
    try:
        return datetime.date(int(s[0:4]), int(s[5:7]), int(s[8:10])).toordinal()
    except ValueError:
        return None


def _group_ok(g, keys):
    return isinstance(g, dict) and all(isinstance(g.get(k), str) and g.get(k) for k in keys)


def select_group(record, candidates, spec):
    """-> (members, unknown).  members = candidates in the record's aggregation group.  unknown = True if the record's own
    group/date cannot be determined, or any same-subject candidate cannot be placed (fail-safe)."""
    keys, win = spec['keys'], spec['window_days']
    rd = _parse_date(record.get('date'))
    if not _group_ok(record.get('group'), keys) or rd is None:
        return [], True
    members, unknown = [], False
    for c in candidates:
        if not isinstance(c, dict):
            unknown = True; continue
        if c.get('subject') != record.get('subject'):
            continue
        if c.get('id') is not None and c.get('id') == record.get('id'):
            continue                                   # the record itself
        cd = _parse_date(c.get('date'))
        if not _group_ok(c.get('group'), keys) or cd is None:
            unknown = True; continue
        if all(c['group'][k] == record['group'][k] for k in keys) and abs(cd - rd) <= win:
            members.append(c)
    return members, unknown


def _flag(res, extra):
    """Return a copy of an assess() result with extra material reasons added."""
    res = dict(res)
    res['reasons'] = sorted((set(res['reasons']) | set(extra)) - {'NM-BELOW'})
    res['material'] = True
    return res


def assess_with_context(record, candidates, policy):
    """Assess a record against the other records of the same project/period: the model selects the aggregation group from
    `candidates` using policy['aggregation'] and then applies assess().  The digest covers ALL candidates."""
    ctx_digest = _digest(record, policy, {'candidates': candidates})
    if not isinstance(candidates, list) or ctx_digest is None:
        res = _flag(assess(record, policy, None), ['M-INPUT-INVALID'])
        res['digest'] = ctx_digest
        return res
    subject = record.get('subject') if isinstance(record, dict) else None
    if not policy_valid(policy) or not isinstance(subject, str) or subject not in policy['rules']:
        res = assess(record, policy, None)
        res['digest'] = ctx_digest
        return res
    state, m = _rule_state(policy['rules'][subject])
    needs = state == 'ok' and ('abs_cents' in m or 'rel_bps' in m) and policy.get('aggregate', True)
    extra, members = [], None
    if needs:
        spec = policy.get('aggregation')
        if spec is None:
            extra.append('M-AGG-SPEC-MISSING')
        else:
            mem, unknown = select_group(record, candidates, spec)
            if unknown:
                extra.append('M-AGG-UNKNOWN')
            members = mem or None
    res = assess(record, policy, members)
    if extra:
        res = _flag(res, extra)
    res['digest'] = ctx_digest
    return res


# ---------------------------------------------------------------- policy change control (R7)
def _strict_items(policy):
    """Flatten a policy into comparable items. For thresholds, a SMALLER number is STRICTER."""
    items = {}
    for subj, rule in sorted(policy['rules'].items()):
        st, m = _rule_state(rule)
        items[('rule', subj)] = (st if st in ('all', 'ok') else 'unset', None)
        if st == 'ok':
            for k in ('abs_cents', 'rel_bps', 'delay_days'):
                items[('thr', subj, k)] = m.get(k)
            items[('base', subj)] = m.get('rel_base')
    for c in policy.get('always_material', []):
        items[('always', c)] = True
    items[('agg',)] = policy.get('aggregate', True)
    return items


def classify_change(old, new):
    """-> 'none' | 'equivalent' | 'tighten' | 'loosen' | 'mixed' | 'invalid'.
    'equivalent' = the set of material records is unchanged but the configuration differs (not-configured <-> explicit all_records).
    Setting a threshold where none (or all_records) existed is a LOOSENING."""
    if not policy_valid(old) or not policy_valid(new):
        return 'invalid'
    for p in (old, new):
        for rule in p['rules'].values():
            if _rule_state(rule)[0] == 'invalid':
                return 'invalid'
    a, b = _strict_items(old), _strict_items(new)
    tight = loose = equiv = False
    for key in set(a) | set(b):
        o, n = a.get(key), b.get(key)
        if o == n:
            continue
        kind = key[0]
        if kind == 'rule':
            so = o[0] if o else 'unset'
            sn = n[0] if n else 'unset'
            if so == sn:
                continue
            if {so, sn} == {'unset', 'all'}:
                equiv = True
            elif sn == 'ok':
                loose = True
            elif so == 'ok':
                tight = True
        elif kind == 'thr':
            if o is None and n is not None:    # extra test added
                if a.get(('rule', key[1]), ('unset',))[0] == 'ok':
                    tight = True
            elif o is not None and n is None:  # a test removed
                if b.get(('rule', key[1]), ('unset',))[0] == 'ok':
                    loose = True
            elif o is not None and n is not None:
                if n < o: tight = True
                else: loose = True
        elif kind == 'base':
            if o is not None and n is not None:
                tight = loose = True            # a changed basis cannot be shown stricter or looser: 'mixed'
        elif kind == 'always':
            if o is None: tight = True
            elif n is None: loose = True
        elif kind == 'agg':
            if o is True and n is False: loose = True
            elif o is False and n is True: tight = True
    # aggregation specification (only meaningful when aggregation is on in both)
    if old.get('aggregate', True) and new.get('aggregate', True):
        so, sn = old.get('aggregation'), new.get('aggregation')
        if so != sn:
            if so is None: loose = True        # absent spec fails safe (strictest); a spec is a loosening
            elif sn is None: tight = True
            else:
                ko, kn = set(so['keys']), set(sn['keys'])
                if kn > ko: loose = True       # more keys -> narrower groups -> easier to split
                elif kn < ko: tight = True
                elif kn != ko: tight = loose = True
                if sn['window_days'] > so['window_days']: tight = True
                elif sn['window_days'] < so['window_days']: loose = True
    if tight and loose: return 'mixed'
    if tight: return 'tighten'
    if loose: return 'loosen'
    if equiv: return 'equivalent'
    return 'none'


def change_allowed(old, new, change):
    """-> (bool, code). `change` = {'proposer': str, 'proposer_kind': 'human'|'ai',
    'approvals': [{'approver': str, 'role': str, 'kind': 'human'|'ai'}]}"""
    kind = classify_change(old, new)
    if kind == 'invalid':
        return False, 'C-INVALID'
    if kind == 'none':
        return False, 'C-NOCHANGE'
    if new['version'] == old['version']:
        return False, 'C-VERSION'
    if not isinstance(change, dict) or not isinstance(change.get('proposer'), str) or not change['proposer']:
        return False, 'C-PROPOSER'
    if change.get('proposer_kind') not in ('human', 'ai'):
        return False, 'C-PROPOSER'
    valid = {}
    for ap in change.get('approvals', []) if isinstance(change.get('approvals'), list) else []:
        if not isinstance(ap, dict): continue
        who, role, k = ap.get('approver'), ap.get('role'), ap.get('kind')
        if not isinstance(who, str) or not who or k != 'human' or who == change['proposer']:
            continue
        valid.setdefault(who, set()).add(role)
    owners = [w for w, r in valid.items() if 'materiality_owner' in r]
    if kind in ('tighten', 'equivalent'):
        return (True, 'C-OK') if owners else (False, 'C-APPROVAL')
    # loosen or mixed
    if len(valid) >= 2 and owners:
        return True, 'C-OK'
    return False, 'C-APPROVAL'
