"""Which Builder Zero file reaches APG through which AUIF integration (SYNTHETIC configuration, no real system).

ENTITIES lists every record type APG's import paths read for the financial core and detection, in the order M3 loads them (apg.ingest.demo_setup.files_for, then
apg.fin.demo_fin.FIN_FILES, then apg.det.intake.DET_FILES), with the same template, file, source identity and revision field.  A test checks this table against those
three lists, so the AUIF path cannot quietly read a different file or call a source by another name.

One AUIF integration is one synthetic "source system": the files of one APG source identity in one Builder Zero folder (AUIF's file importer reads one folder).  The
APG source identity (accounting, procurement, ...) is what the source-authority register is written against, so it must be the same on both paths.
Market data for M6 (mkt_templates) is not carried in M8 (the authorised flow is the financial core and detection)."""
from collections import OrderedDict

# (family, template id, folder, file, apg source, revision field)   family: m3 = apg.ingest (M3), fin = apg.fin.intake (M4), det = apg.det.intake (M5)
ENTITIES = (
    ('m3', 'TPL-BZ-SUPPLIERS', 'reference', 'suppliers.csv', 'master', None),
    ('m3', 'TPL-BZ-AP-INVOICES', 'SRC-01_accounting', 'ap_invoices.csv', 'accounting', None),
    ('m3', 'TPL-BZ-CREDIT-NOTES', 'SRC-01_accounting', 'credit_notes.csv', 'accounting', None),
    ('m3', 'TPL-BZ-PAYMENTS', 'SRC-01_accounting', 'payments.csv', 'accounting', None),
    ('m3', 'TPL-BZ-PURCHASE-ORDERS', 'SRC-03_procurement', 'purchase_orders.csv', 'procurement', None),
    ('m3', 'TPL-BZ-PO-AMENDMENTS', 'SRC-03_procurement', 'po_amendments.csv', 'procurement', None),
    ('m3', 'TPL-BZ-QUOTES', 'SRC-03_procurement', 'quotes.csv', 'procurement', None),
    ('m3', 'TPL-BZ-BUDGET-LINES', 'SRC-02_costing', 'budget_lines.csv', 'job_costing', 'source_revision_label'),
    ('m3', 'TPL-BZ-FX-RATES', 'SRC-10_market', 'fx_rates.csv', 'market', None),
    ('m3', 'TPL-BZ-MARKET-OBSERVATIONS', 'SRC-10_market', 'market_observations.csv', 'market', None),
    ('m3', 'TPL-BZ-PM-INVOICES', 'conflicting_sources', 'pm_system_invoices.csv', 'pm_system', None),
    ('fin', 'TPL-BZ-PROJECTS', 'reference', 'projects.csv', 'job_costing', None),
    ('fin', 'TPL-BZ-CONTRACTS', 'SRC-07_commercial', 'contracts.csv', 'commercial', None),
    ('fin', 'TPL-BZ-VARIATIONS', 'SRC-07_commercial', 'variations.csv', 'commercial', None),
    ('fin', 'TPL-BZ-CTC-FORECASTS', 'SRC-02_costing', 'forecasts.csv', 'job_costing', None),
    ('fin', 'TPL-BZ-RETENTION', 'SRC-09_retentions', 'retention_ledger.csv', 'retention_ledger', None),
    ('fin', 'TPL-BZ-SECURITY', 'SRC-09_retentions', 'security_instruments.csv', 'retention_ledger', None),
    ('fin', 'TPL-BZ-FACILITY', 'SRC-14_bank', 'funding_facility.csv', 'bank', None),
    ('fin', 'TPL-BZ-BANK', 'SRC-14_bank', 'bank_transactions.csv', 'bank', None),
    ('det', 'TPL-BZ-COMPLIANCE', 'SRC-06_supplier_compliance', 'supplier_compliance.csv', 'compliance', None),
    ('det', 'TPL-BZ-NOTICES', 'SRC-07_commercial', 'notices.csv', 'commercial', None),
    ('det', 'TPL-BZ-DELAY-EVENTS', 'SRC-04_programme', 'delay_events.csv', 'programme', None),
    ('det', 'TPL-BZ-PLANT-HIRE', 'SRC-13_plant', 'plant_hire.csv', 'plant', None),
    ('det', 'TPL-BZ-TIMESHEETS', 'SRC-12_labour', 'timesheets.csv', 'labour', None),
    ('det', 'TPL-BZ-WORK-OUTPUT', 'SRC-12_labour', 'work_output.csv', 'labour', None),
    ('det', 'TPL-BZ-DEFECTS', 'SRC-08_quality', 'defects.csv', 'quality', None),
)
TEMPLATE_DIRS = {'m3': ('import_templates', 'ingest_templates'), 'fin': ('fin_templates',), 'det': ('det_templates',)}


def integration_id(source, folder):
    """bz-<source>, or bz-<source>-<folder> when one source spans two folders (job costing reads reference/projects.csv and SRC-02_costing/)."""
    folders = sorted({e[2] for e in ENTITIES if e[4] == source})
    base = 'bz-' + source.replace('_', '-')
    return base if len(folders) == 1 or folder == folders[0] else base + '-' + folder.lower().replace('_', '-')


def integrations():
    """-> OrderedDict integration_id -> {'source', 'folder', 'files': [(template id, file, family, revision field), ...]} (first appearance order)."""
    out = OrderedDict()
    for fam, tid, folder, fname, src, rev in ENTITIES:
        i = out.setdefault(integration_id(src, folder), {'source': src, 'folder': folder, 'files': []})
        i['files'].append((tid, fname, fam, rev))
    return out


def by_template():
    return {e[1]: dict(family=e[0], template_id=e[1], folder=e[2], file=e[3], source=e[4], revision_field=e[5], integration_id=integration_id(e[4], e[2])) for e in ENTITIES}
