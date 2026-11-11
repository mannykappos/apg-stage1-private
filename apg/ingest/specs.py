"""What each kind of record means to the pipeline: which of its fields are material (they decide money), which must be positive, which dates are events,
how to recognise a duplicate delivery, and which supplier field it carries.  These are the builder's reading of Section 04 for the Builder Zero record types and are
open to correction by whoever confirms the real source layouts (they are not product-owner decisions and they invent no thresholds).

IngestPolicy holds the choices that ARE configuration.  Its default is the safe one: any optional value that is missing and not explicitly declared tolerable stops the
record from being used (it goes to reconciliation).  A policy may relax that field by field; it can never relax a MATERIAL field."""
from dataclasses import dataclass, field
from .mapping import Limits

SPECS = {
    'supplier': dict(material=(), primary=None, positive=(), dates=(), supplier_field=None, strong=(), composite=()),
    'ap_invoice': dict(material=('amount_ex_gst_cents',), primary='amount_ex_gst_cents', positive=('amount_ex_gst_cents',), dates=('invoice_date',), supplier_field='supplier_ref',
                       strong=('supplier_ref', 'supplier_invoice_number'),
                       composite=('supplier_ref', 'supplier_invoice_number', 'project_ref', 'purchase_order_ref', 'invoice_date', 'amount_ex_gst_cents', 'gst_cents')),
    'credit_note': dict(material=('amount_ex_gst_cents',), primary='amount_ex_gst_cents', positive=('amount_ex_gst_cents',), dates=('credit_date',), supplier_field='supplier_ref', strong=(),
                        composite=('supplier_ref', 'against_invoice_ref', 'credit_date', 'amount_ex_gst_cents')),
    'payment': dict(material=('amount_cents',), primary='amount_cents', positive=('amount_cents',), dates=('payment_date',), supplier_field=None, strong=(),
                    composite=('invoice_ref', 'payment_date', 'amount_cents')),
    'purchase_order': dict(material=('amount_ex_gst_cents',), primary='amount_ex_gst_cents', positive=('amount_ex_gst_cents',), dates=('order_date',), supplier_field='supplier_ref', strong=(),
                           composite=('supplier_ref', 'project_ref', 'order_date', 'material_ref', 'quantity', 'unit_rate_cents', 'amount_ex_gst_cents')),
    'po_amendment': dict(material=('delta_cents',), primary='delta_cents', positive=(), dates=('amendment_date',), supplier_field=None, strong=(),
                         composite=('purchase_order_ref', 'amendment_date', 'delta_cents')),
    'supplier_quote': dict(material=('unit_rate_minor_units',), primary='unit_rate_minor_units', positive=('unit_rate_minor_units',), dates=('issue_date',), supplier_field='supplier_ref', strong=(),
                           composite=('supplier_ref', 'material_ref', 'issue_date', 'unit_rate_minor_units', 'currency_code')),
    'pm_invoice': dict(material=('amount_ex_gst_cents',), primary='amount_ex_gst_cents', positive=('amount_ex_gst_cents',), dates=(), supplier_field='supplier_ref', strong=(), composite=(),
                       secondary_for=('ap_invoice', 'amount_ex_gst_cents')),
    'budget_line': dict(material=('budget_cents',), primary='budget_cents', positive=(), dates=('revision_date',), supplier_field=None, strong=(), composite=()),
    'fx_rate': dict(material=(), primary=None, positive=(), dates=('fx_date',), supplier_field=None, strong=(), composite=()),
    'market_observation': dict(material=(), primary=None, positive=(), dates=('obs_date',), supplier_field=None, strong=(), composite=()),
}
ENTITIES = tuple(SPECS)


@dataclass(frozen=True)
class IngestPolicy:
    """warn_unknown: {entity: (field, ...)} fields whose absence is only a warning.  Everything else that is missing blocks use.  Material fields are never relaxable.
    future_days_allowed: how many days after the receipt date an event date may fall before the record is held (0 = none)."""
    warn_unknown: dict = field(default_factory=dict)
    future_days_allowed: int = 0
    limits: Limits = field(default_factory=Limits)

    def tolerates_missing(self, entity, fld):
        spec = SPECS[entity]
        return fld not in spec['material'] and fld in self.warn_unknown.get(entity, ())
