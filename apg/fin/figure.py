"""The figure: one financial number together with everything a reviewer needs to trust it or distrust it.  Blueprint: Section 05 sections 5.4 (view metadata), 8 (forecast
qualification), 13 (reproducibility); PG-PC-AC-04, 15, 16, 20; the auditor's M3 review ("every financial figure can explain ...").

A figure is a plain, JSON-able dict (ints, strings, lists, dicts, None; never a float) so it can be stored, hashed and replayed.  Its state is decided by `finish`,
never by the caller, and can only be degraded:
  authoritative  every input was authoritative, nothing that matters was left out, nothing is unknown or disputed, and the policy is approved
  provisional    a value exists but something was left out, unknown, disputed or unapproved; it says exactly what
  cannot_assess  no honest value can be produced (a needed input or a method decision is missing); the value is None, never zero
Exclusions of kind 'duplicate_delivery' and 'after_cutoff' are by design (a repeat delivery has no effect; a later date is outside the period) and do not degrade a figure;
every other kind of exclusion does."""
from .. import canon

AUTH, PROV, CANT = 'authoritative', 'provisional', 'cannot_assess'
STATES = (AUTH, PROV, CANT)
RANK = {AUTH: 0, PROV: 1, CANT: 2}
BENIGN = ('duplicate_delivery', 'after_cutoff', 'rejected_by_review')
HELD = ('held', 'disputed', 'unknown_value', 'unattributed', 'quarantined', 'unresolved_link', 'not_counted')
EXCLUSION_CLASSES = BENIGN + HELD


class FigureError(ValueError):
    pass


def worst(states):
    states = list(states)
    for s in states:
        if s not in STATES:
            raise FigureError(f'unknown state {s!r}')
    return max(states, key=lambda s: RANK[s]) if states else AUTH


class FigureBuilder:
    def __init__(self, name, view, formula, version, scope, as_of, policy=None):
        self.f = {'name': name, 'view': view, 'formula': formula, 'formula_version': version, 'scope': dict(scope), 'as_of': as_of, 'state': None, 'value': {'cents': None, 'bps': None},
                  'contributed': [], 'applied': {'credits': [], 'duplicates': [], 'revisions': []}, 'excluded': [], 'unknown_inputs': [], 'disputed': [], 'limits': [], 'reasons': [],
                  'policy': {'version': (policy or {}).get('version'), 'approved': bool((policy or {}).get('_approved'))}, 'components': {}, 'classified': {}}
        self._required = {}
        self._force = None

    def contribute(self, ref, revision, amount_cents, role='cost', code=None):
        e = {'ref': ref, 'revision': revision, 'amount_cents': amount_cents, 'role': role}
        if code is not None:
            e['cost_code'] = code
        self.f['contributed'].append(e)

    def credit(self, ref, against, amount_cents):
        self.f['applied']['credits'].append({'ref': ref, 'against': against, 'amount_cents': amount_cents})

    def duplicate(self, ref, of):
        self.f['applied']['duplicates'].append({'ref': ref, 'duplicate_of': of})

    def revision(self, ref, revision, source_revision):
        self.f['applied']['revisions'].append({'ref': ref, 'revision': revision, 'source_revision': source_revision})

    def exclude(self, ref, cls, codes=(), amount_cents=None):
        if cls not in EXCLUSION_CLASSES:
            raise FigureError(f'unknown exclusion class {cls!r}')
        self.f['excluded'].append({'ref': ref, 'class': cls, 'codes': sorted(set(codes)), 'amount_cents': amount_cents})

    def unknown(self, what, reason, decision=''):
        self.f['unknown_inputs'].append({'input': what, 'reason': reason, 'decision': decision})

    def dispute(self, ref, reason):
        self.f['disputed'].append({'ref': ref, 'reason': reason})

    def limit(self, text):
        if text not in self.f['limits']:
            self.f['limits'].append(text)

    def reason(self, code):
        if code not in self.f['reasons']:
            self.f['reasons'].append(code)

    def classify(self, name, data):
        """Detail that is not part of the value but that a reviewer or the movement bridge needs (a breakdown, a separate class of amounts).  JSON-able, no floats."""
        self.f['classified'][name] = data

    def child(self, name, fig, required=True):
        self.f['components'][name] = fig
        self._required[name] = required

    def cannot(self, code, decision=''):
        """The figure cannot be produced.  `code` says why; `decision` names the open decision when the cause is a method that nobody has configured."""
        self.reason(code)
        if decision:
            self.unknown(code, 'method_not_configured', decision)
        self._force = CANT
        return self.finish()

    def finish(self, cents=None, bps=None):
        f = self.f
        if cents is not None and bps is not None:
            raise FigureError('a figure has one value')
        for nm, req in self._required.items():
            c = f['components'][nm]
            if req and c['state'] == CANT and (cents is not None or bps is not None):
                raise FigureError(f'component {nm} cannot be assessed, so the figure cannot have a value')
        for k in ('cents', 'bps'):
            v = cents if k == 'cents' else bps
            if v is not None and (not isinstance(v, int) or isinstance(v, bool)):
                raise FigureError('values are whole numbers (cents or basis points)')
        f['value'] = {'cents': cents, 'bps': bps}
        if self._force == CANT or (cents is None and bps is None):
            state = CANT
            f['value'] = {'cents': None, 'bps': None}
            for nm, c in sorted(f['components'].items()):
                if c['state'] != AUTH:
                    self.reason('COMPONENT_%s:%s' % (c['state'].upper(), nm))
        else:
            state = AUTH
            if any(e['class'] not in BENIGN for e in f['excluded']) or f['unknown_inputs'] or f['disputed'] or not f['policy']['approved']:
                state = PROV
            for nm, c in sorted(f['components'].items()):
                got = PROV if c['state'] == CANT and not self._required[nm] else c['state']
                state = worst([state, got])
                if got != AUTH:
                    self.reason('COMPONENT_%s:%s' % (c['state'].upper(), nm))             # the parent says which part it is waiting on, it does not hide it in a child
            if not f['policy']['approved']:
                self.reason('POLICY_NOT_APPROVED:' + str(f['policy']['version']))
        f['state'] = state
        for k in ('contributed',):
            f[k].sort(key=lambda x: (x['ref'], x['role']))
        f['applied']['credits'].sort(key=lambda x: x['ref'])
        f['applied']['duplicates'].sort(key=lambda x: x['ref'])
        f['applied']['revisions'].sort(key=lambda x: x['ref'])
        f['excluded'].sort(key=lambda x: (x['ref'], x['class']))
        f['unknown_inputs'].sort(key=lambda x: (x['input'], x['reason']))
        f['disputed'].sort(key=lambda x: (x['ref'], x['reason']))
        f['limits'].sort()
        f['reasons'].sort()
        validate_figure(f)
        return f


