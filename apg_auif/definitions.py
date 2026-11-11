"""Construction definitions for the AUIF canonical model, in the MODULE namespace (module.apg.*).  STATUS: PROPOSED - for review; never LOCKED here.

They are BUILT from what APG already has, so they invent no meaning:
  * the attributes of each definition are the target fields of the APG mapping template for that record type (the same names M3 stores), each with the template's
    APG type, whether it is required, and the source column it is read from;
  * the identifiers are the template's natural key;
  * the relationships are the reference fields APG's own code follows (the module named in `used_by`), written out once here;
  * missing and conflicting values are handled by the existing APG rules (named per field below), and anything AUIF cannot carry is stated.
`model()` derives the AUIF CanonicalModelDefinition (status PROPOSED) that the Fabric validates objects against.  Mapping these record types onto the CORE concepts
(Party, Agreement, Document, Change, ...) is a decision for the canonical-model owner (AUIF OD-08) and is NOT made here.
Generated files: auif_m8/definitions/construction_definitions.json and auif_m8/definitions/apg_canonical_model.json (tools/make_m8_config.py; a test checks they match)."""
import json, os
from . import layout

STATUS = 'PROPOSED'
MODEL_VERSION = '0.1.0'
MODULE_ID = 'apg'
PREFIX = 'module.%s.' % MODULE_ID

# reference fields APG follows.  entity -> [(attribute, target entity, target identifier attributes, required on the record, used_by)]
# used_by names the APG module that follows the reference; a test checks that the module really reads that field (or, for pm_invoice, the record kind).
SUP = 'apg/ingest/reconcile.py (supplier resolution by the apg/ingest/entities.py ladder; never forced)'
PRJ = 'apg/fin/snap.py (project_of: which project a record belongs to, for every calculation and rule)'
REL = {
    'supplier': [],
    'ap_invoice': [('supplier_ref', 'supplier', ['source_record_id'], True, SUP), ('project_ref', 'project', ['project_ref'], True, PRJ),
                   ('purchase_order_ref', 'purchase_order', ['source_record_id'], False, 'apg/ingest/reconcile.py (PO_PROJECT_MISMATCH, PO_COST_CODE_MISMATCH)'),
                   ('cost_code_ref', 'budget_line', ['project_ref', 'cost_code_ref'], False, 'apg/fin/costs.py (cost by cost code)')],
    'credit_note': [('supplier_ref', 'supplier', ['source_record_id'], True, SUP),
                    ('against_invoice_ref', 'ap_invoice', ['source_record_id'], True, 'apg/ingest/reconcile.py (credit and reissue lineage)')],
    'payment': [('invoice_ref', 'ap_invoice', ['source_record_id'], True, 'apg/ingest/reconcile.py (payment links)')],
    'purchase_order': [('supplier_ref', 'supplier', ['source_record_id'], True, SUP), ('project_ref', 'project', ['project_ref'], True, PRJ),
                       ('cost_code_ref', 'budget_line', ['project_ref', 'cost_code_ref'], False, 'apg/fin/commitments.py'),
                       ('material_ref', 'market_observation', ['material_ref'], False, 'apg/det/rules_cost.py (aggregation key)')],
    'po_amendment': [('purchase_order_ref', 'purchase_order', ['source_record_id'], True, 'apg/ingest/reconcile.py, apg/fin/commitments.py')],
    'supplier_quote': [('supplier_ref', 'supplier', ['source_record_id'], True, SUP),
                       ('material_ref', 'market_observation', ['material_ref'], True, 'apg/det/rules_cost.py (R07 quote comparison)')],
    'budget_line': [('project_ref', 'project', ['project_ref'], True, PRJ)],
    'fx_rate': [],
    'market_observation': [],
    'pm_invoice': [('source_record_id', 'ap_invoice', ['source_record_id'], True, 'apg/ingest/reconcile.py (pm_invoice: a secondary source of the same invoice, matched by record key)'),
                   ('supplier_ref', 'supplier', ['source_record_id'], True, SUP)],
    'project': [],
    'contract': [('project_ref', 'project', ['project_ref'], True, PRJ)],
    'variation': [('project_ref', 'project', ['project_ref'], True, PRJ)],
    'ctc_line': [('project_ref', 'project', ['project_ref'], True, PRJ), ('cost_code_ref', 'budget_line', ['project_ref', 'cost_code_ref'], True, 'apg/fin/forecast.py (cost to complete by cost code)')],
    'retention': [('project_ref', 'project', ['project_ref'], True, PRJ)],
    'security': [('project_ref', 'project', ['project_ref'], True, PRJ)],
    'facility': [],
    'bank_txn': [],
    'compliance': [('supplier_ref', 'supplier', ['source_record_id'], True, 'apg/det/common.py (compliance evidence by supplier)')],
    'notice': [('project_ref', 'project', ['project_ref'], True, PRJ), ('linked_variation_ref', 'variation', ['source_record_id'], False, 'apg/det/rules_commercial.py (R04B)')],
    'delay_event': [('project_ref', 'project', ['project_ref'], True, PRJ)],
    'plant_hire': [('project_ref', 'project', ['project_ref'], True, PRJ)],
    'timesheet': [('project_ref', 'project', ['project_ref'], True, PRJ),
                  ('work_package_ref', 'work_output', ['project_ref', 'work_package_ref'], True, 'apg/det/rules_ops.py (LAB: hours against completed quantities)')],
    'work_output': [('project_ref', 'project', ['project_ref'], True, PRJ)],
    'defect': [('project_ref', 'project', ['project_ref'], True, PRJ)],
}
NOT_A_RECORD_TYPE = {   # reference-like fields APG reads as text only: there is no APG record type behind them in the flow M8 carries
    'po_amendment': {'approved_change_ref': 'a change-approval reference; detection reads only whether it is present (apg/det/rules_cost.py)'},
    'delay_event': {'activity_ref': 'a programme activity; programme activities are not imported'},
    'ap_invoice': {'source_batch_ref': 'the accounting batch label; kept as text'},
}
NOT_CARRIED = {   # what the source layout itself does not hold, stated so nobody assumes it is there
    'ap_invoice': 'invoice line items (the Builder Zero accounting layout has one line per invoice), and the payment and credit links are held on the payment and credit records, '
                  'not on the invoice',
    'purchase_order': 'order lines beyond one material line per order; approved changes arrive as separate po_amendment records',
    'supplier_quote': 'quote tiers and terms (M6 market data, not carried in M8)',
}
COMMON_CANNOT_PRESERVE = [
    'Every value crosses AUIF as text (canonical type STRING) and is given its APG type (cents, date, decimal, enum, integer) by the unchanged APG mapping rules after delivery. '
    'AUIF has no calendar-date type (TIMESTAMP needs a time of day), and an AUIF INTEGER or DECIMAL column would make AUIF\'s file importer refuse a whole page for one bad cell '
    'where APG refuses or holds only that row; so the APG type is recorded in each attribute\'s constraints (apg_type) and enforced by APG, not by AUIF.',
    'The record\'s row number is its position in the delivery batch (blank rows skipped as M3 does), not a line of a file; the file name and file hash that M3 stores are replaced '
    'by the AUIF lineage (integration, source record, translation pack and hash, canonical id, observation, manifest).',
    'A column that is not in the template is not carried: any change to the columns is schema drift for AUIF and the assessment cannot proceed until the pack is revalidated '
    '(M3 would accept an extra column and keep its text).',
]
COMPOSITE_IDENTITY = ('APG-M8.1: this record type is identified by a composite natural key, and AUIF rev14 takes it as a composite source identity (the key fields\' text, '
                      'in key order, joined by "|", with "\\" and "|" escaped): the canonical id is stable across revisions of the same business record (finding M8-F2 '
                      'corrected).  APG-M8 to M8-R2, on AUIF rev13, had a content-hash canonical id for these record types.')
