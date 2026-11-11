"""The adapter side of the observation-feed flow (MIE1_SPEC section 10.4; MIE1_FEED_FLOW.csv FF-01 to FF-09; MIE-R-45, 46, 66).
  1 an ingestion driver decides when to retrieve (who runs it, and where, is the host's: MIE-OQ-25);
  2 it calls a feed adapter, the only component that invokes an ObservationSourcePort and knows a feed's protocol;
  3 the adapter maps what it retrieved to observation messages (any check it makes is a convenience; the core trusts none of it);
  4 the driver submits the batch, with its verified context and the pack pin, to submit_observations; the batch names no tenant;
  5 the core alone validates every item and returns a receipt per item;  6 the driver acts on the receipts (a retried batch is a duplicate, a no-op).
A feed failure stays here: no core operation is invoked and no core state changes.  It reaches the core only as a missing observation, which assessment lists as a gap.
None of this is the core: the core never imports this module and never calls a feed."""


class FeedUnavailable(Exception):
    """The feed could not be reached, answered malformed data, or answered nothing.  Adapter-side only; there is no core error for it."""


class ObservationSourcePort:
    """PT-06, adapter-side (not a core port).  Same invariants as the M6 MarketFeedPort (MF-01..MF-13) for what it supplies."""
    def fetch(self, tenant, series_ref, evaluation_date):
        raise NotImplementedError


class RefSource(ObservationSourcePort):
    """A test double: series loaded by the test, a switch to fail, and a log of every call (so a test can show the core never calls it)."""
    def __init__(self):
        self.series, self.calls, self.mode = {}, [], None

    def load(self, tenant, series_ref, rows):
        self.series[(tenant, series_ref)] = [dict(r) for r in rows]

    def fetch(self, tenant, series_ref, evaluation_date):
        self.calls.append((tenant, series_ref, evaluation_date))
        if self.mode == 'down':
            raise FeedUnavailable('unreachable')
        if self.mode == 'malformed':
            return 'not a list'
        if self.mode == 'empty':
            return []
        return [dict(r) for r in self.series.get((tenant, series_ref), []) if r.get('as_of', '') <= evaluation_date]


class FeedAdapter:
    """Maps a feed's rows to observation messages using a mapping the integrator declares: {series_ref: fixed attributes}.  Rows give as_of, retrieved_at and value or
    event_label (and may assert a licence status, which is passed on as evidence only: FL-08)."""
    def __init__(self, source, mapping):
        self.source, self.mapping = source, mapping

    def retrieve(self, tenant, series_ref, evaluation_date):
        rows = self.source.fetch(tenant, series_ref, evaluation_date)
        if not isinstance(rows, list):
            raise FeedUnavailable('malformed answer')
        fixed = self.mapping[series_ref]
        out = []
        for r in rows:
            m = dict(fixed)
            for k in ('as_of', 'retrieved_at', 'value', 'event_label', 'valid_until', 'revision', 'supersedes'):
                if k in r:
                    m[k] = r[k]
            if 'licence_status' in r:
                m['feed_licence_status'] = r['licence_status']
            m['adapter_notes'] = {'series_ref': series_ref, 'pre_validated': True}
            out.append(m)
        return out


class IngestionDriver:
    """Runs the flow for a set of series.  Returns what happened per series: the core's receipts, or the adapter-side feed failure (with no core call)."""
    def __init__(self, engine, adapter):
        self.engine, self.adapter = engine, adapter

    def run(self, ctx, tenant_for_feed, pin, series_refs, evaluation_date):
        report = {}
        for ref in series_refs:
            try:
                batch = self.adapter.retrieve(tenant_for_feed, ref, evaluation_date)
            except FeedUnavailable as e:
                report[ref] = {'feed_failure': str(e), 'submitted': False}
                continue
            if not batch:
                report[ref] = {'feed_failure': 'empty', 'submitted': False}
                continue
            report[ref] = {'submitted': True, 'result': self.engine.submit_observations(ctx, pin, batch)}
        return report
