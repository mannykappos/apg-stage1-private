"""Demonstration set-up for the financial core on Builder Zero.  EVERYTHING HERE IS SYNTHETIC OR ILLUSTRATIVE: the policy below is NOT an approved policy for any real builder;
its method choices, status mappings, funded share and freshness limits are the builder's demonstration choices and are NOT product-owner decisions (CR-02 A2 to A13 are
open).  Real values come from a policy owner's approval and from the pilot."""
import json, os
from .. import tenancy
from ..ingest import demo_setup as D, pipeline as P3, reconcile as R3
from . import intake, policy as P

ILLUSTRATIVE_NOTE = 'SYNTHETIC / ILLUSTRATIVE demonstration policy - not a product decision'

FIN_INTAKE_POLICY = intake.FinIntakePolicy(warn_unknown={
    'project': ('project_name', 'contract_value_cents', 'start_date', 'planned_finish'), 'contract': ('approved_variations_cents',), 'variation': ('value_cents', 'description_text'),
    'ctc_line': ('estimate_basis_text', 'movement_reason_text'), 'retention': ('release_due_date', 'released_date', 'hold_reason_text'), 'security': ('expiry_date',),
    'bank_txn': ('description_text',)})

FIN_FILES = [('TPL-BZ-PROJECTS', 'reference/projects.csv', 'job_costing'), ('TPL-BZ-CONTRACTS', 'SRC-07_commercial/contracts.csv', 'commercial'),
             ('TPL-BZ-VARIATIONS', 'SRC-07_commercial/variations.csv', 'commercial'), ('TPL-BZ-CTC-FORECASTS', 'SRC-02_costing/forecasts.csv', 'job_costing'),
             ('TPL-BZ-RETENTION', 'SRC-09_retentions/retention_ledger.csv', 'retention_ledger'), ('TPL-BZ-SECURITY', 'SRC-09_retentions/security_instruments.csv', 'retention_ledger'),
             ('TPL-BZ-FACILITY', 'SRC-14_bank/funding_facility.csv', 'bank'), ('TPL-BZ-BANK', 'SRC-14_bank/bank_transactions.csv', 'bank')]


def fin_template(root, tid):
    return json.load(open(os.path.join(root, 'fin_templates', tid + '.json'), encoding='utf-8'))


def fin_files(root, tenant):
    out = []
    for tid, rel, src in FIN_FILES:
        p = os.path.join(root, 'builder_zero', tenant, rel)
        if os.path.exists(p):
            out.append((fin_template(root, tid), open(p, 'rb').read(), src, os.path.basename(p), None))
    return out


def demo_policy(version='SYN-FIN-POL-1', proposer='synthetic.proposer', **override):
    """The demonstration policy as PROPOSED (APG-F67: it carries no approval; `install` stores it and has the owner approve it in person)."""
    fields = dict(
        recognition_method='cost_to_cost',
        ctc_method={'default': 'declared_else_budget_less_actual'},
        ffc_basis='actual_to_forecast_date_plus_ctc',
        tax_basis='ex_gst',
        cost_scope=['supplier_invoices'],
        variation_status_map={'approved': 'approved', 'submitted': 'unapproved', 'rejected': 'rejected', 'disputed': 'disputed'},
        po_status_map={'open': 'committed', 'draft': 'draft', 'cancelled': 'cancelled', 'closed': 'closed'},
        credit_reopens_commitment=False,
        freshness_days={'forecast': 45, 'budget': 730, 'facility': 45},                    # ILLUSTRATIVE days
        carrying={'eligibility': 'as_of_to_release_due_date', 'rate_source': 'facility', 'day_count_basis': 365, 'funded_share_bps': 5000,        # funded share ILLUSTRATIVE
                  'overlap': 'cost_scope_excludes_financing_costs'},
        cash_adjustment={'base': 'forecast_final', 'components': ['retention_carrying']},
        note=ILLUSTRATIVE_NOTE)
    fields.update(override)
    return P.new_policy(version, proposer, **fields)


def install(scoped, clock, owner=None, version='SYN-FIN-POL-1', **override):
    """Store the demonstration policy proposed by the person of `scoped` and, when the owner's own session is given, approve it from that session (APG-F67).  -> the stored payload."""
    P.store_policy(scoped, demo_policy(version, scoped.ctx.user_id, **override))
    if owner is not None:
        return P.approve_policy(owner, clock, version, 'SYNTHETIC demonstration: approved by the demonstration owner in person')
    return scoped.get(P.POLICY_KIND, version).payload


def load_zero(root, scoped, clock, tenant='zero_one', register=None, as_of='2026-09-30'):
    """Ingest the M3 files and the fin files for one Builder Zero tenant, reconcile with the SYNTHETIC register.  -> receipts."""
    receipts = {}
    for t, data, src, name, rev in D.files_for(root, tenant):
        receipts[name] = P3.ingest_file(scoped, clock, t, data, src, name, D.DEMO_POLICY, rev)
    for t, data, src, name, rev in fin_files(root, tenant):
        receipts[name] = intake.ingest_fin_file(scoped, clock, t, data, src, name, FIN_INTAKE_POLICY, rev)
    R3.reconcile(scoped, register or D.demo_register(), as_of)
    return receipts
