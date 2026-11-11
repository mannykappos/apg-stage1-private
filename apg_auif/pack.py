"""The SYNTHETIC translation packs (configuration only) and the file-import connectors for the Builder Zero integrations.

One pack per integration.  Every mapping is a one-to-one IDENTITY from a source column to the attribute of the same APG meaning (the template's target field): nothing is
converted, combined, defaulted or guessed inside AUIF.  The packs are generated deterministically from the APG templates and the construction definitions; their mappings
carry AUIF's executable state VALIDATED (in AUIF that means "deterministic validation performed": tools/make_m8_config.py checks every mapping against the template) and
proposed_by DETERMINISTIC_TOOL.  That is NOT an approval: the packs themselves are pack_state CANDIDATE and the canonical model they target is PROPOSED.
Columns the pack does not map make the object TRANSLATION_INVALID (default_outcome REJECTED).  Packs are read-only: every outbound half is "not supported"."""
import os
from . import definitions as DEF, layout

PACK_VERSION = '0.1.0'
CONNECTOR = ('generic-file-import', '0.1.0')                 # AUIF's own unchanged file importer (auif_ext.connectors.file_import)
TARGET_KIND = 'synthetic-builder-zero-csv-export'
READ_ONLY = 'APG imports only: it never writes to a source system'


def field_ref(concept, attr):
    """The contract form 'module.apg.<Type>.<attribute>': the concept's full name, then the attribute.  APG-M8.1 (on AUIF rev14, which reads the attribute after the
    concept's full name: finding M8-F1 corrected) ends DEV-M8-01, under which APG-M8 to M8-R2 wrote '<Type>.<attribute>' because AUIF rev13 split at the FIRST dot.
    This is the ONLY form this function produces; check_field_ref refuses any other, including the old deviation form (which rev14 itself also refuses when the pack is
    registered)."""
    if not concept.startswith(DEF.PREFIX):
        raise ValueError('not an APG module concept: %r' % concept)
    return '%s.%s' % (concept, attr)


def check_field_ref(mapping, entity_mapping):
    """-> problems ([] = the FIELD mapping is exactly the contract form for the concept its ENTITY mapping names)."""
    c = entity_mapping['canonical_ref']
    want_prefix = c + '.' if c.startswith(DEF.PREFIX) else None
    ref = mapping['canonical_ref']
    if want_prefix is None or not ref.startswith(want_prefix) or '.' in ref[len(want_prefix):] or not ref[len(want_prefix):]:
        return ['%s: %r is not the contract form %s<attribute>' % (mapping['mapping_id'], ref, want_prefix)]
    return []


def pack_id(iid):
    return 'apg-m8-' + iid


def _evidence(kind, obj, ident):
    from auif.util import evidence
    return evidence(kind, obj, ident)


def _check_mapping(defn, col):
    """The deterministic validation behind every VALIDATED mapping: the source column and the attribute are the same column and field of the APG template."""
    a = next((x for x in defn['attributes'] if x['constraints']['source_column'] == col), None)
    if a is None:
        raise ValueError('column %r is not in the template for %s' % (col, defn['apg_entity']))
    return a['name']


def mappings_for(defn):
    ent, out = defn['apg_entity'], []
    out.append({'mapping_id': 'm8-%s-entity' % ent.replace('_', '-'), 'kind': 'ENTITY', 'source_ref': ent, 'canonical_ref': defn['concept'], 'mapping_state': 'VALIDATED',
                'proposed_by': 'DETERMINISTIC_TOOL', 'deterministic_validation_performed': True,
                'validation_ref': _evidence('mapping-validation', {'entity': ent, 'concept': defn['concept'], 'template': defn['template_id']}, 'val-apg-m8-%s' % ent.replace('_', '-')),
                'inbound': {'source_type': 'entity', 'canonical_type': defn['concept'], 'transform': {'kind': 'IDENTITY', 'parameters': {}, 'deterministic': True}},
                'outbound': {'supported': False, 'reason': READ_ONLY}})
    for a in defn['attributes']:
        col = a['constraints']['source_column']
        attr = _check_mapping(defn, col)
        mid = 'm8-%s-%s' % (ent.replace('_', '-'), attr.replace('_', '-'))
        out.append({'mapping_id': mid, 'kind': 'FIELD', 'source_ref': '%s.%s' % (ent, col), 'canonical_ref': field_ref(defn['concept'], attr), 'mapping_state': 'VALIDATED',
                    'proposed_by': 'DETERMINISTIC_TOOL', 'deterministic_validation_performed': True,
                    'validation_ref': _evidence('mapping-validation', {'mapping': mid, 'column': col, 'attribute': attr, 'template': defn['template_id']}, 'val-apg-m8-' + mid[3:]),
                    'inbound': {'source_type': 'string', 'canonical_type': 'STRING', 'transform': {'kind': 'IDENTITY', 'parameters': {}, 'deterministic': True}},
                    'outbound': {'supported': False, 'reason': READ_ONLY}})
    return out


