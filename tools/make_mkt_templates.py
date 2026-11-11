#!/usr/bin/env python3
"""Writes the M6 mapping templates (same format as the M1, M3, M4 and M5 templates) for the procurement records that earlier milestones did not ingest: the material master, material
demand, delivery dockets, and five SYNTHETIC supplement files that carry what no Builder Zero file carries (person-declared specification requirements, verified readings of quote
text, quote terms and quantity tiers, landed-cost assumptions, import-check outcomes).  Usage: make_mkt_templates.py <out_dir>.  Deterministic.  Every template is a DRAFT, unverified against any real export."""
import json, os, sys
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
FILE = {'delimiter': ',', 'encoding': 'utf-8', 'header_row': 1, 'type': 'csv'}


def col(src, tgt, typ, required=True, transform=None, **kw):
    c = {'required': required, 'source_column': src, 'target_field': tgt, 'type': typ, 'transform': transform or {'string': 'trim', 'date': 'parse_date'}.get(typ, 'none')}
    if typ == 'date':
        c['date_format'] = '%Y-%m-%d'
    if not required:
        c['missing_means'] = 'unknown_not_zero'
    c.update(kw)
    return c


def tpl(tid, cat, label, entity, key, cols):
    t = {'columns': cols, 'file': dict(FILE), 'format_version': 'apg-mapping-template-1.0', 'money': {'gst': 'not_applicable', 'unit': 'cents'}, 'natural_key': key, 'on_row_error': 'reject_row_and_report',
         'source_category': cat, 'source_label': label, 'status': 'draft - unverified against any real export', 'target_entity': entity, 'template_id': tid,
         'tenant_binding': 'authenticated_context', 'unmapped_columns_policy': 'preserve_as_raw_and_report'}
    p = os.path.join(out, tid + '.json')
    json.dump(t, open(p, 'w'), indent=1, sort_keys=True)
    open(p, 'a').write('\n')


tpl('TPL-BZ-MATERIALS', 'SRC-05', 'Builder Zero material master (synthetic)', 'material', ['material_id'],
    [col('material_id', 'source_record_id', 'string'), col('description', 'description_text', 'string', False), col('unit', 'unit_text', 'string')])
tpl('TPL-BZ-MATERIAL-DEMAND', 'SRC-05', 'Builder Zero material demand (synthetic)', 'material_demand', ['demand_id'],
    [col('demand_id', 'source_record_id', 'string'), col('project_id', 'project_ref', 'string'), col('material_id', 'material_ref', 'string'), col('qty', 'quantity', 'decimal'),
     col('unit', 'unit_text', 'string'), col('required_on_site', 'required_date', 'date')])
tpl('TPL-BZ-DELIVERIES', 'SRC-05', 'Builder Zero delivery dockets (synthetic)', 'delivery', ['docket_id'],
    [col('docket_id', 'source_record_id', 'string'), col('po_id', 'purchase_order_ref', 'string'), col('material_id', 'material_ref', 'string'), col('delivery_date', 'delivery_date', 'date'),
     col('qty_delivered', 'qty_delivered', 'decimal'), col('qty_accepted', 'qty_accepted', 'decimal', False)])
tpl('TPL-MKT-SPEC-REQUIREMENTS', 'SRC-05', 'M6 synthetic supplement: specification requirements a person approved', 'spec_requirement', ['requirement_id'],
    [col('requirement_id', 'source_record_id', 'string'), col('project_id', 'project_ref', 'string'), col('material_id', 'material_ref', 'string'), col('basis_ref', 'basis_ref', 'string', False),
     col('approved_by', 'approved_by', 'string', False), col('approved_on', 'approved_on', 'date', False)])
tpl('TPL-MKT-QUOTE-READINGS', 'SRC-03', 'M6 synthetic supplement: readings of quote text (extraction and its human verification)', 'quote_reading', ['quote_id', 'attribute'],
    [col('quote_id', 'quote_ref', 'string'), col('attribute', 'attribute_name', 'string'), col('value', 'value_text', 'string'), col('extracted_by', 'extracted_by', 'string'),
     col('extractor_kind', 'extractor_kind', 'string'), col('verified_by', 'verified_by', 'string', False), col('verified_on', 'verified_on', 'date', False)])
tpl('TPL-MKT-QUOTE-TIERS', 'SRC-03', 'M6 synthetic supplement: quote quantity tiers', 'quote_tier', ['quote_id', 'min_qty'],
    [col('quote_id', 'quote_ref', 'string'), col('min_qty', 'min_quantity', 'decimal'), col('unit_rate_cents', 'unit_rate_minor_units', 'money_cents')])
tpl('TPL-MKT-QUOTE-TERMS', 'SRC-03', 'M6 synthetic supplement: quote terms', 'quote_term', ['quote_id', 'term'],
    [col('quote_id', 'quote_ref', 'string'), col('term', 'term_name', 'string'), col('value', 'value_text', 'string')])
tpl('TPL-MKT-LANDED-ASSUMPTIONS', 'SRC-03', 'M6 synthetic supplement: landed-cost component assumptions a person set', 'landed_assumption', ['quote_id', 'component'],
    [col('quote_id', 'quote_ref', 'string'), col('component', 'component_name', 'string'), col('per_unit_cents', 'per_unit_minor_units', 'money_cents', False),
     col('rate_bps', 'rate_bps', 'integer', False), col('currency', 'currency_code', 'string', False), col('basis', 'basis_text', 'string', False), col('source_ref', 'source_ref', 'string', False),
     col('set_by', 'set_by', 'string', False), col('set_on', 'set_on', 'date', False)])
tpl('TPL-MKT-IMPORT-CHECKS', 'SRC-03', 'M6 synthetic supplement: import and compliance check outcomes a person recorded', 'import_check', ['quote_id', 'check'],
    [col('quote_id', 'quote_ref', 'string'), col('check', 'check_name', 'string'), col('status', 'status_text', 'string'), col('evidence_ref', 'evidence_ref', 'string', False),
     col('checked_by', 'checked_by', 'string', False), col('checked_on', 'checked_on', 'date', False)])
print('written', len(os.listdir(out)), 'templates to', out)
