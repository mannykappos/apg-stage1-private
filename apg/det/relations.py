"""Relationships between findings and the groups whose money must not be added together.  Blueprint: Section 06 sections 5.4 (related findings are not independent losses), 9
(link symptoms to a common cause only as a hypothesis unless evidence supports it; prevent portfolio aggregation from summing overlapping exposures), PG-AI-AC-10, 11.

Two findings are in the same OVERLAP COMPONENT when any of these holds:
  * their signals name the same overlap group (for example two delay events on one activity);
  * they rest on at least one of the same stored records (a budget overrun and an over-invoiced order that contains one of the overrun's own invoices);
  * a person linked them as 'financial_overlap'.
That is deliberately wide: sharing a record does NOT prove the amounts overlap, only that they MIGHT, so the safe consequence is drawn: inside a component the amounts are reported as a RANGE (the
largest single amount up to the plain sum), never as a single total.  A 'shared_root_cause_hypothesis' link is a hypothesis; it never merges or sums anything."""
POLICY_REF_PREFIXES = ('det_policy/', 'fin_policy/', 'mkt_policy/', 'mkt_spec/')
EXCLUDED_STATUSES = ('dismissed', 'superseded')


def _find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def components(findings):
    """-> {finding id: component id}.  `findings`: finding payloads."""
    parent = {f['finding_id']: f['finding_id'] for f in findings}

    def union(a, b):
        ra, rb = _find(parent, a), _find(parent, b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    by_group, by_ref = {}, {}
    for f in findings:
        g = f['signal'].get('overlap_group')
        if g:
            by_group.setdefault(g, []).append(f['finding_id'])
        for e in f['signal']['evidence']:
            if not e['ref'].startswith(POLICY_REF_PREFIXES):
                by_ref.setdefault(e['ref'], set()).add(f['finding_id'])
        for r in f['relations']:
            if r['kind'] == 'financial_overlap' and r['with'] in parent:
                union(f['finding_id'], r['with'])
    for ids in list(by_group.values()) + [sorted(v) for v in by_ref.values()]:
        for x in ids[1:]:
            union(ids[0], x)
    return {fid: _find(parent, fid) for fid in parent}


def related(findings):
    """-> {finding id: [{'with', 'because'}]} for display: shared overlap group, shared record, or a person's link."""
    out = {f['finding_id']: [] for f in findings}
    idx = {f['finding_id']: f for f in findings}
    ids = sorted(idx)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            fa, fb = idx[a], idx[b]
            why = []
            if fa['signal'].get('overlap_group') and fa['signal']['overlap_group'] == fb['signal'].get('overlap_group'):
                why.append('overlap_group:' + fa['signal']['overlap_group'])
            sh = sorted({e['ref'] for e in fa['signal']['evidence'] if not e['ref'].startswith(POLICY_REF_PREFIXES)} & {e['ref'] for e in fb['signal']['evidence']})
            if sh:
                why.append('shared_records:' + ','.join(sh[:3]) + ('...' if len(sh) > 3 else ''))
            for r in fa['relations']:
                if r['with'] == b:
                    why.append(('confirmed ' if r['confirmed'] else 'suspected ') + r['kind'])
            if why:
                out[a].append({'with': b, 'because': why})
                out[b].append({'with': a, 'because': why})
    return out
