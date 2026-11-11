#!/usr/bin/env python3
"""Writes the example mapping templates and one small sample file. Usage: make_templates.py <import_templates_dir>"""
import json, os, sys
O = sys.argv[1]; os.makedirs(os.path.join(O, 'samples'), exist_ok=True)
def col(src, tgt, typ, req=False, tr=None, **kw):
    d = {'source_column': src, 'target_field': tgt, 'type': typ, 'required': req}
    if tr: d['transform'] = tr
    d.update(kw); return d
COMMON = {'format_version': 'apg-mapping-template-1.0', 'status': 'draft - unverified against any real export', 'tenant_binding': 'authenticated_context',
          'unmapped_columns_policy': 'preserve_as_raw_and_report', 'on_row_error': 'reject_row_and_report'}
T = []
T.append(dict(COMMON, template_id='TPL-BZ-AP-INVOICES', source_label='Builder Zero accounting export (synthetic)', source_category='SRC-01', file={'type': 'csv', 'encoding': 'utf-8', 'delimiter': ',', 'header_row': 1},
    money={'unit': 'cents', 'gst': 'separate_column'}, natural_key=['invoice_id'], target_entity='ap_invoice', columns=[
    col('invoice_id', 'source_record_id', 'string', True, 'trim'), col('supplier_id', 'supplier_ref', 'string', True, 'trim'), col('supplier_invoice_no', 'supplier_invoice_number', 'string', True, 'trim'),
    col('project_id', 'project_ref', 'string', True, 'trim'), col('cost_code', 'cost_code_ref', 'string', False, 'trim'), col('po_id', 'purchase_order_ref', 'string', False, 'trim'),
    col('invoice_date', 'invoice_date', 'date', True, 'parse_date', date_format='%Y-%m-%d'), col('ex_gst_cents', 'amount_ex_gst_cents', 'money_cents', True, 'none'),
    col('gst_cents', 'gst_cents', 'money_cents', False, 'none', missing_means='unknown_not_zero'), col('status', 'source_status', 'string', False, 'trim'), col('source_batch', 'source_batch_ref', 'string', False, 'trim')]))
T.append(dict(COMMON, template_id='TPL-BZ-PURCHASE-ORDERS', source_label='Builder Zero procurement export (synthetic)', source_category='SRC-03', file={'type': 'csv', 'encoding': 'utf-8', 'delimiter': ',', 'header_row': 1},
    money={'unit': 'cents', 'gst': 'not_applicable'}, natural_key=['po_id'], target_entity='purchase_order', columns=[
    col('po_id', 'source_record_id', 'string', True, 'trim'), col('supplier_id', 'supplier_ref', 'string', True, 'trim'), col('project_id', 'project_ref', 'string', True, 'trim'),
    col('cost_code', 'cost_code_ref', 'string', False, 'trim', missing_means='unknown_not_zero'), col('po_date', 'order_date', 'date', True, 'parse_date', date_format='%Y-%m-%d'),
    col('material_id', 'material_ref', 'string', False, 'trim'), col('qty', 'quantity', 'integer', True, 'none'), col('unit', 'unit_of_measure', 'string', True, 'trim'),
    col('unit_rate_cents', 'unit_rate_cents', 'money_cents', False, 'none'), col('amount_cents', 'amount_ex_gst_cents', 'money_cents', True, 'none'), col('status', 'source_status', 'string', False, 'trim')]))
T.append(dict(COMMON, template_id='TPL-BZ-QUOTES', source_label='Builder Zero quotes export (synthetic)', source_category='SRC-03', file={'type': 'csv', 'encoding': 'utf-8', 'delimiter': ',', 'header_row': 1},
    money={'unit': 'cents', 'gst': 'not_applicable'}, natural_key=['quote_id'], target_entity='supplier_quote', columns=[
    col('quote_id', 'source_record_id', 'string', True, 'trim'), col('supplier_id', 'supplier_ref', 'string', True, 'trim'), col('material_id', 'material_ref', 'string', True, 'trim'),
    col('specification', 'specification_text', 'string', True, 'trim'), col('issue_date', 'issue_date', 'date', True, 'parse_date', date_format='%Y-%m-%d'),
    col('valid_until', 'valid_until', 'date', True, 'parse_date', date_format='%Y-%m-%d'), col('unit_rate_cents', 'unit_rate_minor_units', 'money_cents', True, 'none'),
    col('currency', 'currency_code', 'enum', True, 'upper', allowed=['AUD', 'USD', 'EUR', 'NZD', 'CNY']), col('fx_rate_used', 'fx_rate_used', 'decimal', False, 'none'),
    col('fx_rate_date', 'fx_rate_date', 'date', False, 'parse_date', date_format='%Y-%m-%d'), col('freight_cents_per_unit', 'freight_per_unit_cents', 'money_cents', False, 'none'),
    col('incoterm_delivery_basis', 'delivery_basis', 'string', True, 'trim'), col('lead_time_days', 'lead_time_days', 'integer', False, 'none'), col('price_kind', 'price_kind', 'string', True, 'trim')]))
T.append(dict(COMMON, template_id='TPL-EX-ACCOUNTING-DOLLARS', source_label='Example only: a different layout with DD/MM/YYYY dates and dollar amounts (synthetic)', source_category='SRC-01',
    file={'type': 'csv', 'encoding': 'utf-8-sig', 'delimiter': ',', 'header_row': 1}, money={'unit': 'dollars', 'gst': 'inclusive_total_column'}, natural_key=['Ref'], target_entity='ap_invoice', columns=[
    col('Ref', 'source_record_id', 'string', True, 'trim'), col('Supplier', 'supplier_name_text', 'string', True, 'trim'), col('Job', 'project_ref', 'string', True, 'trim'),
    col('Date', 'invoice_date', 'date', True, 'parse_date', date_format='%d/%m/%Y'), col('Total (inc GST)', 'amount_inc_gst_cents', 'money_cents', True, 'dollars_to_cents')]))
for t in T:
    json.dump(t, open(os.path.join(O, t['template_id'] + '.json'), 'w'), indent=1, sort_keys=True); open(os.path.join(O, t['template_id'] + '.json'), 'a').write('\n')
open(os.path.join(O, 'samples/EX_accounting_dollars.csv'), 'w', newline='\n', encoding='utf-8-sig').write('Ref,Supplier,Job,Date,Total (inc GST)\nEX-1,Example Supplier A (synthetic),J1,05/03/2026,"1,100.00"\nEX-2,Example Supplier B (synthetic),J1,17/03/2026,$55.55\n')
