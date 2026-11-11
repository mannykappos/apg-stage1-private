"""Demonstration configuration for Builder Zero.  EVERYTHING HERE IS SYNTHETIC OR ILLUSTRATIVE: the authority register below is NOT an approved register for any real
builder, and the tolerated-missing fields are the builder's demonstration choices, not product-owner decisions.  Real values come from the Source Authority Register
that a real authority owner approves, and from the pilot."""
import json, os
from ..source_authority import Approval, AuthorityRegister, AuthorityRule, RegisterHistory
from .specs import IngestPolicy

SOURCES = {'accounting': 'accounting', 'procurement': 'procurement', 'job_costing': 'job_costing', 'pm_system': 'pm_system'}


def _rule(kind, fld, auth, secondary=(), disagree='quarantine', role='reconciler', approvals=1):
    return AuthorityRule(kind, fld, auth, tuple(secondary), 'source_owned', disagree, role, approvals, '2025-01-01', None, 'synthetic.authority_owner', 'SYNTHETIC demonstration rule')


def demo_register(approved=True, version='SYN-REG-1'):
    rules = (_rule('ap_invoice', 'amount_ex_gst_cents', 'accounting', ('pm_system',)), _rule('credit_note', 'amount_ex_gst_cents', 'accounting'), _rule('payment', 'amount_cents', 'accounting'),
             _rule('purchase_order', 'amount_ex_gst_cents', 'procurement'), _rule('po_amendment', 'delta_cents', 'procurement'), _rule('supplier_quote', 'unit_rate_minor_units', 'procurement'),
             _rule('budget_line', 'budget_cents', 'job_costing'))
    ap = (Approval('synthetic.owner', 'authority_owner', 'human', '2026-09-30'),) if approved else ()
    return AuthorityRegister(version, rules, 'synthetic.proposer', ap)


DEMO_POLICY = IngestPolicy(warn_unknown={
    'ap_invoice': ('gst_cents', 'purchase_order_ref', 'source_status', 'source_batch_ref'), 'credit_note': ('gst_cents',), 'purchase_order': ('material_ref', 'unit_rate_cents', 'source_status'),
    'po_amendment': ('approved_change_ref', 'reason_text'), 'pm_invoice': ('source_label_text',), 'supplier': ('abn_text',),
    'supplier_quote': ('fx_rate_used', 'fx_rate_date', 'freight_per_unit_cents', 'lead_time_days')})

# (template file, data file under builder_zero/<tenant>/, source identity, revision field)
def files_for(root, tenant):
    tdirs = (os.path.join(root, 'import_templates'), os.path.join(root, 'ingest_templates'))
    def T(name):
        for d in tdirs:
            p = os.path.join(d, name + '.json')
            if os.path.exists(p):
                return json.load(open(p, encoding='utf-8'))
        raise FileNotFoundError(name)
    base = os.path.join(root, 'builder_zero', tenant)
    L = [('TPL-BZ-SUPPLIERS', 'reference/suppliers.csv', 'master', None), ('TPL-BZ-AP-INVOICES', 'SRC-01_accounting/ap_invoices.csv', 'accounting', None),
         ('TPL-BZ-CREDIT-NOTES', 'SRC-01_accounting/credit_notes.csv', 'accounting', None), ('TPL-BZ-PAYMENTS', 'SRC-01_accounting/payments.csv', 'accounting', None),
         ('TPL-BZ-PURCHASE-ORDERS', 'SRC-03_procurement/purchase_orders.csv', 'procurement', None), ('TPL-BZ-PO-AMENDMENTS', 'SRC-03_procurement/po_amendments.csv', 'procurement', None),
         ('TPL-BZ-QUOTES', 'SRC-03_procurement/quotes.csv', 'procurement', None), ('TPL-BZ-BUDGET-LINES', 'SRC-02_costing/budget_lines.csv', 'job_costing', 'source_revision_label'),
         ('TPL-BZ-FX-RATES', 'SRC-10_market/fx_rates.csv', 'market', None), ('TPL-BZ-MARKET-OBSERVATIONS', 'SRC-10_market/market_observations.csv', 'market', None),
         ('TPL-BZ-PM-INVOICES', 'conflicting_sources/pm_system_invoices.csv', 'pm_system', None)]
    out = []
    for tid, rel, src, rev in L:
        p = os.path.join(base, rel)
        if os.path.exists(p):
            out.append((T(tid), open(p, 'rb').read(), src, os.path.basename(p), rev))
    return out
