"""The construction definitions (MODULE namespace, status PROPOSED).  Each definition names its demonstrating test; DefinitionDemonstrations holds one per record type, generated
below.  Each demonstration runs that record type's Builder Zero file through AUIF and checks: the same APG records as the M3 path (provenance apart); complete lineage; the
relationship and identifier fields are carried; a blank required identifier stops the assessment (M3 rejects the row; APG-M8.1 on rev14 refuses the batch); and a missing column stops the
assessment with nothing stored."""
import os, re, shutil, unittest
from ._auif import (HERE_ROOT, client, codes, comparable, copy_folder, layout, m3_ingest, records, rewrite_csv, single, status, world)
from apg_auif import definitions as DEF, lineage

CFG = client.load_config(HERE_ROOT)
DEFS = DEF.by_entity(CFG['definitions'])


class TestDefinitions(unittest.TestCase):
    def test_every_definition_and_the_model_are_proposed_in_the_module_namespace(self):
        self.assertEqual(CFG['model']['status'], 'PROPOSED')
        self.assertEqual(len(CFG['definitions']), len(layout.ENTITIES))
        for d in CFG['definitions']:
            self.assertEqual((d['status'], d['namespace']), ('PROPOSED', 'MODULE'))
            self.assertRegex(d['concept'], r'^module\.apg\.[A-Z][A-Za-z0-9]*$')
        from auif.canonical import CanonicalModel
        CanonicalModel(CFG['model'])

    def test_each_definition_states_everything_the_authorisation_asks_for(self):
        tpl = DEF.load_templates(HERE_ROOT)
        for d in CFG['definitions']:
            with self.subTest(d['apg_entity']):
                t = tpl[d['template_id']]
                self.assertEqual([a['name'] for a in d['attributes']], [c['target_field'] for c in t['columns']])
                self.assertEqual(d['identifiers']['natural_key'], [next(c['target_field'] for c in t['columns'] if c['source_column'] == k) for k in t['natural_key']])
                self.assertTrue(d['missing_or_conflicting'] and d['cannot_preserve'])
                self.assertIn('effective_time', d)
                m = re.fullmatch(r'tests_m8/test_m8_definitions\.py::DefinitionDemonstrations::(test_\w+)', d['demonstrating_test'])
                self.assertTrue(m and hasattr(DefinitionDemonstrations, m.group(1)), d['demonstrating_test'])
                if len(d['identifiers']['natural_key']) > 1:                     # APG-M8.1: a composite key IS preserved on rev14 (M8-F2 corrected)
                    self.assertEqual(len(d['identifiers']['auif_identity_field']), len(d['identifiers']['natural_key']))      # the source columns of the key, in key order
                    self.assertIn('M8-F2', d['identifiers']['composite_identity'])
                    self.assertFalse(any('M8-F2' in c for c in d['cannot_preserve']))

    def test_every_relationship_names_code_that_really_follows_it(self):
        for d in CFG['definitions']:
            for r in d['relationships']:
                with self.subTest(d['apg_entity'] + '.' + r['attribute']):
                    self.assertIn(r['attribute'], [a['name'] for a in d['attributes']])
                    self.assertIn(r['to'], {x['concept'] for x in CFG['definitions']})
                    f = re.findall(r'apg/[a-z_/]+\.py', r['used_by'])[0]
                    token = 'pm_invoice' if (d['apg_entity'], r['attribute']) == ('pm_invoice', 'source_record_id') else r['attribute']
                    self.assertIn(token, open(os.path.join(HERE_ROOT, f), encoding='utf-8').read())


