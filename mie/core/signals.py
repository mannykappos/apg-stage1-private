"""Evidence and signals (MIE1_SPEC sections 4.4 to 4.8, 5, 6.4; MIE-R-09 to 12, 14 to 20, 24, 27, 64, 65).
Pure functions over the stored observations a caller hands in: nothing here reads a store, a clock or a feed.  A signal states what was observed; none predicts anything.
A missing point stays missing (no interpolation, carry-forward or borrowing), a conflict is reported and never resolved, and every exclusion is a listed gap."""
from fractions import Fraction
from . import values as V, vocab as Y

ELIGIBLE = 'ELIGIBLE'


def series_key(o):
    return (o['subject_id'], o['market'], o['unit'], o['observation_class'], o['value_basis'])


def corrects(new, old):
    """True when `new` may supersede `old` (MIE-1.1, F-71; section 4.7: a correction is for one series and as_of).  Both are of the same subject, market, unit,
    observation class and value basis (one series), from the same source, for the same as_of date, and of the same kind (both a LEVEL value or both an EVENT)."""
    return (series_key(new) == series_key(old) and new['source_id'] == old['source_id'] and new['as_of'] == old['as_of']
            and ('value' in new) == ('value' in old) and ('event_label' in new) == ('event_label' in old))


def _licences(doc):
    return {x['licence_id']: x for x in doc['licences']}


def classify(doc, observations, evaluation_date):
    """-> {observation_id: (state, reason)} where state is ELIGIBLE, HISTORY (expired or superseded: kept as labelled history) or EXCLUDED, and the reason is a core reason
    code or None.  Observations dated after the evaluation date and observations outside their licence are never used."""
    lic = _licences(doc)
    out = {}
    superseded = {o['supersedes'] for o in observations.values()
                  if o.get('supersedes') and o['supersedes'] in observations and corrects(o, observations[o['supersedes']])}   # an incompatible link never hides evidence
    best_rev = {}
    for oid, o in observations.items():
        if 'value' in o and o.get('revision') is not None:
            k = series_key(o) + (o['as_of'], o['source_id'])
            best_rev[k] = max(best_rev.get(k, -1), o['revision'])
    for oid, o in observations.items():
        L = lic.get(o['licence_ref'])
        if o['as_of'] > evaluation_date:
            out[oid] = ('EXCLUDED', 'OBSERVATION_AFTER_EVALUATION_DATE')
        elif L is None or L['status'] != 'LICENSED' or not (L['valid_from'] <= evaluation_date <= L['valid_to']):
            out[oid] = ('EXCLUDED', 'LICENCE_EXCLUDED')
        elif oid in superseded:
            out[oid] = ('HISTORY', None)
        elif 'value' in o and (o.get('revision') or 0) < best_rev.get(series_key(o) + (o['as_of'], o['source_id']), -1):
            out[oid] = ('HISTORY', None)
        elif o.get('valid_until') is not None and o['valid_until'] < evaluation_date:
            out[oid] = ('HISTORY', 'EXPIRED_EVIDENCE')
        else:
            out[oid] = (ELIGIBLE, None)
    return out


def conflicts(observations, states):
    """-> {(series key, as_of): [observation ids]} for every series and date where eligible observations disagree on the exact value (equal values written with
    different exponents are the same value, not a conflict).  Both values are reported; the core never chooses."""
    by = {}
    for oid, o in observations.items():
        if states[oid][0] == ELIGIBLE and 'value' in o:
            by.setdefault((series_key(o), o['as_of']), []).append(oid)
    out = {}
    for k, ids in by.items():
        vals = {V.exact(observations[i]['value']) for i in ids}
        if len(vals) > 1:
            out[k] = sorted(ids)
    return out


