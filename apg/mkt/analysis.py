"""The M6 analysis for one scope, built lazily from pinned records.  Blueprint: Section 08 sections 3 (procurement domains), 8, 11, 13, 14 (every market-dependent finding keeps source, observation and
retrieval dates, validity, currency, scope and method).

`Analysis` holds NO state beyond memoised results of pure functions of (pinned facts, policy, specification register, as-of day, authorised projects).  The rules ask it for what they need; the
detection run asks it for the stored `analyses` block (requirements with coverage, rankings, scenarios, opportunities, supplier profiles, portfolio opportunities, evidence register) and for the
`events` list that M7 will connect.  A policy value that is missing stops only the analysis that needs it, and says which (MissingParam)."""
from . import common as C, compare as CP, demand as DM, fresh as FR, opportunity as OP, purchasing as PU, scenarios as SC, suppliers as SU


class Analysis:
    def __init__(self, F, mp, spec, as_of, project=None, authorised=None):
        self.F, self.mp, self.spec, self.as_of, self.project = F, mp, spec, as_of, project
        self.authorised = authorised if authorised is not None else ({project} if project else None)
        self.ctx = CP.Ctx(F, mp, spec, as_of)
        self._m = {}

    def _memo(self, key, fn):
        if key not in self._m:
            self._m[key] = fn()
        return self._m[key]

    # ------------------------------------------------------------------ requirements and what covers them
    def requirements(self):
        return self._memo('reqs', lambda: CP.requirements(self.ctx, self.authorised))

    def demands(self):
        return [r for r in self.requirements() if r['kind'] == 'demand']

    def coverage(self, req):
        return self._memo(('cov', req['id']), lambda: DM.coverage(self.ctx, req))

    def ranking(self, req, decision, qty=None, with_index=False):
        return self._memo(('rank', req['id'], decision, qty, with_index), lambda: CP.rank(self.ctx, req, decision, qty, with_index))

    def last_paid(self, req):
        return self._memo(('lp', req['id']), lambda: CP.last_paid(self.ctx, req))

    def scenarios(self, req):
        return self._memo(('scn', req['id']), lambda: SC.build(self.ctx, req, self.coverage(req)))

    def opportunities(self):
        def go():
            out = []
            for r in self.demands():
                out.extend(OP.discover(self.ctx, r, self.coverage(r)))
            return out
        return self._memo('opps', go)

    def duplicates(self):
        def go():
            groups = DM.duplicate_groups(self.ctx)
            return [g for g in groups if self.authorised is None or g['project'] in self.authorised]
        return self._memo('dups', go)

    def suppliers(self):
        return self._memo('sup', lambda: SU.profiles(self.ctx, self.authorised))

    def portfolio(self):
        return self._memo('port', lambda: PU.opportunities(self.ctx, self.authorised if self.authorised is not None else set()))

    # ------------------------------------------------------------------ evidence register
    def watched_materials(self):
        """Materials in the policy's watch list plus the materials of the demand in scope."""
        return sorted(set(self.mp['scope']['watch_materials']) | {r['material'] for r in self.demands()})

    def evidence_register(self):
        """Per watched material: the state of its quotes and of its index series under the benchmark decision."""
        def go():
            th = self.mp['freshness']['benchmark']
            out = {}
            for m in self.watched_materials():
                qs = [FR.quote_state(q, self.as_of, th) for k, q in sorted(self.ctx.quotes.items()) if q['ok'] and q['material'] == m]
                out[m] = {'quotes': qs, 'index': FR.index_state(self.F, m, self.as_of, th)}
            return out
        return self._memo('evreg', go)

    # ------------------------------------------------------------------ stored analyses block and events
    def block(self):
        """The reproducible analyses block stored with the run.  Only analyses whose policy values exist are included; the others are listed under `not_assessed`."""
        def go():
            out = {'requirements': {}, 'not_assessed': []}
            for r in self.requirements():
                ent = {'requirement': {k: v for k, v in r.items() if k not in ('sources',)}}
                if r['kind'] == 'demand':
                    for name, fn in (('coverage', lambda: self.coverage(r)), ('ranking', lambda: self.ranking(r, 'quote_ranking', self.coverage(r).get('uncovered_micro') or None)),
                                     ('scenarios', lambda: self.scenarios(r)), ('reference', lambda: self.last_paid(r))):
                        try:
                            ent[name] = _plain(fn())
                        except C.MissingParam as e:
                            out['not_assessed'].append({'subject': r['id'], 'analysis': name, 'missing_parameter': str(e)})
                else:
                    try:
                        ent['ranking'] = _plain(self.ranking(r, 'quote_ranking'))
                    except C.MissingParam as e:
                        out['not_assessed'].append({'subject': r['id'], 'analysis': 'ranking', 'missing_parameter': str(e)})
                out['requirements'][r['id']] = ent
            for name, fn in (('opportunities', self.opportunities), ('duplicates', self.duplicates), ('suppliers', self.suppliers), ('evidence_register', self.evidence_register)):
                try:
                    out[name] = _plain(fn())
                except C.MissingParam as e:
                    out['not_assessed'].append({'subject': 'scope', 'analysis': name, 'missing_parameter': str(e)})
            if self.project is None:
                try:
                    pf, boundary = self.portfolio()
                    out['portfolio'] = _plain(pf)
                    out['portfolio_boundary_applied'] = boundary
                except C.MissingParam as e:
                    out['not_assessed'].append({'subject': 'scope', 'analysis': 'portfolio', 'missing_parameter': str(e)})
            return out
        return self._memo('block', go)


def _plain(x):
    """Drop what a stored analysis must not carry twice: the full offer evaluations inside opportunities are kept once, as given; views are plain data already."""
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    return x
