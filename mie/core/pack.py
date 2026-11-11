"""Pack schema mie-pack-1 and its validation (MIE1_SPEC sections 6.2, 6.6, 7.1 to 7.7; MIE-R-22, 28 to 34, 63, 64, 65, 69).  A pack is data: closed schema, no
executable content, validated by the core.  The order of the checks fixes which code a pack with several defects gets:
  1 size (LIMIT_EXCEEDED)  2 parse (PACK_MALFORMED)  3 schema version (PACK_SCHEMA_UNSUPPORTED)  4 core versions (PACK_CORE_INCOMPATIBLE)
  5 attempts to override a core invariant (PACK_INVARIANT_OVERRIDE)  6 closed structure, types, references, duplicates, text (PACK_MALFORMED)  7 rule count (LIMIT_EXCEEDED)
  8 the decision profile and the signal-influence policy (PACK_RULE_POLICY_VIOLATION)."""
import re
from . import canon, values as V, vocab as Y
from .vocab import MieError

TOP = ('pack_schema', 'pack_id', 'pack_version', 'field_label', 'core_compat', 'allowed_intentions', 'decision_profile', 'vocabulary', 'aliases', 'comparison_groups',
       'sources', 'licences', 'event_mapping', 'conversions', 'signals', 'parameters', 'freshness_limits', 'required_evidence', 'decision_table', 'hooks', 'provenance')
OVERRIDE_KEYS = {'default_freshness_limit', 'freshness_default', 'default_limit', 'default', 'treat_as_licensed', 'usable_statuses', 'licence_override', 'usable',
                 'signal_types', 'signal_definitions', 'signal_meaning', 'meaning', 'outcome_vocabulary', 'allow_floats', 'intentions_override'}
WILDCARD_CLASSES = {'*', 'ALL', 'ANY', 'DEFAULT'}
CODE_RE = re.compile(r'(__\w+__|\blambda\b|\b(eval|exec|compile|__import__|getattr|setattr|popen)\s*\(|<\s*script|\$\{|#!/)', re.I)
MOVEMENT_PARAMS = ('window_days', 'min_points', 'movement_basis', 'threshold')
EVENT_PARAMS = ('lookback_days',)
SELECTOR_KEYS = ('observation_class', 'value_basis', 'market', 'unit')
PRED_KEYS = {'SIGNAL_PRESENT': ('p', 'type', 'evidence_class', 'direction', 'negate'), 'SIGNAL_NOT_ASSESSED': ('p', 'type', 'reason', 'negate'),
             'GAP_PRESENT': ('p', 'reason', 'negate'), 'CONSTRAINT_COMPARE': ('p', 'constraint', 'comparison', 'param', 'negate'),
             'CONSTRAINT_ABSENT': ('p', 'constraint', 'negate'), 'SCENARIO_PRESENT': ('p', 'label', 'negate'), 'QUALIFIED': ('p', 'negate')}
RULE_KEYS = ('rule_id', 'intention', 'predicates', 'outcome', 'rationale_code', 'basis_class', 'owner_ref', 'assumption')


def _bad(code, why):
    raise MieError(code, why)