def group_conflicts(doc, observations, states):
    """Disagreement inside a pack-declared comparison group: same date, different sources, different exact values."""
    out = []
    for g in doc['comparison_groups']:
        by = {}
        for oid, o in observations.items():
            if states[oid][0] != ELIGIBLE or 'value' not in o:
                continue
            if (o['subject_id'], o['unit'], o['market'], o['observation_class'], o['value_basis']) != (g['subject_id'], g['unit'], g['market'], g['observation_class'],
                                                                                                         g['value_basis']):
                continue
            if o['source_id'] in g['sources']:
                by.setdefault(o['as_of'], []).append(oid)
        for d in sorted(by):
            ids = by[d]
            if len({observations[i]['source_id'] for i in ids}) > 1 and len({V.exact(observations[i]['value']) for i in ids}) > 1:
                out.append({'group_id': g['group_id'], 'as_of': d, 'evidence_ids': sorted(ids)})
    return out


def freshness_for(doc, request_limits, observation_class):
    """-> (limit days or None, where it came from).  The pack's policy limit governs; a request limit is used only where the pack has none for that class; an invalid
    request value is treated as not supplied (there is no default)."""
    for f in doc['freshness_limits']:
        if f['observation_class'] == observation_class:
            return f['days'], 'pack'
    v = (request_limits or {}).get(observation_class)
    if V.is_int(v) and v >= 0:
        return v, 'request'
    return None, None


def _select(observations, states, subject, sel):
    return {oid: o for oid, o in observations.items()
            if o['subject_id'] == subject and 'value' in o and states[oid][0] == ELIGIBLE and all(o[k] == sel[k] for k in sel)}


def _base(sig, subject, cfg, typ):
    return {'signal_id': cfg['signal_id'], 'type': typ, 'vocabulary': Y.VERSIONS['signal_vocabulary'], 'subject_id': subject, 'parameters': cfg['params'],
            'parameter_owner_ref': cfg['parameter_owner_ref'], **sig}


def _na(subject, cfg, typ, reason, **extra):
    return _base({'status': 'NOT_ASSESSED', 'reason': reason, **extra}, subject, cfg, typ)


def movement(doc, observations, states, conf, subject, cfg, typ, sel, evaluation_date, request_limits):
    """LEVEL_MOVEMENT and CONVERSION_MOVEMENT (section 5.3).  Every parameter comes from the pack; a missing one gives PARAMETER_MISSING and nothing is assumed."""
    pr = cfg['params']
    missing = [k for k in ('window_days', 'min_points', 'movement_basis', 'threshold') if pr[k] is None]
    if missing:
        return _na(subject, cfg, typ, 'PARAMETER_MISSING', missing_parameters=missing)
    cand = _select(observations, states, subject, sel)
    series = sorted({series_key(o) for o in cand.values()})
    if not series:
        return _na(subject, cfg, typ, 'NO_EVIDENCE')
    if len(series) > 1:
        return _na(subject, cfg, typ, 'UNIT_MISMATCH', series=[list(s) for s in series])
    key = series[0]
    cls = key[3]
    limit, src = freshness_for(doc, request_limits, cls)
    if limit is None:
        return _na(subject, cfg, typ, 'FRESHNESS_LIMIT_MISSING', evidence_class=cls)
    start_day = V.shift(evaluation_date, -pr['window_days'])
    pts = {oid: o for oid, o in cand.items() if start_day <= o['as_of'] <= evaluation_date}
    dates = sorted({o['as_of'] for o in pts.values()})
    window = {'from': start_day, 'to': evaluation_date, 'days': pr['window_days']}
    if len(dates) < pr['min_points']:
        return _na(subject, cfg, typ, 'INSUFFICIENT_POINTS', window=window, points=len(dates), evidence_class=cls)
    d0, d1 = dates[0], dates[-1]
    if (key, d0) in conf or (key, d1) in conf:
        return _na(subject, cfg, typ, 'CONFLICT_IN_EVIDENCE', window=window, conflicting_dates=[d for d in (d0, d1) if (key, d) in conf], evidence_class=cls)
    s_ids = sorted(i for i, o in pts.items() if o['as_of'] == d0)
    e_ids = sorted(i for i, o in pts.items() if o['as_of'] == d1)
    s_val, e_val = pts[s_ids[0]]['value'], pts[e_ids[0]]['value']
    si, ei, exp = V.align(s_val, e_val)
    d = ei - si
    T = Fraction(pr['threshold']['num'], pr['threshold']['den'])
    age = V.days(d1, evaluation_date)
    common = {'evidence_class': cls, 'value_basis': key[4], 'market': key[1], 'unit': key[2], 'window': window, 'evidence_ids': sorted(pts),
              'start': {'as_of': d0, 'value': s_val, 'evidence_ids': s_ids}, 'end': {'as_of': d1, 'value': e_val, 'evidence_ids': e_ids},
              'movement_basis': pr['movement_basis'], 'threshold': pr['threshold'], 'data_age_days': age,
              'freshness': {'limit_days': limit, 'limit_source': src, 'age_days': age, 'stale': age > limit},
              'basis': {'observations': len(pts), 'distinct_sources': len({o['source_id'] for o in pts.values()}), 'conflicts': 0, 'gaps': 0}}
    if pr['movement_basis'] == 'RELATIVE':
        if si == 0:
            return _na(subject, cfg, typ, 'ZERO_BASE', **common)
        r = Fraction(d, abs(si))
        direction = 'UP' if r >= T else 'DOWN' if r <= -T else 'UNCHANGED'
        ratio = V.ratio_out(r)
    else:
        diff = Fraction(d) * (Fraction(10) ** exp)
        direction = 'UP' if diff >= T else 'DOWN' if diff <= -T else 'UNCHANGED'
        ratio = V.ratio_out(Fraction(d, abs(si))) if si != 0 else None
    return _base({'status': 'ASSESSED', 'reason': None, **common, 'difference': V.decimal_out(d, exp), 'ratio': ratio, 'direction': direction,
                  'crosses_zero': (si < 0 < ei) or (ei < 0 < si)}, subject, cfg, typ)