MISSING_AND_CONFLICT = [
    'A field absent from the delivered object: the batch is not applied and the assessment cannot proceed (MISSING_FIELD).',
    'A value of the wrong canonical type (not text): AUIF marks the object TRANSLATION_INVALID; the batch is not applied (TRANSLATION_INVALID).',
    'A blank value: as M3 - a blank required field rejects the row (and the assessment cannot proceed: ROW_REJECTED); a blank optional field is UNKNOWN, never zero: a material '
    'field is held (MATERIAL_VALUE_UNKNOWN), a field the intake policy tolerates is a warning (VALUE_MISSING), any other is held (CRITICAL_VALUE_MISSING).',
    'A value APG cannot parse (cents with a decimal point, a date not written as the template says, an unknown enum value): a required field rejects the row; an optional '
    'field is held as INVALID_VALUE; either way the assessment cannot proceed (ROW_REJECTED / VALUE_INVALID).',
    'The same key delivered again with the same content: a duplicate delivery, no second effect.  A higher declared source revision: a new revision.  A lower one: a stale '
    'delivery, recorded and not applied (the assessment cannot proceed: STALE_DELIVERY).  Different content with no way to order the versions: a quarantined conflict holding '
    'every version (the existing M3 contract; shown as an exclusion).',
    'Two sources disagreeing on a field the source-authority register governs: decided by the register in reconciliation (apg/ingest/reconcile.py), never by arrival order.',
    'A mapping AUIF marks AMBIGUOUS, or a field the pack does not map: the object is not delivered (AMBIGUOUS / TRANSLATION_INVALID) and the assessment cannot proceed.',
]


def concept_name(entity):
    return PREFIX + ''.join(p.capitalize() for p in entity.split('_'))


def load_templates(root):
    out = {}
    for fam, dirs in layout.TEMPLATE_DIRS.items():
        for d in dirs:
            for f in sorted(os.listdir(os.path.join(root, d))):
                if f.endswith('.json'):
                    t = json.load(open(os.path.join(root, d, f), encoding='utf-8'))
                    out[t['template_id']] = t
    return out


def _specs():
    from apg.ingest.specs import SPECS
    from apg.fin.intake import FIN_SPECS
    from apg.det.intake import DET_SPECS
    return {'m3': SPECS, 'fin': FIN_SPECS, 'det': DET_SPECS}


