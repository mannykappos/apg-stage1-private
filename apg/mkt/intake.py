"""Intake of the procurement records earlier milestones did not ingest.  Blueprint: Section 04 (the same delivery rules as M3, M4 and M5), Section 08 sections 4 (demand, specification,
deliveries), 5 (what a quote captures), 6 (landed-cost components), 12 (import checks).

There is no fourth copy of the delivery loop: this module calls the M4 loop with its own entity rules (`specs`), exactly as M5 does.  Quotes, purchase orders, amendments, market observations
and FX rates are already ingested by M3 and are read where they are.

Three of the nine templates map Builder Zero files (material master, material demand, delivery dockets).  The other six map SYNTHETIC SUPPLEMENT files (mkt_data/), written for this
milestone because no Builder Zero file carries them: specification requirements a person approved, readings of quote text with their human verification, quote tiers and terms, landed-cost
assumptions, and import-check outcomes.  The supplement files say so in their names and are not part of the frozen Builder Zero manifest.

A record is USED by a rule only when its intrinsic outcome is accepted or accepted_with_warnings (fin.intake.usable).  A held, quarantined or conflicted record is never silently used and
never silently ignored: MPD1 lists it."""
import json, os
from ..fin import intake as FI

MKT_SPECS = {
    'material': dict(material=('unit_text',), positive=(), dates=()),
    'material_demand': dict(material=('quantity', 'required_date'), positive=(), dates=()),            # a required-on-site date is in the future by nature: it is not a future-dating error
    'delivery': dict(material=('qty_delivered', 'delivery_date'), positive=(), dates=('delivery_date',)),
    'spec_requirement': dict(material=('material_ref',), positive=(), dates=('approved_on',)),
    'quote_reading': dict(material=('value_text',), positive=(), dates=('verified_on',)),
    'quote_tier': dict(material=('unit_rate_minor_units', 'min_quantity'), positive=('unit_rate_minor_units',), dates=()),
    'quote_term': dict(material=('value_text',), positive=(), dates=()),
    'landed_assumption': dict(material=(), positive=(), nonnegative=('per_unit_minor_units', 'rate_bps'), dates=('set_on',)),
    'import_check': dict(material=('status_text',), positive=(), dates=('checked_on',)),
}
MKT_ENTITIES = tuple(MKT_SPECS)

MKT_INTAKE_POLICY = FI.FinIntakePolicy(warn_unknown={
    'material': ('description_text',),
    'delivery': ('qty_accepted',),
    'spec_requirement': ('basis_ref', 'approved_by', 'approved_on'),
    'quote_reading': ('verified_by', 'verified_on'),
    'landed_assumption': ('per_unit_minor_units', 'rate_bps', 'currency_code', 'basis_text', 'source_ref', 'set_by', 'set_on'),
    'import_check': ('evidence_ref', 'checked_by', 'checked_on')})

# (template id, file under builder_zero/<tenant>/ or mkt_data/<tenant>/, source identity, where)
MKT_FILES = [('TPL-BZ-MATERIALS', 'reference/materials.csv', 'master', 'bz'), ('TPL-BZ-MATERIAL-DEMAND', 'SRC-05_materials/material_demand.csv', 'materials', 'bz'),
             ('TPL-BZ-DELIVERIES', 'SRC-05_materials/deliveries.csv', 'materials', 'bz'),
             ('TPL-MKT-SPEC-REQUIREMENTS', 'spec_requirements.csv', 'specification', 'sup'), ('TPL-MKT-QUOTE-READINGS', 'quote_readings.csv', 'procurement', 'sup'),
             ('TPL-MKT-QUOTE-TIERS', 'quote_tiers.csv', 'procurement', 'sup'), ('TPL-MKT-QUOTE-TERMS', 'quote_terms.csv', 'procurement', 'sup'),
             ('TPL-MKT-LANDED-ASSUMPTIONS', 'landed_assumptions.csv', 'procurement', 'sup'), ('TPL-MKT-IMPORT-CHECKS', 'import_checks.csv', 'procurement', 'sup')]


def mkt_template(root, tid):
    return json.load(open(os.path.join(root, 'mkt_templates', tid + '.json'), encoding='utf-8'))


def mkt_files(root, tenant):
    out = []
    for tid, rel, src, where in MKT_FILES:
        p = os.path.join(root, 'builder_zero' if where == 'bz' else 'mkt_data', tenant, rel)
        if os.path.exists(p):
            out.append((mkt_template(root, tid), open(p, 'rb').read(), src, os.path.basename(p), None))
    return out


def ingest_mkt_file(scoped, clock, template, data, source, file_name='', policy=None, revision_field=None):
    return FI.ingest_fin_file(scoped, clock, template, data, source, file_name, policy or MKT_INTAKE_POLICY, revision_field, specs=MKT_SPECS)


usable = FI.usable
outcome = FI.outcome