def build_pack(iid, defs_by_entity, entities, fingerprints, version=PACK_VERSION):
    from auif.translation import pack_hash
    ms = []
    for e in entities:
        ms += mappings_for(defs_by_entity[e])
    p = {'contract_kind': 'TranslationPack', 'pack_id': pack_id(iid), 'pack_version': version, 'artifact_hash': '0' * 64, 'immutable': True, 'contains_governance_logic': False,
         'contains_secrets': False, 'pack_state': 'CANDIDATE', 'target_system_kind': TARGET_KIND, 'schema_expectations': {'compatible_fingerprints': sorted(set(fingerprints))},
         'canonical_model_compat': {'min': DEF.MODEL_VERSION, 'max': '0.1.99'}, 'auif_contract_compat': {'min': '1.0.0', 'max': '1.0.99'}, 'mappings': ms,
         'unmapped_field_policy': {'default_outcome': 'REJECTED', 'ignored_by_rule': [], 'optional_and_unused': []},
         'classification_mappings': [], 'provenance_rules': {'preserve_source_object': True, 'preserve_source_field': True, 'preserve_pack_identity': True}}
    p['artifact_hash'] = pack_hash(p)
    return p


def form_problems(p):
    """The reference-form check over a whole pack: every FIELD mapping is in the contract form for its entity's concept (APG-M8.1: DEV-M8-01 has ended)."""
    ents = {m['source_ref']: m for m in p['mappings'] if m['kind'] == 'ENTITY'}
    out = []
    for m in p['mappings']:
        if m['kind'] == 'FIELD':
            e = ents.get(m['source_ref'].split('.', 1)[0])
            out += ['%s: no ENTITY mapping for its source' % m['mapping_id']] if e is None else check_field_ref(m, e)
        elif m['kind'] == 'ENTITY' and not m['canonical_ref'].startswith(DEF.PREFIX):
            out.append('%s: the ENTITY mapping must keep the full %s<Type> name' % (m['mapping_id'], DEF.PREFIX))
    return out


def ref(p):
    return {'id': p['pack_id'], 'version': p['pack_version'], 'hash': p['artifact_hash']}


def file_specs(root, tenant, iid, templates):
    """-> OrderedDict entity -> FileSpec for the files of this integration that exist for this tenant (the AUIF entity name is the APG record type)."""
    from collections import OrderedDict
    from auif_ext.connectors.file_import import FileSpec
    info = layout.integrations()[iid]
    out = OrderedDict()
    for tid, fname, fam, rev in info['files']:
        t = templates[tid]
        if os.path.exists(os.path.join(root, 'builder_zero', tenant, info['folder'], fname)):
            out[t['target_entity']] = FileSpec(fname, fmt='csv', types={}, delimiter=t['file']['delimiter'])
    return out


def connector(root, tenant, iid, templates, specs=None, base_dir=None):
    from auif_ext.connectors.file_import import FileImportConnector
    base = base_dir or os.path.join(root, 'builder_zero', tenant, layout.integrations()[iid]['folder'])
    return FileImportConnector(base, specs or file_specs(root, tenant, iid, templates), connector_id=CONNECTOR[0], version=CONNECTOR[1])


def fingerprint_of(conn):
    from auif.discovery import fingerprint
    return fingerprint(conn.discover())['value']
