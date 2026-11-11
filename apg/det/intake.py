"""Intake of the records the detection rules read that M3 and M4 did not ingest: supplier compliance evidence, commercial notices, delay events, plant hire, timesheets,
completed quantities and defects.  Blueprint: Section 04 (the same delivery rules as M3 and M4), Section 06 section 5 (the data each rule needs).

There is no third copy of the delivery loop: this module calls the M4 loop with its own entity rules (`specs`), which closes M4 finding F-16.  Quotes, purchase orders, amendments,
budgets, invoices and credits are already ingested by M3 and variations, retention and forecasts by M4; the detection run reads those where they are.

A record is USED by a rule only when its intrinsic outcome is accepted or accepted_with_warnings (fin.intake.usable).  A held, quarantined or conflicted record is never silently
used and never silently ignored: the rule lists it as a data-quality signal."""
import json, os
from ..fin import intake as FI

DET_SPECS = {
    'compliance': dict(material=('expiry_date',), positive=(), dates=()),
    'notice': dict(material=('notice_date',), positive=(), dates=('notice_date',)),
    'delay_event': dict(material=('start_date',), positive=(), nonnegative=('holding_rate_cents_per_day',), dates=('start_date',)),
    'plant_hire': dict(material=('rate_cents_per_day', 'on_hire_date'), positive=('rate_cents_per_day',), dates=('on_hire_date',)),
    'timesheet': dict(material=('ordinary_hours', 'work_date'), positive=(), dates=('work_date',)),
    'work_output': dict(material=('quantity', 'week_start'), positive=(), dates=('week_start',)),
    'defect': dict(material=('raised_date',), positive=(), nonnegative=('rework_cost_cents',), dates=('raised_date',)),
}
DET_ENTITIES = tuple(DET_SPECS)

DET_INTAKE_POLICY = FI.FinIntakePolicy(warn_unknown={
    'notice': ('linked_variation_ref', 'description_text'),
    'delay_event': ('activity_ref', 'end_date', 'working_days', 'recorded_cause_text', 'holding_rate_cents_per_day'),
    'plant_hire': ('off_hire_date', 'needed_until'),
    'timesheet': ('overtime_hours', 'rate_cents_per_hour'),
    'defect': ('subcontractor_text', 'trade_text', 'severity_text', 'rework_cost_cents', 'status_text')})

DET_FILES = [('TPL-BZ-COMPLIANCE', 'SRC-06_supplier_compliance/supplier_compliance.csv', 'compliance'), ('TPL-BZ-NOTICES', 'SRC-07_commercial/notices.csv', 'commercial'),
             ('TPL-BZ-DELAY-EVENTS', 'SRC-04_programme/delay_events.csv', 'programme'), ('TPL-BZ-PLANT-HIRE', 'SRC-13_plant/plant_hire.csv', 'plant'),
             ('TPL-BZ-TIMESHEETS', 'SRC-12_labour/timesheets.csv', 'labour'), ('TPL-BZ-WORK-OUTPUT', 'SRC-12_labour/work_output.csv', 'labour'),
             ('TPL-BZ-DEFECTS', 'SRC-08_quality/defects.csv', 'quality')]


def det_template(root, tid):
    return json.load(open(os.path.join(root, 'det_templates', tid + '.json'), encoding='utf-8'))


def det_files(root, tenant):
    out = []
    for tid, rel, src in DET_FILES:
        p = os.path.join(root, 'builder_zero', tenant, rel)
        if os.path.exists(p):
            out.append((det_template(root, tid), open(p, 'rb').read(), src, os.path.basename(p), None))
    return out


def ingest_det_file(scoped, clock, template, data, source, file_name='', policy=None, revision_field=None):
    return FI.ingest_fin_file(scoped, clock, template, data, source, file_name, policy or DET_INTAKE_POLICY, revision_field, specs=DET_SPECS)


usable = FI.usable
outcome = FI.outcome
