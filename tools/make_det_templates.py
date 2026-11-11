#!/usr/bin/env python3
"""Writes the M5 mapping templates (same format as the M1, M3 and M4 templates) for the Builder Zero record types the detection rules read that earlier milestones did not
ingest: supplier compliance evidence, commercial notices, delay events, plant hire, timesheets, work output, defects and supplier quotes.
Usage: make_det_templates.py <out_dir>.  Deterministic.  Every template is a DRAFT, unverified against any real export."""
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


tpl('TPL-BZ-COMPLIANCE', 'SRC-06', 'Builder Zero supplier compliance evidence (synthetic)', 'compliance', ['supplier_id', 'evidence_type'],
    [col('supplier_id', 'supplier_ref', 'string'), col('evidence_type', 'evidence_type_text', 'string'), col('expiry_date', 'expiry_date', 'date')])
tpl('TPL-BZ-NOTICES', 'SRC-07', 'Builder Zero commercial notices (synthetic)', 'notice', ['notice_id'],
    [col('notice_id', 'source_record_id', 'string'), col('project_id', 'project_ref', 'string'), col('notice_date', 'notice_date', 'date'), col('notice_type', 'notice_type_text', 'string'),
     col('linked_variation_id', 'linked_variation_ref', 'string', False), col('description', 'description_text', 'string', False)])
tpl('TPL-BZ-DELAY-EVENTS', 'SRC-04', 'Builder Zero delay events (synthetic)', 'delay_event', ['event_id'],
    [col('event_id', 'source_record_id', 'string'), col('project_id', 'project_ref', 'string'), col('activity_id', 'activity_ref', 'string', False), col('start_date', 'start_date', 'date'),
     col('end_date', 'end_date', 'date', False), col('working_days', 'working_days', 'integer', False), col('recorded_cause', 'recorded_cause_text', 'string', False),
     col('holding_cost_rate_cents_per_day', 'holding_rate_cents_per_day', 'money_cents', False)])
tpl('TPL-BZ-PLANT-HIRE', 'SRC-13', 'Builder Zero plant hire (synthetic)', 'plant_hire', ['hire_id'],
    [col('hire_id', 'source_record_id', 'string'), col('project_id', 'project_ref', 'string'), col('equipment', 'equipment_text', 'string'), col('on_hire_date', 'on_hire_date', 'date'),
     col('off_hire_date', 'off_hire_date', 'date', False), col('needed_until', 'needed_until', 'date', False), col('rate_cents_per_day', 'rate_cents_per_day', 'money_cents')])
tpl('TPL-BZ-TIMESHEETS', 'SRC-12', 'Builder Zero timesheets, pseudonymised (synthetic)', 'timesheet', ['entry_id'],
    [col('entry_id', 'source_record_id', 'string'), col('worker_pseudonym', 'worker_pseudonym', 'string'), col('project_id', 'project_ref', 'string'),
     col('work_package', 'work_package_ref', 'string'), col('work_date', 'work_date', 'date'), col('ordinary_hours', 'ordinary_hours', 'decimal'),
     col('overtime_hours', 'overtime_hours', 'decimal', False), col('rate_cents_per_hour', 'rate_cents_per_hour', 'money_cents', False)])
tpl('TPL-BZ-WORK-OUTPUT', 'SRC-12', 'Builder Zero completed quantities by week (synthetic)', 'work_output', ['project_id', 'work_package', 'week_start'],
    [col('project_id', 'project_ref', 'string'), col('work_package', 'work_package_ref', 'string'), col('week_start', 'week_start', 'date'), col('quantity', 'quantity', 'decimal'),
     col('unit', 'unit_text', 'string')])
tpl('TPL-BZ-DEFECTS', 'SRC-08', 'Builder Zero defects (synthetic)', 'defect', ['defect_id'],
    [col('defect_id', 'source_record_id', 'string'), col('project_id', 'project_ref', 'string'), col('subcontractor', 'subcontractor_text', 'string', False), col('trade', 'trade_text', 'string', False),
     col('raised_date', 'raised_date', 'date'), col('severity', 'severity_text', 'string', False), col('rework_cost_cents', 'rework_cost_cents', 'money_cents', False),
     col('status', 'status_text', 'string', False)])
print('written', len(os.listdir(out)), 'templates to', out)
