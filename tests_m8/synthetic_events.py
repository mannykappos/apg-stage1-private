"""A SYNTHETIC event source for the M8 tests: payments arriving as events, one at a time, with a source sequence number.  A test double, not a real system; it holds no
credential, opens no socket and cannot be written to."""
from auif.connector import Connector
from auif.errors import TransportError
from auif_ext.connectors.descriptor import build_descriptor

COLUMNS = ['payment_id', 'invoice_id', 'payment_date', 'amount_cents']
EVENT = 'payment.recorded'


class SyntheticPaymentEvents(Connector):
    connector_id, connector_version = 'synthetic-payment-events', '0.1.0'

    def __init__(self):
        self.queue = []

    def descriptor(self):
        return build_descriptor(connector_id=self.connector_id, version=self.connector_version, protocol_class='EXTENSION', display_name='Synthetic payment events (test double)')

    def connect(self, credentials):
        return None

    def disconnect(self):
        return None

    def health(self):
        return {'status': 'up'}

    def capabilities(self):
        return {'read': True, 'write': False, 'discover': True}

    def discover(self):
        return {'system_version': 'synthetic-events-1', 'generated_at': 'volatile', 'environment': 'synthetic', 'auth_requirements': {'type': 'none'},
                'pagination': {'style': 'CURSOR', 'max_page_size': 200}, 'rate_limits': {'requests_per_second': 10},
                'entities': [{'name': 'payment', 'fields': [{'name': c, 'type': 'string'} for c in COLUMNS], 'relationships': []}],
                'operations': [{'name': 'read_payment', 'kind': 'read', 'entities': ['payment']}], 'events': [{'name': EVENT, 'entities': ['payment']}],
                'not_exposed': ['write', 'webhook_support']}

    def read(self, request):
        items, self.queue = self.queue, []
        return {'items': items, 'next_cursor': None, 'complete': True}

    def write(self, request):
        raise TransportError('UNSUPPORTED_OPERATION', applied='NOT_APPLIED')

    def subscribe(self, request):
        raise TransportError('UNSUPPORTED_OPERATION', applied='NOT_APPLIED')

    def unsubscribe(self, request):
        return {'unsubscribed': True}


def event(n, payment_id, invoice_id='INV-0001', date='2026-06-01', cents='1000', event_id=None):
    return {'event_id': event_id or 'ev-%04d' % n, 'type': EVENT, 'source_sequence': n,
            'payload': {'payment_id': payment_id, 'invoice_id': invoice_id, 'payment_date': date, 'amount_cents': cents}}