def event_signal(doc, observations, states, subject, cfg, typ, evaluation_date, request_limits):
    """AVAILABILITY_CHANGE, VARIANT_INTRODUCED, VARIANT_WITHDRAWN: only from event observations the pack maps, within the pack's lookback."""
    if cfg['params']['lookback_days'] is None:
        return _na(subject, cfg, typ, 'PARAMETER_MISSING', missing_parameters=['lookback_days'])
    emap = {e['label']: e for e in doc['event_mapping']}
    start_day = V.shift(evaluation_date, -cfg['params']['lookback_days'])
    evs = sorted(((o['as_of'], oid) for oid, o in observations.items()
                  if o['subject_id'] == subject and 'event_label' in o and states[oid][0] == ELIGIBLE and Y.EVENT_SIGNAL[emap[o['event_label']]['event_class']] == typ
                  and start_day <= o['as_of'] <= evaluation_date))
    if not evs:
        return _na(subject, cfg, typ, 'NO_EVIDENCE', window={'from': start_day, 'to': evaluation_date, 'days': cfg['params']['lookback_days']})
    last = observations[evs[-1][1]]
    cls = last['observation_class']
    limit, src = freshness_for(doc, request_limits, cls)
    if limit is None:
        return _na(subject, cfg, typ, 'FRESHNESS_LIMIT_MISSING', evidence_class=cls)
    age = V.days(last['as_of'], evaluation_date)
    events = [{'as_of': d, 'observation_id': oid, 'label': observations[oid]['event_label'], 'event_class': emap[observations[oid]['event_label']]['event_class'],
               'availability': emap[observations[oid]['event_label']]['availability']} for d, oid in evs]
    return _base({'status': 'ASSESSED', 'reason': None, 'evidence_class': cls, 'evidence_ids': [oid for _, oid in evs], 'events': events,
                  'direction': emap[last['event_label']]['availability'], 'data_age_days': age,
                  'window': {'from': start_day, 'to': evaluation_date, 'days': cfg['params']['lookback_days']},
                  'freshness': {'limit_days': limit, 'limit_source': src, 'age_days': age, 'stale': age > limit},
                  'basis': {'observations': len(evs), 'distinct_sources': len({observations[oid]['source_id'] for _, oid in evs}), 'conflicts': 0, 'gaps': 0}},
                 subject, cfg, typ)


