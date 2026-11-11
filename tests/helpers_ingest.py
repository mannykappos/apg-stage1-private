import csv, io, json, os
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from apg import tenancy
from apg.reference_impl import FakeClock, InMemoryAuditLog, InMemoryRecordStore, StaticContextProvider
from apg.ingest import demo_setup as D


class World:
    def __init__(self, start='2026-10-01T09:00:00Z'):
        self.clock = FakeClock(start)
        self.provider = StaticContextProvider(self.clock)
        self.store = InMemoryRecordStore(self.provider)
        self.audit = InMemoryAuditLog(self.provider, self.clock)

    def who(self, token, tenant='zero_one', user='ann', roles=('importer',), kind='human', ttl=360000):
        self.provider._contract_register_session(token, tenant, user, tuple(roles), kind, ttl)
        return tenancy.ScopedStore(self.store, self.audit, self.provider.resolve(token))


def tpl(name):
    for d in ('import_templates', 'ingest_templates'):
        p = os.path.join(HERE_ROOT, d, name + '.json')
        if os.path.exists(p):
            return json.load(open(p, encoding='utf-8'))
    raise FileNotFoundError(name)


def csvb(header, rows, delim=',', newline='\n'):
    b = io.StringIO()
    w = csv.writer(b, delimiter=delim, lineterminator=newline)
    w.writerow(header)
    w.writerows(rows)
    return b.getvalue().encode('utf-8')


def bz(rel):
    return open(os.path.join(HERE_ROOT, 'builder_zero', rel), 'rb').read()


INV_H = ['invoice_id', 'supplier_id', 'supplier_invoice_no', 'project_id', 'cost_code', 'po_id', 'invoice_date', 'ex_gst_cents', 'gst_cents', 'status', 'source_batch']


def inv(invoice_id='INV-1', supplier='SUP-001', sin='SI-1', project='PRJ-001', cc='CC-01', po='', date='2026-05-01', ex='1000000', gst='100000', status='posted', batch='B-1'):
    return [invoice_id, supplier, sin, project, cc, po, date, ex, gst, status, batch]


def inv_file(*rows):
    return csvb(INV_H, rows)


SUP_H = ['supplier_id', 'name', 'abn_synthetic']


def sup_file(*pairs):
    return csvb(SUP_H, [[s, n, ''] for s, n in pairs])


STD_SUPPLIERS = (('SUP-001', 'Alpha Concrete Pty Ltd'), ('SUP-002', 'Beta Timber Pty Ltd'), ('SUP-003', 'Metro Steel Pty Ltd'), ('SUP-004', 'Metro Steel and Fixings Pty Ltd'))


def load_suppliers(w, s):
    from apg.ingest import pipeline
    return pipeline.ingest_file(s, w.clock, tpl('TPL-BZ-SUPPLIERS'), sup_file(*STD_SUPPLIERS), 'master', 'suppliers.csv', D.DEMO_POLICY)
