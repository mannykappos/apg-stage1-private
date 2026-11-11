"""Observations: validation at submission, identity and the per-item receipt (MIE1_SPEC sections 4.2 to 4.4, 4.9, 10.4; MIE-R-06 to 09, 13, 64, 66).
The core alone validates: whatever an adapter says about an item is ignored.  An item that fails is rejected with the field named and counted; it is never stored or used."""
from . import canon, pack as P, signals as S, values as V, vocab as Y

REQUIRED = ('subject_id', 'source_id', 'licence_ref', 'market', 'unit', 'observation_class', 'value_basis', 'as_of', 'retrieved_at')
OPTIONAL = ('value', 'event_label', 'valid_until', 'revision', 'supersedes', 'feed_licence_status', 'adapter_notes')
STORED = REQUIRED + ('value', 'event_label', 'valid_until', 'revision', 'supersedes', 'feed_licence_status')
ID_PREFIX = 'OB-'


def tenant_claim(obj, depth=0):
    """True if any key anywhere in obj names a tenant (a payload never chooses a tenant: MIE-R-38)."""
    if depth > 40:
        return True
    if isinstance(obj, dict):
        return any(isinstance(k, str) and 'tenant' in k.casefold() for k in obj) or any(tenant_claim(v, depth + 1) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(tenant_claim(v, depth + 1) for v in obj)
    return False


def observation_id(obs):
    return ID_PREFIX + canon.digest(obs)


def _reject(fields, why, code='OBSERVATION_INVALID', reason=None):
    out = {'status': 'REJECTED', 'code': code, 'fields': list(fields), 'why': why}
    if reason:
        out['reason'] = reason
    return out


def check(item, doc, limits, known):
    """item -> (receipt, stored observation or None).  known(observation_id) returns the observation this tenant already holds under that identifier, or None."""
    if not isinstance(item, dict):
        return _reject(['$'], 'an observation is an object'), None
    extra = sorted(set(item) - set(REQUIRED) - set(OPTIONAL))
    if extra:
        return _reject(extra, 'unknown attribute'), None
    for k in REQUIRED:
        if k not in item or item[k] is None:
            return _reject([k], 'required attribute missing'), None
    ml = limits['max_string_length']
    for k in ('subject_id', 'source_id', 'licence_ref', 'market', 'unit'):
        p = V.id_problem(item[k], ml)
        if p:
            return _reject([k], p), None
    has_value, has_event = item.get('value') is not None, item.get('event_label') is not None
    if has_value == has_event:
        return _reject(['value', 'event_label'], 'exactly one of a LEVEL value and an EVENT label is required'), None
    sid = P.canonical_subject(doc, item['subject_id'])
    if sid is None:
        return _reject(['subject_id'], 'a subject the pack does not declare'), None
    sources = {s['source_id']: s for s in doc['sources']}
    src = sources.get(item['source_id'])
    if src is None:
        return _reject(['source_id'], 'a source the pack does not declare'), None
    if item['licence_ref'] != src['licence_ref']:
        return _reject(['licence_ref'], 'not the licence the pack declares for this source'), None
    if item['market'] not in doc['vocabulary']['markets']:
        return _reject(['market'], 'a market the pack does not declare'), None
    units = {u['unit_id']: u for u in doc['vocabulary']['units']}
    if item['unit'] not in units:
        return _reject(['unit'], 'a unit the pack does not declare'), None
    if item['observation_class'] not in Y.OBSERVATION_CLASSES:
        return _reject(['observation_class'], 'not a core observation class'), None
    if item['value_basis'] not in Y.VALUE_BASES:
        return _reject(['value_basis'], 'not a core value basis'), None
    if item['value_basis'] not in src['value_bases']:
        return _reject(['value_basis'], 'a value basis the pack does not allow for this source'), None
    if V.parse_date(item['as_of']) is None:
        return _reject(['as_of'], 'as_of must be an ISO calendar date'), None
    rd = V.stamp_date(item['retrieved_at'])
    if rd is None:
        return _reject(['retrieved_at'], 'retrieved_at must be an ISO date or date-time'), None
    if rd < V.parse_date(item['as_of']):
        return _reject(['retrieved_at'], 'retrieved before the date it describes'), None
    if item.get('valid_until') is not None and V.parse_date(item['valid_until']) is None:
        return _reject(['valid_until'], 'valid_until must be an ISO calendar date'), None
    if item.get('revision') is not None and (not V.is_int(item['revision']) or item['revision'] < 0):
        return _reject(['revision'], 'revision must be a whole number of 0 or more'), None
    prior = None
    if item.get('supersedes') is not None:
        if not isinstance(item['supersedes'], str) or not item['supersedes'].startswith(ID_PREFIX):
            return _reject(['supersedes'], 'names no observation this tenant holds'), None
        prior = known(item['supersedes'])
        if not prior:
            return _reject(['supersedes'], 'names no observation this tenant holds'), None
    if item.get('feed_licence_status') is not None and item['feed_licence_status'] not in Y.LICENCE_STATUSES:
        return _reject(['feed_licence_status'], 'not a licence status'), None
    notes = item.get('adapter_notes')
    if notes is not None and not (isinstance(notes, dict) and all(isinstance(k, str) and (isinstance(v, (str, bool)) or V.is_int(v)) for k, v in notes.items())):
        return _reject(['adapter_notes'], 'adapter notes are a flat object of text, true or false and whole numbers'), None
    if has_value:
        p = V.value_problem(item['value'], limits)
        if p:
            code = 'LIMIT_EXCEEDED' if 'bound' in p or 'digits' in p else 'OBSERVATION_INVALID'
            return _reject(['value'], p, code), None
        dom = units[item['unit']]['value_domain']
        if not V.in_domain(item['value'], dom):
            return _reject(['value'], 'outside the %s value domain of the unit %s' % (dom, item['unit']), reason='VALUE_OUT_OF_DOMAIN'), None
    else:
        labels = {e['label'] for e in doc['event_mapping']}
        if item['event_label'] not in labels:
            return _reject(['event_label'], 'an event label the pack does not map'), None
    lic = {x['licence_id']: x for x in doc['licences']}[item['licence_ref']]
    if lic['status'] != 'LICENSED':
        return _reject(['licence_ref'], 'the licence is %s' % lic['status'], code='LICENCE_NOT_PERMITTED'), None
    obs = {k: item[k] for k in STORED if item.get(k) is not None}
    obs['subject_id'] = sid
    if prior is not None and not S.corrects(obs, prior):              # MIE-1.1, F-71
        return _reject(['supersedes'], 'not a correction of the same series (subject, market, unit, class, basis), source, date and kind'), None
    try:
        oid = observation_id(obs)
    except canon.CanonError as e:
        return _reject(['$'], 'no canonical form (%s)' % e.what), None
    if known(oid):
        return {'status': 'DUPLICATE', 'observation_id': oid}, None
    return {'status': 'ACCEPTED', 'observation_id': oid}, obs