def validate_figure(f, path='$'):
    """Raises FigureError if a figure breaks the rules above.  Used by the builder, the record store and the tests."""
    if f.get('state') not in STATES:
        raise FigureError(f'{path}: state')
    v = f['value']
    has = v['cents'] is not None or v['bps'] is not None
    if (f['state'] == CANT) == has:
        raise FigureError(f'{path}: cannot_assess means no value and any other state needs one')
    if v['cents'] is not None and v['bps'] is not None:
        raise FigureError(f'{path}: two values')
    for e in f['excluded']:
        if e['class'] not in EXCLUSION_CLASSES:
            raise FigureError(f'{path}: exclusion class')
    degrading = (any(e['class'] not in BENIGN for e in f['excluded']) or f['unknown_inputs'] or f['disputed'] or not f['policy']['approved'])
    if f['state'] == AUTH and degrading:
        raise FigureError(f'{path}: an authoritative figure cannot have exclusions, unknown or disputed inputs or an unapproved policy')
    if f['state'] != AUTH and not (f['reasons'] or f['unknown_inputs'] or f['disputed'] or any(e['class'] not in BENIGN for e in f['excluded'])):
        raise FigureError(f'{path}: a figure that is not authoritative must say why')
    for nm, c in f['components'].items():
        validate_figure(c, f'{path}.{nm}')
        if f['state'] == AUTH and c['state'] != AUTH:
            raise FigureError(f'{path}: authoritative figure with a component that is {c["state"]}')
    canon.canonical(f)                                          # no floats, only JSON types


def explain(f, indent=0):
    """Plain-language lines for a reviewer (also used in the demonstration)."""
    pad = ' ' * indent
    val = f['value']
    shown = 'no value' if f['state'] == CANT else (f"{val['cents'] / 100:,.2f}" if val['cents'] is not None else f"{val['bps'] / 100:.2f}%")
    lines = [f"{pad}{f['name']} [{f['state']}] = {shown}   ({f['view']}, as of {f['as_of']}, {f['formula']} v{f['formula_version']}, policy {f['policy']['version']}{'' if f['policy']['approved'] else ' UNAPPROVED'})"]
    lines.append(f"{pad}  built from {len(f['contributed'])} record(s); credits applied {len(f['applied']['credits'])}; duplicates ignored {len(f['applied']['duplicates'])}; revisions noted {len(f['applied']['revisions'])}")
    for e in f['excluded']:
        lines.append(f"{pad}  left out [{e['class']}] {e['ref']}: {', '.join(e['codes']) or '-'}")
    for u in f['unknown_inputs']:
        lines.append(f"{pad}  unknown: {u['input']} ({u['reason']}){' - decision ' + u['decision'] if u['decision'] else ''}")
    for d in f['disputed']:
        lines.append(f"{pad}  disputed: {d['ref']} ({d['reason']})")
    for r in f['reasons']:
        lines.append(f"{pad}  reason: {r}")
    for nm, c in sorted(f['components'].items()):
        lines.extend(explain(c, indent + 4))
    return lines
