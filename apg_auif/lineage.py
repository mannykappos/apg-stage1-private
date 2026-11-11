"""Lineage checks (M8 acceptance: "no record, figure input or signal evidence lacks lineage").

  record_problems(payload)      a stored source record: its provenance is complete AUIF lineage, the chain is one AUIF can reconstruct, and (for a quarantined conflict
                                marker) every contender carries the same
  store_problems(scoped)        every revision of every source record, and every reject, duplicate and stale delivery the AUIF path recorded
  trace_run(scoped, run)        every input a stored calculation or detection run pinned: a source record (its pinned revision has lineage), a reconciliation state (the
                                record it describes has lineage at every revision), or configuration (an approved policy record: not source data, listed separately);
                                anything else is UNTRACED
  trace_signals(scoped, result) every evidence reference of every signal of a detection result, the same way
Nothing is inferred: a missing field, an empty value or an unknown kind is a problem."""
from . import layout
from .intake import LINEAGE_FIELDS

CONFIG_KINDS = ('fin_policy', 'det_policy')
DERIVED_KINDS = ('recon_state',)


def source_kinds(root):
    from .definitions import load_templates
    t = load_templates(root)
    return tuple(t[e[1]]['target_entity'] for e in layout.ENTITIES)


def _prov_problems(prov, where):
    out = []
    if not isinstance(prov, dict) or prov.get('path') != 'auif':
        return ['%s: provenance is not AUIF lineage' % where]
    for f in LINEAGE_FIELDS:
        if prov.get(f) in (None, '', [], {}):
            out.append('%s: lineage field %s is missing' % (where, f))
    if 'effective_at' not in prov or (prov.get('effective_at') is None and not str(prov.get('effective_time_basis', '')).startswith(('none:', 'unknown:'))):
        out.append('%s: no effective time and no stated reason' % where)
    if prov.get('validation_state') not in (None, 'VALID'):
        out.append('%s: validation state %s' % (where, prov.get('validation_state')))
    try:
        from auif.canonical import verify_chain
        pr = verify_chain(prov.get('provenance_chain') or [])
    except Exception as e:                                         # an unreadable chain is a problem, not an exception
        pr = ['chain unreadable: %s' % type(e).__name__]
    out += ['%s: %s' % (where, p) for p in pr]
    return out


def record_problems(payload, where='record'):
    if payload.get('conflict'):
        cons = payload['conflict'].get('contenders') or []
        return (['%s: a conflict marker with no contenders' % where] if not cons else []) + \
            [p for i, c in enumerate(cons) for p in _prov_problems(c.get('provenance'), '%s contender %d' % (where, i))]
    return _prov_problems(payload.get('provenance'), where)


def store_problems(scoped, kinds):
    out, n = [], 0
    for kind in kinds:
        for r in scoped.query(kind):
            for h in scoped.history(kind, r.key):
                n += 1
                out += record_problems(h.payload, '%s/%s@%d' % (kind, r.key, h.revision))
    for kind in ('ingest_reject', 'ingest_duplicate', 'ingest_stale'):
        for r in scoped.query(kind):
            n += 1
            out += _prov_problems(r.payload.get('provenance'), '%s/%s' % (kind, r.key))
    return out, n


def _trace(scoped, kind, key, revision, kinds, where):
    if kind in CONFIG_KINDS:
        return [], 'config'
    if kind in DERIVED_KINDS:
        sk, _, sid = key.partition('/')
        if sk not in kinds or scoped.get(sk, sid) is None:
            return ['%s: %s/%s describes no stored source record' % (where, kind, key)], 'derived'
        probs = []
        for h in scoped.history(sk, sid):
            probs += record_problems(h.payload, '%s -> %s/%s@%d' % (where, sk, sid, h.revision))
        return probs, 'derived'
    if kind in kinds:
        rec = scoped.get(kind, key, revision)
        if rec is None:
            return ['%s: %s/%s@%s is not stored' % (where, kind, key, revision)], 'source'
        return record_problems(rec.payload, '%s -> %s/%s@%s' % (where, kind, key, revision)), 'source'
    return ['%s: input kind %s is UNTRACED' % (where, kind)], 'untraced'


def trace_run(scoped, run, kinds):
    """-> (problems, {'source': n, 'derived': n, 'config': n, 'untraced': n})."""
    probs, count = [], {'source': 0, 'derived': 0, 'config': 0, 'untraced': 0}
    for i in run['inputs']:
        p, cls = _trace(scoped, i['kind'], i['key'], i['revision'], kinds, 'run %s input' % run['run_key'][:12])
        probs += p
        count[cls] += 1
    return probs, count


def trace_signals(scoped, result, kinds):
    probs, n = [], 0
    for s in result.get('signals', []):
        for e in s.get('evidence', []):
            n += 1
            kind, _, key = str(e.get('ref', '')).partition('/')
            p, _ = _trace(scoped, kind, key, e.get('revision'), kinds, 'signal %s evidence' % s.get('identity'))
            probs += p
        if not s.get('evidence'):
            probs.append('signal %s has no evidence' % s.get('identity'))
    return probs, n