def _requirement(doc, observations, states, conf, subject, req, evaluation_date, request_limits):
    """-> (status 'OK' or a reason code, evidence ids) for one required-evidence declaration."""
    sel = {k: req[k] for k in ('observation_class', 'value_basis', 'market', 'unit') if k in req}
    match = {oid: o for oid, o in observations.items() if o['subject_id'] == subject and all(o[k] == sel[k] for k in sel)}
    if not match:
        return 'NO_EVIDENCE', []
    elig = {oid: o for oid, o in match.items() if states[oid][0] == ELIGIBLE}
    if not elig:
        reasons = {states[oid][1] for oid in match}
        for r in ('LICENCE_EXCLUDED', 'EXPIRED_EVIDENCE', 'OBSERVATION_AFTER_EVALUATION_DATE'):
            if r in reasons:
                return r, sorted(match)
        return 'NO_EVIDENCE', sorted(match)
    limit, _ = freshness_for(doc, request_limits, req['observation_class'])
    if limit is None:
        return 'FRESHNESS_LIMIT_MISSING', sorted(elig)
    latest = max(o['as_of'] for o in elig.values())
    ids = sorted(oid for oid, o in elig.items() if o['as_of'] == latest)
    if any((series_key(elig[i]), latest) in conf for i in ids):
        return 'CONFLICT_IN_EVIDENCE', ids
    if V.days(latest, evaluation_date) > limit:
        return 'STALE_EVIDENCE', ids
    return 'OK', ids


