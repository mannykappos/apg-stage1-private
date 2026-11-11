"""DELIBERATELY BROKEN MarketFeedPort and ExtractionRuntimePort implementations.  They exist only to prove the M6 contract suites have teeth: each fault must make at least the listed cases fail.
Never use these for anything else.   FAULTS maps id -> (description, suite, factory, expected failing case ids)."""
import hashlib
from .. import canon, tenancy
from ..reference_impl import _need
from ..ingest import documents as DOC
from . import reference_m6 as R
from .ports_m6 import DocumentInvalid, MAX_DOCUMENT_BYTES, MEDIA_TYPES


class _Feed(R.InMemoryMarketFeed):
    """Re-implements fetch/freshness with switches; the switches name the fault."""
    K = frozenset()

    def _auth(self, ctx):
        if 'no_auth' not in self.K:
            _need(self.provider, ctx)

    def _get(self, ctx, series_id):
        if 'cross_tenant' in self.K:
            for (t, sid), s in self._series.items():
                if sid == series_id:
                    return s
        if 'unknown_empty' in self.K and (ctx.tenant_id, series_id) not in self._series:
            return {'licence': {'series_id': series_id, 'status': 'licensed', 'terms_ref': '', 'checked_at': ''}, 'obs': []}
        return super()._get(ctx, series_id)

    def _licensed(self, s):
        st = s['licence']['status']
        if 'ignore_licence' in self.K or ('unknown_ok' in self.K and st == 'unknown'):
            return
        super()._licensed(s)

    def _state(self, obs, as_of, max_age):
        f = R.freshness_of(obs, as_of, max_age)
        if 'boundary' in self.K and f['state'] == 'fresh' and f['age_days'] == max_age:
            f['state'] = 'stale'
        if 'hide_stale' in self.K and f['state'] == 'stale':
            f['state'] = 'fresh'
        return f

    def _check(self, as_of, max_age):
        R.iso(as_of, 'as_of')
        if max_age is None and 'default_age' in self.K:
            return 45
        return R.limit(max_age)

    def licence_status(self, ctx, series_id):
        self._auth(ctx)
        return canon.deep_copy(self._get(ctx, series_id)['licence'])

    def fetch(self, ctx, series_id, as_of, max_age_days):
        self._auth(ctx)
        max_age_days = self._check(as_of, max_age_days)
        s = self._get(ctx, series_id)
        self._licensed(s)
        good, rejected = [], 0
        for o in s['obs']:
            if R.good_observation(o) or ('floats' in self.K and isinstance(o, dict) and isinstance(o.get('value'), float) and R.good_observation(dict(o, value=1))):
                good.append(o)
            else:
                rejected += 1
        if 'rejected_not_counted' in self.K:
            rejected = 0
        pool = good if 'future' in self.K else [x for x in good if x['obs_date'] <= as_of]
        seen, out, conflicts = {}, [], set()
        for o in sorted(pool, key=lambda x: (x['obs_date'], x['obs_id'])):
            prior = seen.get(o['obs_date'])
            if prior is not None:
                if prior['value'] == o['value'] and prior['unit'] == o['unit']:
                    continue
                if 'drop_conflicts' in self.K:
                    continue
                conflicts.add(o['obs_date'])
            seen.setdefault(o['obs_date'], o)
            out.append(o)
        if 'fill' in self.K and not [o for o in out if o['obs_date'] <= as_of] and good:
            out = [min(good, key=lambda x: x['obs_date'])]
        res = {'series_id': series_id, 'as_of': as_of, 'observations': out, 'rejected': rejected, 'conflicting_dates': sorted(conflicts), 'freshness': self._state(out, as_of, max_age_days)}
        if 'fill' in self.K and res['freshness']['state'] == 'unavailable':
            pass
        if 'fill' in self.K and out and out[0]['obs_date'] > as_of:
            res['freshness'] = {'state': 'fresh', 'as_of': as_of, 'latest_obs_date': out[0]['obs_date'], 'age_days': 0, 'max_age_days': max_age_days}
        return res if 'shared' in self.K else canon.deep_copy(res)

    def freshness(self, ctx, series_id, as_of, max_age_days):
        self._auth(ctx)
        max_age_days = self._check(as_of, max_age_days)
        s = self._get(ctx, series_id)
        self._licensed(s)
        obs = [o for o in s['obs'] if R.good_observation(o)]
        if 'future' in self.K:
            obs = [dict(o, obs_date=min(o['obs_date'], as_of)) for o in obs]
        return self._state(obs, as_of, max_age_days)

    def _contract_load_series(self, tenant_id, series_id, observations, licence='licensed', terms_ref='SYNTHETIC-TERMS'):
        super()._contract_load_series(tenant_id, series_id, observations, licence, terms_ref)
        if 'shared' in self.K:
            self._series[(tenant_id, series_id)]['obs'] = [o for o in self._series[(tenant_id, series_id)]['obs']]


