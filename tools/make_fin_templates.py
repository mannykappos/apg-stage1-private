#!/usr/bin/env python3
"""Writes the M4 mapping templates (same format as the M1 and M3 templates) for the Builder Zero record types the financial core reads that M3 did not ingest:
projects, contracts, variations, cost-to-complete forecast lines, retention, security instruments, the funding facility and bank transactions.
Usage: make_fin_templates.py <out_dir>.  Deterministic.  Every template is a DRAFT, unverified against any real export."""
import json, os, sys
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
FILE = {'delimiter': ',', 'encoding': 'utf-8', 'header_row': 1, 'type': 'csv'}
def col(src, tgt, typ, required=True, transform=None, **kw):
    c = {'required': required, 'source_column': src, 'target_field': tgt, 'type': typ, 'transform': transform or {'string': 'trim', 'date': 'parse_date'}.get(typ, 'none')}
    if typ == 'date': c['date_format'] = '%Y-%m-%d'
    if not required: c['missing_means'] = 'unknown_not_zero'
    c.update(kw); return c
def tpl(tid, cat, label, entity, key, cols):
    t = {'columns': cols, 'file': dict(FILE), 'format_version': 'apg-mapping-template-1.0', 'money': {'gst': 'not_applicable', 'unit': 'cents'}, 'natural_key': key, 'on_row_error': 'reject_row_and_report',
         'source_category': cat, 'source_label': label, 'status': 'draft - unverified against any real export', 'target_entity': entity, 'template_id': tid,
         'tenant_binding': 'authenticated_context', 'unmapped_columns_policy': 'preserve_as_raw_and_report'}
    p = os.path.join(out, tid + '.json')
    json.dump(t, open(p, 'w'), indent=1, sort_keys=True); open(p, 'a').write('\n')
tpl('TPL-BZ-PROJECTS', 'SRC-02', 'Builder Zero project master (synthetic)', 'project', ['project_id'],
    [col('project_id', 'project_ref', 'string'), col('name', 'project_name', 'string', False), col('contract_value_cents', 'contract_value_cents', 'money_cents', False),
     col('start_date', 'start_date', 'date', False), col('planned_finish', 'planned_finish', 'date', False)])
tpl('TPL-BZ-CONTRACTS', 'SRC-07', 'Builder Zero contracts (synthetic)', 'contract', ['project_id'],
    [col('project_id', 'project_ref', 'string'), col('original_contract_cents', 'original_contract_cents', 'money_cents'), col('approved_variations_cents', 'approved_variations_cents', 'money_cents', False)])
tpl('TPL-BZ-VARIATIONS', 'SRC-07', 'Builder Zero variations (synthetic)', 'variation', ['variation_id'],
    [col('variation_id', 'source_record_id', 'string'), col('project_id', 'project_ref', 'string'), col('raised_date', 'raised_date', 'date'), col('status', 'source_status', 'string'),
     col('value_cents', 'value_cents', 'money_cents', False), col('description', 'description_text', 'string', False)])
tpl('TPL-BZ-CTC-FORECASTS', 'SRC-02', 'Builder Zero cost-to-complete forecast lines (synthetic)', 'ctc_line', ['project_id', 'cost_code', 'forecast_version'],
    [col('project_id', 'project_ref', 'string'), col('cost_code', 'cost_code_ref', 'string'), col('forecast_version', 'forecast_version', 'string'), col('forecast_date', 'forecast_date', 'date'),
     col('cost_to_complete_cents', 'cost_to_complete_cents', 'money_cents'), col('estimate_basis', 'estimate_basis_text', 'string', False), col('movement_reason', 'movement_reason_text', 'string', False)])
tpl('TPL-BZ-RETENTION', 'SRC-09', 'Builder Zero retention ledger (synthetic)', 'retention', ['project_id'],
    [col('project_id', 'project_ref', 'string'), col('retention_held_cents', 'retention_held_cents', 'money_cents'), col('release_due_date', 'release_due_date', 'date', False),
     col('released_date', 'released_date', 'date', False), col('hold_reason', 'hold_reason_text', 'string', False)])
tpl('TPL-BZ-SECURITY', 'SRC-09', 'Builder Zero security instruments (synthetic)', 'security', ['instrument_id'],
    [col('instrument_id', 'source_record_id', 'string'), col('project_id', 'project_ref', 'string'), col('kind', 'kind_text', 'string'), col('face_value_cents', 'face_value_cents', 'money_cents'),
     col('expiry_date', 'expiry_date', 'date', False)])
tpl('TPL-BZ-FACILITY', 'SRC-14', 'Builder Zero funding facility statement (synthetic)', 'facility', ['facility_id'],
    [col('facility_id', 'source_record_id', 'string'), col('limit_cents', 'limit_cents', 'money_cents'), col('drawn_cents', 'drawn_cents', 'money_cents'), col('rate_bps', 'rate_bps', 'integer'),
     col('as_of', 'statement_date', 'date')])
tpl('TPL-BZ-BANK', 'SRC-14', 'Builder Zero bank transactions (synthetic)', 'bank_txn', ['txn_id'],
    [col('txn_id', 'source_record_id', 'string'), col('txn_date', 'txn_date', 'date'), col('amount_cents', 'amount_cents', 'money_cents'), col('description', 'description_text', 'string', False)])
print('written', len(os.listdir(out)), 'templates to', out)