def _demo(entity):
    def test(self):
        d = DEFS[entity]
        info = layout.by_template()[d['template_id']]
        iid, fam, rev = info['integration_id'], info['family'], info['revision_field']
        tpl = DEF.load_templates(HERE_ROOT)[d['template_id']]
        # 1. the same records as M3, with complete lineage
        w = single(iid)
        s = w['env'].import_entity('zero_one', iid, entity)
        self.assertEqual(s['status'], 'applied', s['reasons'][:3])
        clock, prov, store, audit, who = world()
        m3 = who('m3', 'zero_one', 'ann')
        data = open(os.path.join(HERE_ROOT, 'builder_zero', 'zero_one', info['folder'], info['file']), 'rb').read()
        rc = m3_ingest(m3, clock, tpl, data, info['source'], info['file'], fam, rev)
        got, want = records(w['s'], entity), records(m3, entity)
        self.assertTrue(want)
        self.assertEqual({k: comparable(v) for k, v in got.items()}, {k: comparable(v) for k, v in want.items()})
        self.assertEqual(s['receipt']['counts'], rc['counts'])
        for k, v in got.items():
            self.assertEqual(lineage.record_problems(v, k), [])
        self.assertEqual(status(w['s'], w['env'], expected=[(iid, entity)])['status'], 'can_assess')
        # 2. relationship and identifier fields are carried on every record (known, or explicitly unknown with a reason)
        for k, v in got.items():
            if v.get('conflict'):
                continue
            for r in d['relationships'] + [{'attribute': a} for a in d['identifiers']['natural_key']]:
                self.assertTrue(r['attribute'] in v['fields'] or r['attribute'] in v['unknown'], (k, r['attribute']))
        # 3. a blank required identifier: M3 rejects the row; the AUIF path refuses the batch; the assessment cannot proceed either way
        tmp = copy_folder('zero_one', info['folder'])
        try:
            col = tpl['natural_key'][0]
            def blank(h, b):
                b[0][h.index(col)] = ''
                return h, b
            rewrite_csv(os.path.join(tmp, info['file']), blank)
            w2 = single(iid, base_dir=tmp)
            s2 = w2['env'].import_entity('zero_one', iid, entity)
            rc2 = m3_ingest(who('m3b', 'zero_one', 'ann'), clock, tpl, open(os.path.join(tmp, info['file']), 'rb').read(), info['source'], info['file'], fam, rev)
            self.assertEqual(rc2['results'][0]['codes'], ['REQUIRED_MISSING'])
            st2 = status(w2['s'], w2['env'], expected=[(iid, entity)])
            # APG-M8.1: the blank value is (part of) AUIF rev14's source identity, single or composite: AUIF refuses that record (IDENTITY_MISSING) and reads on, and
            # the batch is refused whole (stricter than M3, which rejects the row).  On rev13 a single-field identity made sync raise (M8-F6) and a composite one fell
            # back to a content hash, so M3's row rejection was reproduced; both are corrected in rev14 (M8-F2, M8-F6).
            self.assertEqual(s2['status'], 'blocked')
            self.assertIn('IDENTITY_MISSING', {c for c, _ in s2['reasons']})
            self.assertNotIn('AUIF_RAISED', {c for c, _ in s2['reasons']})
            self.assertEqual(len(w2['s'].query(entity)), 0)
            self.assertIn('IDENTITY_MISSING', codes(st2))
        finally:
            shutil.rmtree(tmp)
        # 4. a missing column: schema drift, nothing stored, the assessment cannot proceed
        tmp = copy_folder('zero_one', info['folder'])
        try:
            last = tpl['columns'][-1]['source_column']
            rewrite_csv(os.path.join(tmp, info['file']), lambda h, b: ([x for x in h if x != last], [[c for x, c in zip(h, r) if x != last] for r in b]))
            w3 = single(iid, base_dir=tmp)
            s3 = w3['env'].import_entity('zero_one', iid, entity)
            self.assertEqual(s3['status'], 'blocked')
            self.assertEqual(len(w3['s'].query(entity)), 0)
            st = status(w3['s'], w3['env'], expected=[(iid, entity)])
            self.assertEqual(st['status'], 'cannot_assess')
            self.assertIn('INTEGRATION_NOT_ACTIVE', codes(st))
        finally:
            shutil.rmtree(tmp)
    test.__doc__ = 'Demonstration for %s (%s).' % (DEFS[entity]['concept'], entity)
    return test


class DefinitionDemonstrations(unittest.TestCase):
    pass


for _e in DEFS:
    setattr(DefinitionDemonstrations, 'test_' + _e, _demo(_e))


if __name__ == '__main__':
    unittest.main()