def _feed(*knobs):
    return R.feed_env(type('FaultyFeed', (_Feed,), {'K': frozenset(knobs)}))


class _SharedStore(_Feed):
    """returns the stored observation objects themselves"""
    K = frozenset({'shared'})

    def fetch(self, ctx, series_id, as_of, max_age_days):
        r = super().fetch(ctx, series_id, as_of, max_age_days)
        s = self._series[(ctx.tenant_id, series_id)]['obs']
        ids = {o['obs_id']: o for o in s}
        r['observations'] = [ids.get(o['obs_id'], o) for o in r['observations']]
        return r

    def licence_status(self, ctx, series_id):
        self._auth(ctx)
        return self._get(ctx, series_id)['licence']


class _Ext(R.StandInExtractor):
    K = frozenset()

    def __init__(self, provider, clock):
        super().__init__(provider, clock)
        self._n = 0
        self._cache = {}

    def extract(self, ctx, document):
        K = self.K
        if 'no_auth' not in K:
            _need(self.provider, ctx)
        if not isinstance(document, dict):
            raise DocumentInvalid('a document is a dict')
        if 'trust_tenant' not in K:
            tenancy.screen_payload(ctx, {k: v for k, v in document.items() if k != 'content'})
        if set(document) != {'doc_id', 'sha256', 'media_type', 'content'} or not isinstance(document['doc_id'], str) or not document['doc_id']:
            raise DocumentInvalid('shape')
        data = document['content']
        if not isinstance(data, (bytes, bytearray)) or (len(data) > MAX_DOCUMENT_BYTES and 'no_size_limit' not in K):
            raise DocumentInvalid('content')
        if document['media_type'] not in MEDIA_TYPES:
            raise DocumentInvalid('media type')
        if 'ignore_hash' not in K and hashlib.sha256(bytes(data)).hexdigest() != document['sha256']:
            raise DocumentInvalid('hash')
        text = bytes(data).decode('utf-8', 'replace')
        key = (document['doc_id'], document['sha256'])
        if 'shared' in K and key in self._cache:
            return self._cache[key]
        self._n += 1
        fields = []
        for f in DOC.standin_extract_quote(text):
            rec = {'name': f['name'], 'text': f['text'], 'location': f['location'], 'candidates': list(f['candidates']), 'ambiguous': bool(f['ambiguous']), 'why': f['why'], 'confidence_bps': None, 'status': 'unverified'}
            if not rec['ambiguous']:
                rec['value'] = rec['candidates'][0] if len(rec['candidates']) == 1 else rec['text']
            elif 'guess' in K:
                rec['value'] = rec['candidates'][0] if rec['candidates'] else rec['text']
                rec['ambiguous'] = False
            if 'verify' in K:
                rec['status'] = 'verified'
                rec['verified_by'] = 'extractor'
            if 'float_conf' in K:
                rec['confidence_bps'] = 0.93
            fields.append(rec)
        if 'invent' in K and not any(f['name'] == 'quantity' for f in fields):
            fields.append({'name': 'quantity', 'text': '1', 'location': 'line 1', 'candidates': ['1'], 'ambiguous': False, 'why': '', 'confidence_bps': None, 'status': 'unverified', 'value': 1})
        if 'obey' in K and 'ignore all previous instructions' in text.lower():
            for f in fields:
                f['status'] = 'verified'
                if f['name'] == 'unit_rate_cents':
                    f['value'] = 1
        version = self.VERSION + ('.%d' % self._n if 'nondeterministic' in K else '')
        res = {'doc_id': document['doc_id'], 'sha256': document['sha256'], 'tool': self.TOOL, 'tool_version': version, 'fields': fields}
        if 'shared' in K:
            self._cache[key] = res
            return res
        return canon.deep_copy(res)