def _walk(obj, path='$'):
    """Yield (path, key, value) for every dict entry and (path, None, value) for every list item and scalar."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path, k, v
            yield from _walk(v, '%s.%s' % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, '%s[%d]' % (path, i))
    else:
        yield path, None, obj


def _overrides(doc):
    for path, k, v in _walk(doc):
        if k is not None and k in OVERRIDE_KEYS:
            _bad('PACK_INVARIANT_OVERRIDE', 'the key %r at %s would override a core invariant' % (k, path))
    floats = canon.find_floats(doc)
    if floats:
        _bad('PACK_INVARIANT_OVERRIDE', 'a float at %s: values are exact integers' % floats[0])
    ai = doc.get('allowed_intentions')
    if isinstance(ai, list) and any(i not in Y.INTENTIONS for i in ai):
        _bad('PACK_INVARIANT_OVERRIDE', 'intentions are BUY and SELL only')
    for s in doc.get('signals') or []:
        if isinstance(s, dict) and 'type' in s and s['type'] not in Y.SIGNALS:
            _bad('PACK_INVARIANT_OVERRIDE', 'the signal vocabulary is closed: %r is not a core signal' % (s['type'],))
    for f in doc.get('freshness_limits') or []:
        if isinstance(f, dict) and f.get('observation_class') in WILDCARD_CLASSES:
            _bad('PACK_INVARIANT_OVERRIDE', 'a default or wildcard freshness limit: there is no default')
    for r in doc.get('decision_table') or []:
        if isinstance(r, dict) and 'outcome' in r:
            if r.get('intention') not in Y.INTENTIONS or r['outcome'] not in Y.OUTCOMES[r['intention']]:
                _bad('PACK_INVARIANT_OVERRIDE', 'rule %r: the outcome %r is not in the vocabulary of the intention %r' % (r.get('rule_id'), r.get('outcome'), r.get('intention')))


class _Check:
    def __init__(self, limits):
        self.max_len = limits['max_string_length']

    def keys(self, obj, allowed, where, required=None):
        if not isinstance(obj, dict):
            _bad('PACK_MALFORMED', '%s must be an object' % where)
        extra = sorted(set(obj) - set(allowed))
        if extra:
            _bad('PACK_MALFORMED', 'unknown key %r in %s' % (extra[0], where))
        missing = [k for k in (allowed if required is None else required) if k not in obj]
        if missing:
            _bad('PACK_MALFORMED', 'missing key %r in %s' % (missing[0], where))

    def ident(self, v, where):
        p = V.id_problem(v, self.max_len)
        if p:
            _bad('PACK_MALFORMED', '%s: %s' % (where, p))

    def text(self, v, where):
        p = V.text_problem(v, self.max_len)
        if p:
            _bad('PACK_MALFORMED', '%s: %s' % (where, p))

    def lst(self, v, where, nonempty=False):
        if not isinstance(v, list) or (nonempty and not v):
            _bad('PACK_MALFORMED', '%s must be a %slist' % (where, 'non-empty ' if nonempty else ''))
        return v

    def one_of(self, v, options, where):
        if v not in options:
            _bad('PACK_MALFORMED', '%s: %r is not one of %s' % (where, v, ', '.join(options)))

    def unique(self, ids, where):
        seen = set()
        for i in ids:
            if i in seen:
                _bad('PACK_MALFORMED', 'duplicate identifier %r in %s' % (i, where))
            seen.add(i)
        return seen

    def int_or_none(self, v, where, low):
        if v is not None and (not V.is_int(v) or v < low):
            _bad('PACK_MALFORMED', '%s must be a whole number of %d or more, or null (not yet supplied by the owner)' % (where, low))


def _structure(doc, c):
    c.keys(doc, TOP, 'the pack')
    c.ident(doc['pack_id'], 'pack_id')
    c.ident(doc['pack_version'], 'pack_version')
    c.text(doc['field_label'], 'field_label')
    for v in c.lst(doc['core_compat'], 'core_compat', True):
        c.text(v, 'core_compat')
    ai = c.lst(doc['allowed_intentions'], 'allowed_intentions', True)
    c.unique(ai, 'allowed_intentions')
    c.one_of(doc['decision_profile'], Y.DECISION_PROFILES, 'decision_profile')
    voc = doc['vocabulary']
    c.keys(voc, ('subject_kinds', 'subjects', 'units', 'markets'), 'vocabulary')
    kinds = c.unique([k for k in c.lst(voc['subject_kinds'], 'subject_kinds')], 'subject_kinds')
    for k in kinds:
        c.ident(k, 'subject_kinds')
    units = {}
    for u in c.lst(voc['units'], 'units'):
        c.keys(u, ('unit_id', 'decimal_scale', 'value_domain'), 'units[]')
        c.ident(u['unit_id'], 'unit_id')
        if not V.is_int(u['decimal_scale']) or u['decimal_scale'] < 0:
            _bad('PACK_MALFORMED', 'unit %r: decimal_scale must be a whole number of 0 or more' % u['unit_id'])
        c.one_of(u['value_domain'], Y.VALUE_DOMAINS, 'unit %r value_domain' % u['unit_id'])
        if u['unit_id'] in units:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in units' % u['unit_id'])
        units[u['unit_id']] = u
    markets = c.unique(c.lst(voc['markets'], 'markets'), 'markets')
    for m in markets:
        c.ident(m, 'markets')
    conv_ids = set()
    for x in c.lst(doc['conversions'], 'conversions'):
        c.keys(x, ('conversion_id', 'subject_id', 'from_unit', 'to_unit', 'rate_unit', 'market'), 'conversions[]')
        for k in ('conversion_id', 'subject_id', 'from_unit', 'to_unit', 'rate_unit', 'market'):
            c.ident(x[k], 'conversions[].' + k)
        if x['conversion_id'] in conv_ids:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in conversions' % x['conversion_id'])
        conv_ids.add(x['conversion_id'])
        for k in ('from_unit', 'to_unit', 'rate_unit'):
            if x[k] not in units:
                _bad('PACK_MALFORMED', 'conversion %r names the undeclared unit %r' % (x['conversion_id'], x[k]))
        if units[x['rate_unit']]['value_domain'] != 'POSITIVE':
            _bad('PACK_MALFORMED', 'conversion %r: a conversion series must be in the POSITIVE value domain' % x['conversion_id'])
        if x['market'] not in markets:
            _bad('PACK_MALFORMED', 'conversion %r names the undeclared market %r' % (x['conversion_id'], x['market']))
    subjects = {}
    for s in c.lst(voc['subjects'], 'subjects'):
        c.keys(s, ('subject_id', 'kind', 'conversions'), 'subjects[]')
        c.ident(s['subject_id'], 'subject_id')
        if s['kind'] not in kinds:
            _bad('PACK_MALFORMED', 'subject %r has the undeclared kind %r' % (s['subject_id'], s['kind']))
        for cid in c.lst(s['conversions'], 'subjects[].conversions'):
            if cid not in conv_ids:
                _bad('PACK_MALFORMED', 'subject %r names the undeclared conversion %r' % (s['subject_id'], cid))
        if s['subject_id'] in subjects:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in subjects' % s['subject_id'])
        subjects[s['subject_id']] = s
    for x in doc['conversions']:
        if x['subject_id'] not in subjects:
            _bad('PACK_MALFORMED', 'conversion %r names the undeclared subject %r' % (x['conversion_id'], x['subject_id']))
    alias = {}
    for a in c.lst(doc['aliases'], 'aliases'):
        c.keys(a, ('alias', 'canonical'), 'aliases[]')
        c.ident(a['alias'], 'alias')
        if a['alias'] in subjects:
            _bad('PACK_MALFORMED', 'alias %r is itself a declared subject (a cycle or an ambiguity)' % a['alias'])
        if a['canonical'] not in subjects:
            _bad('PACK_MALFORMED', 'alias %r maps to %r, which is not a declared subject' % (a['alias'], a['canonical']))
        if a['alias'] in alias:
            _bad('PACK_MALFORMED', 'alias %r maps to more than one subject' % a['alias'])
        alias[a['alias']] = a['canonical']
    licences = {}
    for lic in c.lst(doc['licences'], 'licences'):
        c.keys(lic, ('licence_id', 'status', 'valid_from', 'valid_to', 'terms_ref'), 'licences[]')
        c.ident(lic['licence_id'], 'licence_id')
        c.one_of(lic['status'], Y.LICENCE_STATUSES, 'licence %r status' % lic['licence_id'])
        a, b = V.parse_date(lic['valid_from']), V.parse_date(lic['valid_to'])
        if a is None or b is None or a > b:
            _bad('PACK_MALFORMED', 'licence %r: valid_from and valid_to must be ISO dates in order' % lic['licence_id'])
        c.text(lic['terms_ref'], 'terms_ref')
        if lic['licence_id'] in licences:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in licences' % lic['licence_id'])
        licences[lic['licence_id']] = lic
    sources = {}
    for s in c.lst(doc['sources'], 'sources'):
        c.keys(s, ('source_id', 'licence_ref', 'value_bases'), 'sources[]')
        c.ident(s['source_id'], 'source_id')
        if s['licence_ref'] not in licences:
            _bad('PACK_MALFORMED', 'source %r names the undeclared licence %r' % (s['source_id'], s['licence_ref']))
        for b in c.lst(s['value_bases'], 'value_bases', True):
            c.one_of(b, Y.VALUE_BASES, 'source %r value_bases' % s['source_id'])
        c.unique(s['value_bases'], 'value_bases')
        if s['source_id'] in sources:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in sources' % s['source_id'])
        sources[s['source_id']] = s
    labels = set()
    for e in c.lst(doc['event_mapping'], 'event_mapping'):
        c.keys(e, ('label', 'event_class', 'availability'), 'event_mapping[]')
        c.ident(e['label'], 'event label')
        c.one_of(e['event_class'], Y.EVENT_CLASSES, 'event %r event_class' % e['label'])
        if e['event_class'] == 'AVAILABILITY_CHANGED':
            c.one_of(e['availability'], Y.AVAILABILITY, 'event %r availability' % e['label'])
        elif e['availability'] is not None:
            _bad('PACK_MALFORMED', 'event %r: availability applies only to AVAILABILITY_CHANGED' % e['label'])
        if e['label'] in labels:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in event_mapping' % e['label'])
        labels.add(e['label'])
    groups = set()
    for g in c.lst(doc['comparison_groups'], 'comparison_groups'):
        c.keys(g, ('group_id', 'subject_id', 'unit', 'market', 'observation_class', 'value_basis', 'sources'), 'comparison_groups[]')
        c.ident(g['group_id'], 'group_id')
        if g['subject_id'] not in subjects or g['unit'] not in units or g['market'] not in markets:
            _bad('PACK_MALFORMED', 'comparison group %r names an undeclared subject, unit or market' % g['group_id'])
        c.one_of(g['observation_class'], Y.OBSERVATION_CLASSES, 'comparison group observation_class')
        c.one_of(g['value_basis'], Y.VALUE_BASES, 'comparison group value_basis')
        for s in c.lst(g['sources'], 'comparison group sources', True):
            if s not in sources:
                _bad('PACK_MALFORMED', 'comparison group %r names the undeclared source %r' % (g['group_id'], s))
        if g['group_id'] in groups:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in comparison_groups' % g['group_id'])
        groups.add(g['group_id'])
    params = {}
    for p in c.lst(doc['parameters'], 'parameters'):
        c.keys(p, ('param_id', 'value', 'owner_ref'), 'parameters[]')
        c.ident(p['param_id'], 'param_id')
        if p['value'] is not None and not V.is_int(p['value']):
            _bad('PACK_MALFORMED', 'parameter %r must be a whole number or null (not yet supplied)' % p['param_id'])
        c.text(p['owner_ref'], 'parameters[].owner_ref')
        if p['param_id'] in params:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in parameters' % p['param_id'])
        params[p['param_id']] = p
    sig_ids, sig_types = set(), set()
    for s in c.lst(doc['signals'], 'signals'):
        c.keys(s, ('signal_id', 'type', 'selector', 'params', 'parameter_owner_ref'), 'signals[]')
        c.ident(s['signal_id'], 'signal_id')
        if s['type'] in Y.DATA_SIGNALS:
            _bad('PACK_MALFORMED', 'signal %r: the data-quality signals are always reported and are not configured' % s['signal_id'])
        c.text(s['parameter_owner_ref'], 'parameter_owner_ref')
        sel = s['selector']
        if s['type'] == 'CONVERSION_MOVEMENT':
            c.keys(sel, ('conversion_id',), 'signal %r selector' % s['signal_id'])
            if sel['conversion_id'] not in conv_ids:
                _bad('PACK_MALFORMED', 'signal %r names the undeclared conversion %r' % (s['signal_id'], sel['conversion_id']))
        else:
            c.keys(sel, SELECTOR_KEYS, 'signal %r selector' % s['signal_id'], required=())
            if 'observation_class' in sel:
                c.one_of(sel['observation_class'], Y.OBSERVATION_CLASSES, 'selector observation_class')
            if 'value_basis' in sel:
                c.one_of(sel['value_basis'], Y.VALUE_BASES, 'selector value_basis')
            if 'market' in sel and sel['market'] not in markets:
                _bad('PACK_MALFORMED', 'signal %r names the undeclared market %r' % (s['signal_id'], sel['market']))
            if 'unit' in sel and sel['unit'] not in units:
                _bad('PACK_MALFORMED', 'signal %r names the undeclared unit %r' % (s['signal_id'], sel['unit']))
        pr = s['params']
        if s['type'] in Y.MOVEMENT_SIGNALS:
            c.keys(pr, MOVEMENT_PARAMS, 'signal %r params' % s['signal_id'])
            c.int_or_none(pr['window_days'], 'window_days', 1)
            c.int_or_none(pr['min_points'], 'min_points', 2)
            if pr['movement_basis'] is not None:
                c.one_of(pr['movement_basis'], Y.MOVEMENT_BASES, 'movement_basis')
            t = pr['threshold']
            if t is not None:
                if not (isinstance(t, dict) and set(t) == {'num', 'den'} and V.is_int(t['num']) and V.is_int(t['den']) and t['num'] > 0 and t['den'] > 0):
                    _bad('PACK_MALFORMED', 'signal %r: the movement threshold must be an exact positive integer ratio {num, den}' % s['signal_id'])
        else:
            c.keys(pr, EVENT_PARAMS, 'signal %r params' % s['signal_id'])
            c.int_or_none(pr['lookback_days'], 'lookback_days', 0)
        if s['signal_id'] in sig_ids:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in signals' % s['signal_id'])
        sig_ids.add(s['signal_id'])
        sig_types.add(s['type'])
    fclasses = set()
    for f in c.lst(doc['freshness_limits'], 'freshness_limits'):
        c.keys(f, ('observation_class', 'days', 'owner_ref'), 'freshness_limits[]')
        c.one_of(f['observation_class'], Y.OBSERVATION_CLASSES, 'freshness_limits observation_class')
        if not V.is_int(f['days']) or f['days'] < 0:
            _bad('PACK_MALFORMED', 'freshness limit for %s must be a whole number of days, 0 or more (negative, boolean, float, text or null is refused)' % f['observation_class'])
        c.text(f['owner_ref'], 'freshness_limits[].owner_ref')
        if f['observation_class'] in fclasses:
            _bad('PACK_MALFORMED', 'two freshness limits for %s' % f['observation_class'])
        fclasses.add(f['observation_class'])
    ev = set()
    for r in c.lst(doc['required_evidence'], 'required_evidence'):
        c.keys(r, ('evidence_id',) + SELECTOR_KEYS, 'required_evidence[]', required=('evidence_id', 'observation_class'))
        c.ident(r['evidence_id'], 'evidence_id')
        c.one_of(r['observation_class'], Y.OBSERVATION_CLASSES, 'required_evidence observation_class')
        if 'value_basis' in r:
            c.one_of(r['value_basis'], Y.VALUE_BASES, 'required_evidence value_basis')
        if 'market' in r and r['market'] not in markets or 'unit' in r and r['unit'] not in units:
            _bad('PACK_MALFORMED', 'required evidence %r names an undeclared market or unit' % r['evidence_id'])
        if r['evidence_id'] in ev:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in required_evidence' % r['evidence_id'])
        ev.add(r['evidence_id'])
    hooks = set()
    for h in c.lst(doc['hooks'], 'hooks'):
        c.keys(h, ('hook_id', 'port'), 'hooks[]')
        c.ident(h['hook_id'], 'hook_id')
        if h['port'] != 'CostValueHookPort':
            _bad('PACK_MALFORMED', 'hook %r names the port %r: the only hook slot is CostValueHookPort' % (h['hook_id'], h['port']))
        if h['hook_id'] in hooks:
            _bad('PACK_MALFORMED', 'duplicate identifier %r in hooks' % h['hook_id'])
        hooks.add(h['hook_id'])
    prov = doc['provenance']
    c.keys(prov, ('author_ref', 'owner_ref', 'synthetic'), 'provenance')
    c.text(prov['author_ref'], 'author_ref')
    c.text(prov['owner_ref'], 'owner_ref')
    if not isinstance(prov['synthetic'], bool):
        _bad('PACK_MALFORMED', 'provenance.synthetic must be true or false')
    table = doc['decision_table']
    if table is not None:
        rule_ids = set()
        for r in c.lst(table, 'decision_table'):
            c.keys(r, RULE_KEYS, 'decision rule', required=RULE_KEYS[:6])
            c.ident(r['rule_id'], 'rule_id')
            if r['intention'] not in ai:
                _bad('PACK_MALFORMED', 'rule %r is for the intention %r, which the pack does not allow' % (r['rule_id'], r['intention']))
            c.ident(r['rationale_code'], 'rationale_code')
            c.one_of(r['basis_class'], Y.BASIS_CLASSES, 'rule %r basis_class' % r['rule_id'])
            for k in ('owner_ref', 'assumption'):
                if r.get(k) is not None:
                    c.text(r[k], 'rule %r %s' % (r['rule_id'], k))
            for p in c.lst(r['predicates'], 'rule %r predicates' % r['rule_id'], True):
                _predicate(p, r['rule_id'], c, params, sig_types)
            if r['rule_id'] in rule_ids:
                _bad('PACK_MALFORMED', 'duplicate identifier %r in decision_table' % r['rule_id'])
            rule_ids.add(r['rule_id'])
    for path, k, v in _walk(doc):
        if isinstance(v, str) and CODE_RE.search(v):
            _bad('PACK_MALFORMED', 'code-like content at %s: a pack is data only' % path)


def _predicate(p, rid, c, params, sig_types):
    if not isinstance(p, dict) or p.get('p') not in Y.PREDICATES:
        _bad('PACK_MALFORMED', 'rule %r: a predicate must name one of %s' % (rid, ', '.join(Y.PREDICATES)))
    c.keys(p, PRED_KEYS[p['p']], 'rule %r predicate %s' % (rid, p['p']))
    if not isinstance(p['negate'], bool):
        _bad('PACK_MALFORMED', 'rule %r: negate must be true or false' % rid)
    k = p['p']
    if k in ('SIGNAL_PRESENT', 'SIGNAL_NOT_ASSESSED'):
        c.one_of(p['type'], Y.SIGNALS, 'rule %r signal type' % rid)
        if p['type'] in Y.MARKET_SIGNALS and p['type'] not in sig_types:
            _bad('PACK_MALFORMED', 'rule %r refers to the signal %s, which the pack does not configure' % (rid, p['type']))
    if k == 'SIGNAL_PRESENT':
        if p['evidence_class'] is not None:
            c.one_of(p['evidence_class'], Y.OBSERVATION_CLASSES, 'rule %r evidence_class' % rid)
        d = p['direction']
        allowed = Y.DIRECTIONS if p['type'] in Y.MOVEMENT_SIGNALS else Y.AVAILABILITY if p['type'] == 'AVAILABILITY_CHANGE' else ()
        if d is not None and d not in allowed:
            _bad('PACK_MALFORMED', 'rule %r: direction %r does not apply to %s' % (rid, d, p['type']))
    if k == 'SIGNAL_NOT_ASSESSED' and p['reason'] is not None:
        c.one_of(p['reason'], Y.REASONS, 'rule %r reason' % rid)
    if k == 'GAP_PRESENT':
        c.one_of(p['reason'], Y.REASONS, 'rule %r gap reason' % rid)
    if k in ('CONSTRAINT_COMPARE', 'CONSTRAINT_ABSENT'):
        c.one_of(p['constraint'], Y.CONSTRAINTS, 'rule %r constraint' % rid)
    if k == 'CONSTRAINT_COMPARE':
        c.one_of(p['comparison'], Y.COMPARISONS, 'rule %r comparison' % rid)
        if p['param'] not in params:
            _bad('PACK_MALFORMED', 'rule %r refers to the undeclared parameter %r' % (rid, p['param']))
    if k == 'SCENARIO_PRESENT':
        c.ident(p['label'], 'rule %r scenario label' % rid)


def market_predicate(p):
    return p['p'] in ('SIGNAL_PRESENT', 'SIGNAL_NOT_ASSESSED') and p['type'] in Y.MARKET_SIGNALS


def signal_influenced(rule):
    """Definition 1 (MIE-R-63): the rule contains a market-signal predicate, negated or not, whatever its outcome."""
    return any(market_predicate(p) for p in rule['predicates'])


def first_influenced(table):
    """The position of the first signal-influenced rule in the table AS SUBMITTED, or None.  Every rule at or after it is signal-influenced or downstream (definition 2)."""
    for i, r in enumerate(table or []):
        if signal_influenced(r):
            return i
    return None


def owner_labelled(rule):
    return rule['basis_class'] == 'OWNER_ASSUMPTION' and isinstance(rule.get('owner_ref'), str) and bool(rule['owner_ref'].strip()) \
        and isinstance(rule.get('assumption'), str) and bool(rule['assumption'].strip())


def _policy(doc):
    table = doc['decision_table'] or []
    for r in table:
        if r['basis_class'] == 'OWNER_ASSUMPTION' and not owner_labelled(r):
            _bad('PACK_RULE_POLICY_VIOLATION', 'rule %r is OWNER_ASSUMPTION without both an owner reference and an assumption statement' % r['rule_id'])
    if doc['decision_profile'] == 'CONTEXT_ONLY':
        for r in table:
            if signal_influenced(r):
                _bad('PACK_RULE_POLICY_VIOLATION', 'rule %r uses a market-signal predicate under the CONTEXT_ONLY profile' % r['rule_id'])
        return
    first = first_influenced(table)
    if first is None:
        return
    for r in table[first:]:
        if not owner_labelled(r):
            why = 'signal-influenced' if signal_influenced(r) else 'downstream of the signal-influenced rule %r' % table[first]['rule_id']
            _bad('PACK_RULE_POLICY_VIOLATION', 'rule %r is %s and must be OWNER_ASSUMPTION with an owner reference and an assumption statement, whatever its outcome'
                 % (r['rule_id'], why))


def validate(pack_bytes, limits):
    """pack bytes -> (pack document, pin).  Raises MieError with the first defect in the fixed order above."""
    if not isinstance(pack_bytes, (bytes, bytearray)):
        _bad('REQUEST_MALFORMED', 'pack bytes required')
    if len(pack_bytes) > limits['max_pack_bytes']:
        _bad('LIMIT_EXCEEDED', 'pack larger than the configured bound')
    try:
        doc = canon.loads(pack_bytes)
    except canon.CanonError as e:
        _bad('PACK_MALFORMED', 'not a well-formed pack document (%s)' % e.what)
    if not isinstance(doc, dict):
        _bad('PACK_MALFORMED', 'a pack is a JSON object')
    if not isinstance(doc.get('pack_schema'), str):
        _bad('PACK_MALFORMED', 'pack_schema missing')
    if doc['pack_schema'] != Y.PACK_SCHEMA:
        _bad('PACK_SCHEMA_UNSUPPORTED', 'this core reads %s, not %r' % (Y.PACK_SCHEMA, doc['pack_schema']))
    cc = doc.get('core_compat')
    if not isinstance(cc, list) or not all(isinstance(x, str) for x in cc):
        _bad('PACK_MALFORMED', 'core_compat must be a list of core versions')
    if Y.CORE_VERSION not in cc:
        _bad('PACK_CORE_INCOMPATIBLE', 'the pack names no core version this core supports (%s)' % Y.CORE_VERSION)
    _overrides(doc)
    _structure(doc, _Check(limits))
    if doc['decision_table'] is not None and len(doc['decision_table']) > limits['max_rules']:
        _bad('LIMIT_EXCEEDED', 'more decision rules than the configured bound')
    _policy(doc)
    try:
        h = canon.digest(doc)
    except canon.CanonError as e:
        _bad('PACK_MALFORMED', 'the pack has no canonical form (%s)' % e.what)
    return doc, {'pack_id': doc['pack_id'], 'pack_version': doc['pack_version'], 'pack_hash': h}


def pin_problem(pin):
    """-> None or why a pack reference is malformed."""
    if not (isinstance(pin, dict) and set(pin) == {'pack_id', 'pack_version', 'pack_hash'} and all(isinstance(pin[k], str) for k in pin)):
        return 'a pack reference is {pack_id, pack_version, pack_hash}'
    if not re.match(r'^[0-9a-f]{64}$', pin['pack_hash']):
        return 'pack_hash must be 64 lower-case hex characters'
    return None


def canonical_subject(doc, sid):
    """The declared subject an identifier names, through the pack's alias table only, or None.  The core never infers equivalence."""
    subjects = {s['subject_id'] for s in doc['vocabulary']['subjects']}
    if sid in subjects:
        return sid
    for a in doc['aliases']:
        if a['alias'] == sid:
            return a['canonical']
    return None