def assess_evidence(doc, observations, subject, evaluation_date, request_limits):
    """The whole evidence view for one subject: states, signals, data-quality signals, gaps, qualification, evidence groups and the uncertainty statement."""
    states = classify(doc, observations, evaluation_date)
    conf = conflicts(observations, states)
    gconf = group_conflicts(doc, observations, states)
    subjects = {s['subject_id']: s for s in doc['vocabulary']['subjects']}
    convs = {c['conversion_id']: c for c in doc['conversions']}
    signals = []
    for cfg in doc['signals']:
        if cfg['type'] == 'LEVEL_MOVEMENT':
            signals.append(movement(doc, observations, states, conf, subject, cfg, cfg['type'], cfg['selector'], evaluation_date, request_limits))
        elif cfg['type'] == 'CONVERSION_MOVEMENT':
            cid = cfg['selector']['conversion_id']
            if cid in subjects[subject]['conversions']:
                cv = convs[cid]
                signals.append(movement(doc, observations, states, conf, cv['subject_id'], cfg, cfg['type'], {'unit': cv['rate_unit'], 'market': cv['market']},
                                        evaluation_date, request_limits))
        else:
            signals.append(event_signal(doc, observations, states, subject, cfg, cfg['type'], evaluation_date, request_limits))
    gaps = []
    for s in signals:
        if s['status'] == 'NOT_ASSESSED':
            gaps.append({'kind': 'signal', 'signal_id': s['signal_id'], 'reason': s['reason']})
    for oid in sorted(states):
        st, why = states[oid]
        if why is not None:
            gaps.append({'kind': 'observation', 'observation_id': oid, 'reason': why})
    for (key, d), ids in sorted(conf.items()):
        gaps.append({'kind': 'conflict', 'series': list(key), 'as_of': d, 'evidence_ids': ids, 'reason': 'CONFLICT_IN_EVIDENCE'})
    for g in gconf:
        gaps.append({'kind': 'group_conflict', 'group_id': g['group_id'], 'as_of': g['as_of'], 'evidence_ids': g['evidence_ids'], 'reason': 'CONFLICT_IN_EVIDENCE'})
    req = []
    for r in doc['required_evidence']:
        st, ids = _requirement(doc, observations, states, conf, subject, r, evaluation_date, request_limits)
        req.append({'evidence_id': r['evidence_id'], 'status': st, 'evidence_ids': ids})
        if st != 'OK':
            gaps.append({'kind': 'required_evidence', 'evidence_id': r['evidence_id'], 'reason': st})
    stale = [{'signal_id': s['signal_id'], 'age_days': s['freshness']['age_days'], 'limit_days': s['freshness']['limit_days']}
             for s in signals if s['status'] == 'ASSESSED' and s['freshness']['stale']]
    stale += [{'evidence_id': r['evidence_id']} for r in req if r['status'] == 'STALE_EVIDENCE']
    for s in signals:
        if s['status'] == 'ASSESSED' and s['freshness']['stale']:
            gaps.append({'kind': 'stale_signal', 'signal_id': s['signal_id'], 'reason': 'STALE_EVIDENCE'})
    if stale:
        signals.append({'signal_id': 'DATA_STALE', 'type': 'DATA_STALE', 'vocabulary': Y.VERSIONS['signal_vocabulary'], 'subject_id': subject, 'status': 'ASSESSED',
                        'reason': None, 'items': stale})
    missing = [r for r in req if r['status'] != 'OK' and r['status'] not in ('STALE_EVIDENCE', 'CONFLICT_IN_EVIDENCE')]
    if missing:
        signals.append({'signal_id': 'DATA_MISSING', 'type': 'DATA_MISSING', 'vocabulary': Y.VERSIONS['signal_vocabulary'], 'subject_id': subject, 'status': 'ASSESSED',
                        'reason': None, 'items': [{'evidence_id': r['evidence_id'], 'reason': r['status']} for r in missing]})
    if conf or gconf:
        signals.append({'signal_id': 'DATA_CONFLICT', 'type': 'DATA_CONFLICT', 'vocabulary': Y.VERSIONS['signal_vocabulary'], 'subject_id': subject, 'status': 'ASSESSED',
                        'reason': None, 'items': [{'series': list(k), 'as_of': d, 'evidence_ids': ids} for (k, d), ids in sorted(conf.items())] + gconf})
    reasons = sorted({r['status'] for r in req if r['status'] != 'OK'})
    qualification = {'status': 'QUALIFIED' if reasons else 'UNQUALIFIED', 'reasons': reasons, 'required_evidence': req}
    groups = {g: [] for g in Y.EVIDENCE_GROUPS}
    usable = 0
    for oid in sorted(observations):
        o = observations[oid]
        st, why = states[oid]
        if st == 'EXCLUDED':
            continue
        limit, _ = freshness_for(doc, request_limits, o['observation_class'])
        age = V.days(o['as_of'], evaluation_date)
        fresh = limit is not None and age <= limit
        conflicting = 'value' in o and (series_key(o), o['as_of']) in conf
        state = 'history' if st == 'HISTORY' else 'conflicting' if conflicting else 'current' if fresh else 'stale' if limit is not None else 'no_freshness_limit'
        if st == ELIGIBLE and fresh and not conflicting:
            usable += 1
        groups[Y.GROUP_OF_CLASS[o['observation_class']]].append({'observation_id': oid, 'subject_id': o['subject_id'], 'observation_class': o['observation_class'],
                                                                  'value_basis': o['value_basis'], 'as_of': o['as_of'], 'age_days': age,
                                                                  'freshness_limit_days': limit, 'state': state, 'reason': why})
    elig_ids = [oid for oid in observations if states[oid][0] == ELIGIBLE]
    uncertainty = {'observations': len(elig_ids), 'distinct_sources': len({observations[i]['source_id'] for i in elig_ids}),
                   'conflicts': len(conf) + len(gconf), 'gaps': len(gaps), 'statement': Y.MOVEMENT_STATEMENT}
    return {'signals': signals, 'gaps': gaps, 'qualification': qualification, 'evidence': groups, 'usable_evidence': usable, 'uncertainty': uncertainty}