def _policies():
    from apg.ingest.demo_setup import DEMO_POLICY
    from apg.fin.demo_fin import FIN_INTAKE_POLICY
    from apg.det.intake import DET_INTAKE_POLICY
    return {'m3': DEMO_POLICY, 'fin': FIN_INTAKE_POLICY, 'det': DET_INTAKE_POLICY}


def effective_field(family, entity):
    """The business date of a record type: the first event date its intake rules name, or None (the record type carries no business date)."""
    d = _specs()[family][entity].get('dates', ())
    return d[0] if d else None


def construction_definitions(root):
    """-> list of definitions (one per record type in layout.ENTITIES), each status PROPOSED."""
    tpl, specs, pols, out = load_templates(root), _specs(), _policies(), []
    for fam, tid, folder, fname, src, rev in layout.ENTITIES:
        t = tpl[tid]
        ent = t['target_entity']
        spec = specs[fam][ent]
        col = {c['target_field']: c for c in t['columns']}
        key_fields = [next(c['target_field'] for c in t['columns'] if c['source_column'] == k) for k in t['natural_key']]
        attrs = []
        for c in t['columns']:
            tf = c['target_field']
            if c['required']:
                missing = 'required: a blank value rejects the row (REQUIRED_MISSING)'
            elif tf in spec.get('material', ()):
                missing = 'optional but material: a blank value is held (MATERIAL_VALUE_UNKNOWN)'
            elif tf in pols[fam].warn_unknown.get(ent, ()):
                missing = 'optional, tolerated by the demonstration intake policy: a blank value is a warning (VALUE_MISSING)'
            else:
                missing = 'optional, not tolerated: a blank value is held (CRITICAL_VALUE_MISSING)'
            cons = {'apg_type': c['type'], 'source_column': c['source_column'], 'transform': c.get('transform', 'none')}
            for k in ('date_format', 'allowed'):
                if c.get(k):
                    cons[k] = c[k]
            if c['type'] == 'money_cents':
                cons['money_unit'] = t['money']['unit']
            attrs.append({'name': tf, 'canonical_type': 'STRING', 'required': bool(c['required']), 'classification': 'FINANCIAL' if c['type'] == 'money_cents' else 'INTERNAL',
                          'constraints': cons, 'when_blank': missing,
                          'sign_rule': 'must be positive' if tf in spec.get('positive', ()) else ('must not be negative' if tf in spec.get('nonnegative', ()) else None)})
        rels = [{'attribute': a, 'to': concept_name(te), 'to_identifier': ti, 'required': req, 'used_by': ub} for a, te, ti, req, ub in REL[ent]]
        eff = effective_field(fam, ent)
        cannot = list(COMMON_CANNOT_PRESERVE)
        if ent in NOT_CARRIED:
            cannot.append('Not in the source layout: ' + NOT_CARRIED[ent] + '.')
        out.append({'concept': concept_name(ent), 'namespace': 'MODULE', 'status': STATUS, 'apg_entity': ent, 'intake_family': fam, 'template_id': tid,
                    'mapping_template_status': t['status'], 'attributes': attrs,
                    'identifiers': {'natural_key': key_fields, 'auif_identity_field': t['natural_key'][0] if len(key_fields) == 1 else list(t['natural_key']),
                                    'canonical_id': 'module.apg.<type>:<integration target system>:<%s>' % ('source identity field' if len(key_fields) == 1 else 'composite source identity (AUIF rev14)'),
                                    'composite_identity': COMPOSITE_IDENTITY if len(key_fields) > 1 else None},
                    'relationships': rels, 'text_references': NOT_A_RECORD_TYPE.get(ent, {}),
                    'effective_time': {'field': eff, 'basis': ('the record\'s %s' % eff) if eff else 'none: this record type carries no business date, so only the observed time is recorded'},
                    'revision_field': rev,
                    'missing_or_conflicting': MISSING_AND_CONFLICT, 'cannot_preserve': cannot,
                    'demonstrating_test': 'tests_m8/test_m8_definitions.py::DefinitionDemonstrations::test_%s' % ent})
    return out


def model(defs):
    """The AUIF CanonicalModelDefinition (status PROPOSED) for the definitions."""
    return {'contract_kind': 'CanonicalModelDefinition', 'model_version': MODEL_VERSION, 'status': STATUS,
            'concepts': [{'name': d['concept'], 'namespace': 'MODULE', 'extension_rules': {'module_extension_allowed': False},
                          'attributes': [{'name': a['name'], 'type': a['canonical_type'], 'required': a['required'], 'default_classification': a['classification'],
                                          'constraints': a['constraints'], 'description': 'APG %s field read from source column %r (APG type %s)' % (d['apg_entity'], a['constraints']['source_column'], a['constraints']['apg_type'])}
                                         for a in d['attributes']]} for d in defs],
            'compatibility': {'backward_compatible_with': [MODEL_VERSION], 'breaking_change_policy': 'PROPOSED model: any change is a new version; packs pin the range they support.'},
            'deterministic_validation': {'rules_ref': 'apg-m8-rules-0.1.0'}}


def by_entity(defs):
    return {d['apg_entity']: d for d in defs}
