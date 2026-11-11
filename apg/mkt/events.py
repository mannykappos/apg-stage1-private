"""Event records: the hook M7 will connect.  Blueprint: Section 06 section 5.4 (cross-domain relationships show the evidence chain), Section 14 (relationships document the initiating event, authoritative
source and state transition); RFC-01 capability 1 (time-aware relationships need an observation time, an effective time, provenance and the project, material and supplier identifiers).

M6 builds NO relationship or chain detection.  It only makes sure that everything it computes can be located in time and linked later, without re-reading the source records:
  observed_at     when APG learned of it (the retrieval or receipt timestamp of the source record), never the effective date
  effective_from  the first day the fact applies; effective_to the last day it applies, or None when open-ended
  sources         the stored records it rests on, with the revision read
  project, material, supplier   identifiers, or None when the event does not belong to one

An event is data, not a conclusion: a later engine may link events, and a person must still decide what a chain means."""
from .. import canon

EVENT_VERSION = 'apg-event-1'
EVENT_TYPES = ('quote_issued', 'quote_expires', 'market_observed', 'fx_observed', 'demand_required', 'order_placed', 'delivery_received', 'decision_deadline', 'surplus_ordered',
               'duplicate_suspected', 'import_check_open', 'supplier_evidence_expires')


class EventError(ValueError):
    pass


def _date(v):
    return isinstance(v, str) and len(v) == 10 and v[4] == '-' and v[7] == '-' and v[:4].isdigit() and v[5:7].isdigit() and v[8:].isdigit()


def make(etype, subject, observed_at, effective_from, sources, effective_to=None, project=None, material=None, supplier=None, detail=None):
    e = {'event_version': EVENT_VERSION, 'type': etype, 'subject': subject, 'observed_at': observed_at, 'effective_from': effective_from, 'effective_to': effective_to,
         'project': project, 'material': material, 'supplier': supplier, 'sources': sorted(({'ref': r, 'revision': v} for r, v in sources), key=lambda s: (s['ref'], s['revision'] if s['revision'] is not None else -1)),
         'detail': canon.deep_copy(detail or {})}
    e['event_id'] = 'EV-' + canon.digest({k: v for k, v in e.items() if k != 'event_id'})[:20]
    validate(e)
    return e


def validate(e):
    if not isinstance(e, dict) or e.get('event_version') != EVENT_VERSION:
        raise EventError('event version')
    if e['type'] not in EVENT_TYPES:
        raise EventError('event type')
    if not isinstance(e['subject'], str) or not e['subject']:
        raise EventError('subject')
    if not (isinstance(e['observed_at'], str) and e['observed_at'][:10] and _date(e['observed_at'][:10])):
        raise EventError('observed_at is required: the time APG learned of the fact')
    if not _date(e['effective_from']) or (e['effective_to'] is not None and (not _date(e['effective_to']) or e['effective_to'] < e['effective_from'])):
        raise EventError('effective period')
    if not e['sources'] or any(not s['ref'] or '/' not in s['ref'] for s in e['sources']):
        raise EventError('an event rests on at least one stored record')
    for k in ('project', 'material', 'supplier'):
        if e[k] is not None and (not isinstance(e[k], str) or not e[k]):
            raise EventError(k)
    if e.get('event_id') != 'EV-' + canon.digest({k: v for k, v in e.items() if k != 'event_id'})[:20]:
        raise EventError('event identity does not match the event')
    canon.canonical(e)
    return True
