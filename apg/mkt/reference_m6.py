"""In-memory reference MarketFeedPort and ExtractionRuntimePort (TEST DOUBLES that pass the EDR-09 and EDR-08 contracts) and the factories that build the contract environments around them.
The feed holds only series that a test loads: it connects to nothing and names no provider.  The extractor wraps the M3 stand-in TEXT parser (apg/ingest/documents.py); it is not an extraction
product and was not run on any real PDF, scan or e-mail."""
import copy, dataclasses, datetime, hashlib
from .. import canon, tenancy
from ..ports import PayloadInvalid
from ..reference_impl import FakeClock, StaticContextProvider, _need
from ..ingest import documents as DOC
from .ports_m6 import (DocumentInvalid, ExtractionRuntimePort, LicenceRefused, MarketFeedPort, MAX_DOCUMENT_BYTES, MEDIA_TYPES, ObservationInvalid, REQUIRED_TEXT, SeriesNotFound, LICENCE_STATES)


@dataclasses.dataclass
class FeedEnv:
    provider: object
    feed: object
    advance: object


@dataclasses.dataclass
class ExtractEnv:
    provider: object
    extractor: object
    advance: object


def iso(v, what='date'):
    if not isinstance(v, str) or len(v) != 10:
        raise PayloadInvalid(f'{what} must be an ISO date')
    try:
        if datetime.date.fromisoformat(v).isoformat() != v:
            raise ValueError
    except ValueError:
        raise PayloadInvalid(f'{what} must be an ISO date')
    return v


def limit(v):
    if not isinstance(v, int) or isinstance(v, bool) or v < 0:
        raise PayloadInvalid('max_age_days must be a non-negative integer supplied by the caller')
    return v


def good_observation(o):
    if not isinstance(o, dict):
        return False
    try:
        iso(o.get('obs_date'))
    except PayloadInvalid:
        return False
    v = o.get('value')
    if not isinstance(v, int) or isinstance(v, bool):
        return False
    return all(isinstance(o.get(k), str) and o[k].strip() for k in REQUIRED_TEXT) and isinstance(o.get('obs_id'), str) and bool(o['obs_id'])


def days(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


def freshness_of(obs, as_of, max_age):
    dated = [o['obs_date'] for o in obs if o['obs_date'] <= as_of]
    if not dated:
        return {'state': 'unavailable', 'as_of': as_of, 'latest_obs_date': None, 'age_days': None, 'max_age_days': max_age}
    latest = max(dated)
    age = days(latest, as_of)
    return {'state': 'stale' if age > max_age else 'fresh', 'as_of': as_of, 'latest_obs_date': latest, 'age_days': age, 'max_age_days': max_age}


class InMemoryMarketFeed(MarketFeedPort):
    def __init__(self, provider, clock):
        self.provider, self.clock = provider, clock
        self._series = {}

    def _get(self, ctx, series_id):
        s = self._series.get((ctx.tenant_id, series_id))
        if s is None:
            raise SeriesNotFound('no such series')
        return s

    def _licensed(self, s):
        if s['licence']['status'] != 'licensed':
            raise LicenceRefused('series is %s for this tenant' % s['licence']['status'])

    def licence_status(self, ctx, series_id):
        _need(self.provider, ctx)
        return canon.deep_copy(self._get(ctx, series_id)['licence'])

    def fetch(self, ctx, series_id, as_of, max_age_days):
        _need(self.provider, ctx)
        iso(as_of, 'as_of')
        limit(max_age_days)
        s = self._get(ctx, series_id)
        self._licensed(s)
        good, rejected = [], 0
        for o in s['obs']:
            if good_observation(o):
                good.append(o)
            else:
                rejected += 1
        seen, out, conflicts = {}, [], set()
        for o in sorted((x for x in good if x['obs_date'] <= as_of), key=lambda x: (x['obs_date'], x['obs_id'])):
            prior = seen.get(o['obs_date'])
            if prior is not None:
                if prior['value'] == o['value'] and prior['unit'] == o['unit']:
                    continue                                                       # an exact repeat is one observation
                conflicts.add(o['obs_date'])
            seen.setdefault(o['obs_date'], o)
            out.append(o)
        return canon.deep_copy({'series_id': series_id, 'as_of': as_of, 'observations': out, 'rejected': rejected, 'conflicting_dates': sorted(conflicts), 'freshness': freshness_of(out, as_of, max_age_days)})

    def freshness(self, ctx, series_id, as_of, max_age_days):
        _need(self.provider, ctx)
        iso(as_of, 'as_of')
        limit(max_age_days)
        s = self._get(ctx, series_id)
        self._licensed(s)
        return freshness_of([o for o in s['obs'] if good_observation(o)], as_of, max_age_days)

    def _contract_load_series(self, tenant_id, series_id, observations, licence='licensed', terms_ref='SYNTHETIC-TERMS'):
        if licence not in LICENCE_STATES:
            raise ObservationInvalid('licence state')
        self._series[(tenant_id, series_id)] = {'licence': {'series_id': series_id, 'status': licence, 'terms_ref': terms_ref, 'checked_at': self.clock.now()}, 'obs': copy.deepcopy(list(observations))}           # raw: a test hook must be able to load invalid observations


class StandInExtractor(ExtractionRuntimePort):
    TOOL, VERSION = DOC.STANDIN_TOOL, '1'

    def __init__(self, provider, clock):
        self.provider, self.clock = provider, clock

    def extract(self, ctx, document):
        _need(self.provider, ctx)
        if not isinstance(document, dict):
            raise DocumentInvalid('a document is a dict')
        tenancy.screen_payload(ctx, {k: v for k, v in document.items() if k != 'content'})
        if set(document) != {'doc_id', 'sha256', 'media_type', 'content'} or not isinstance(document['doc_id'], str) or not document['doc_id']:
            raise DocumentInvalid('a document has exactly doc_id, sha256, media_type and content')
        data = document['content']
        if not isinstance(data, (bytes, bytearray)) or len(data) > MAX_DOCUMENT_BYTES:
            raise DocumentInvalid('content must be bytes within the size limit')
        if document['media_type'] not in MEDIA_TYPES:
            raise DocumentInvalid('unsupported media type')
        if hashlib.sha256(bytes(data)).hexdigest() != document['sha256']:
            raise DocumentInvalid('the hash does not match the bytes')
        try:
            text = bytes(data).decode('utf-8')
        except UnicodeDecodeError:
            raise DocumentInvalid('not UTF-8 text')
        fields = []
        for f in DOC.standin_extract_quote(text):
            rec = {'name': f['name'], 'text': f['text'], 'location': f['location'], 'candidates': list(f['candidates']), 'ambiguous': bool(f['ambiguous']), 'why': f['why'], 'confidence_bps': None, 'status': 'unverified'}
            if not rec['ambiguous']:
                rec['value'] = rec['candidates'][0] if len(rec['candidates']) == 1 else rec['text']
            fields.append(rec)
        return canon.deep_copy({'doc_id': document['doc_id'], 'sha256': document['sha256'], 'tool': self.TOOL, 'tool_version': self.VERSION, 'fields': fields})


def feed_env(feed_cls=InMemoryMarketFeed, provider_cls=StaticContextProvider):
    def factory():
        c = FakeClock()
        p = provider_cls(c)
        return FeedEnv(p, feed_cls(p, c), c.advance)
    return factory


def extract_env(extractor_cls=StandInExtractor, provider_cls=StaticContextProvider):
    def factory():
        c = FakeClock()
        p = provider_cls(c)
        return ExtractEnv(p, extractor_cls(p, c), c.advance)
    return factory