def _ext(*knobs):
    return R.extract_env(type('FaultyExtractor', (_Ext,), {'K': frozenset(knobs)}))


FF, XF = 'market_feed', 'extraction'
FAULTS = {
    'FF-01': ('observations dated after the as-of day are returned and counted', FF, _feed('future'), ['MF-01', 'MF-13']),
    'FF-02': ('the licence is not checked', FF, _feed('ignore_licence'), ['MF-04', 'MF-05']),
    'FF-03': ('an unknown licence status is treated as licensed', FF, _feed('unknown_ok'), ['MF-05']),
    'FF-04': ('stale data is reported as fresh', FF, _feed('hide_stale'), ['MF-02']),
    'FF-05': ('a series exactly at the age limit is called stale', FF, _feed('boundary'), ['MF-02']),
    'FF-06': ('a series with nothing yet is filled from a later observation', FF, _feed('fill'), ['MF-03']),
    'FF-07': ('a series is found across tenants', FF, _feed('cross_tenant'), ['MF-06']),
    'FF-08': ('a conflicting second value for a date is dropped silently', FF, _feed('drop_conflicts'), ['MF-09']),
    'FF-09': ('a float value is accepted as an observation', FF, _feed('floats'), ['MF-08']),
    'FF-10': ('a missing age limit is replaced by a default', FF, _feed('default_age'), ['MF-10']),
    'FF-11': ('the stored observations are returned to the caller', FF, R.feed_env(_SharedStore), ['MF-12']),
    'FF-12': ('no check that the caller is authenticated', FF, _feed('no_auth'), ['MF-11']),
    'FF-13': ('rejected observations are not counted', FF, _feed('rejected_not_counted'), ['MF-08']),
    'FF-14': ('an unknown series is answered as an empty, licensed series', FF, _feed('unknown_empty'), ['MF-07']),
    'XF-01': ('an ambiguous reading is resolved by guessing', XF, _ext('guess'), ['EX-02']),
    'XF-02': ('extracted fields are marked verified', XF, _ext('verify'), ['EX-01', 'EX-03']),
    'XF-03': ('a missing field is invented', XF, _ext('invent'), ['EX-04']),
    'XF-04': ('the result differs between calls', XF, _ext('nondeterministic'), ['EX-07']),
    'XF-05': ('an instruction written in the document is followed', XF, _ext('obey'), ['EX-05']),
    'XF-06': ('the document hash is not checked', XF, _ext('ignore_hash'), ['EX-06']),
    'XF-07': ('confidence is a float', XF, _ext('float_conf'), ['EX-10']),
    'XF-08': ('a tenant named in the document is trusted', XF, _ext('trust_tenant'), ['EX-08']),
    'XF-09': ('a stored result is returned to the caller', XF, _ext('shared'), ['EX-11']),
    'XF-10': ('no check that the caller is authenticated', XF, _ext('no_auth'), ['EX-09']),
    'XF-11': ('over-size documents are accepted', XF, _ext('no_size_limit'), ['EX-06']),
}
