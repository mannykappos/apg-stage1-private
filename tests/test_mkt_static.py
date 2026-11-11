"""Static discipline for the procurement layer, checked on the source: pure rules (no clock, randomness, files, network or floats), consistent rule lists, regenerated templates and synthetic data, and no text
the layer produces that claims a realised saving, an approval, a compliance or a recommendation."""
import ast, os, re, subprocess, sys, tempfile, unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT
from apg.mkt import detect as MD, policy as MP, rules as R

MKT = os.path.join(HERE_ROOT, 'apg', 'mkt')
PURE = ['common', 'analysis', 'compare', 'demand', 'events', 'fresh', 'fx', 'intl', 'landed', 'opportunity', 'policy', 'purchasing', 'rules', 'scenarios', 'spec', 'suppliers']
FORBIDDEN = {'os', 'sys', 'json', 'csv', 'io', 'time', 'random', 'socket', 'subprocess', 'urllib', 'http', 'threading', 'uuid', 'secrets', 'decimal', 'math', 'hashlib', 'inspect'}
ALLOWED_STD = {'copy', 'dataclasses', 'datetime', 'hashlib', 'inspect', 'json', 'os'}
ALLOWED_EXTRA = {'golden_mkt': {'csv', 'fractions', 'io'}}      # the independent oracle reads the CSV files directly and calculates in exact fractions
TEST_DOUBLES = {'reference_m6', 'faulty_m6'}                  # EDR-08/09 test doubles: they take an INJECTED clock (a stand-in for the Engine's) and are never imported by the analysis code


def tree(mod):
    return ast.parse(open(os.path.join(MKT, mod + '.py'), encoding='utf-8').read())


def imports(t):
    out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            out |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0:
            out.add((n.module or '').split('.')[0])
    return out


class TestPurity(unittest.TestCase):
    def test_the_pure_modules_import_nothing_that_could_make_a_rule_impure(self):
        for m in PURE:
            self.assertEqual(imports(tree(m)) & FORBIDDEN, set(), m)

    def test_every_mkt_module_imports_only_the_standard_library_and_apg(self):
        for f in sorted(os.listdir(MKT)):
            if f.endswith('.py'):
                allowed = ALLOWED_STD | ALLOWED_EXTRA.get(f[:-3], set())
                self.assertTrue(imports(tree(f[:-3])) <= allowed, (f, imports(tree(f[:-3])) - allowed))

    def test_no_floating_point_and_no_hidden_io_in_the_pure_modules(self):
        for m in PURE:
            for n in ast.walk(tree(m)):
                if isinstance(n, ast.Constant):
                    self.assertNotIsInstance(n.value, float, f'{m}:{n.lineno}')
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    self.assertNotIn(n.func.id, ('float', 'round', 'eval', 'exec', 'open', 'print', 'input'), f'{m}:{n.lineno}')
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
                    self.fail(f'true division in {m}:{n.lineno}')

    def test_no_module_reads_the_clock_or_writes_to_a_store_outside_run_recording(self):
        for f in sorted(os.listdir(MKT)):
            if not f.endswith('.py') or f[:-3] in TEST_DOUBLES:
                continue
            t = tree(f[:-3])
            for n in ast.walk(t):
                if isinstance(n, ast.Attribute) and n.attr in ('now', 'utcnow', 'today'):
                    self.fail(f'{f}:{n.lineno} reads the clock')
        for f in [p for p in PURE if p != 'policy']:                                         # policy.py stores the two versioned configuration records and nothing else
            src = open(os.path.join(MKT, f + '.py'), encoding='utf-8').read()
            self.assertNotRegex(src, r'\.(put|store_policy|store_spec)\(', f)

    def test_the_analysis_modules_never_import_the_port_test_doubles(self):
        for m in PURE + ['detect', 'gather', 'intake', 'demo_mkt', 'golden_mkt']:
            src = open(os.path.join(MKT, m + '.py'), encoding='utf-8').read()
            self.assertNotRegex(src, r'reference_m6|faulty_m6|contracts_m6', m)

    def test_every_rule_function_takes_the_analysis_and_not_a_store_or_a_clock(self):
        for fn in [n for n in tree('rules').body if isinstance(n, ast.FunctionDef) and n.name.startswith(('mp0', 'mp1', 'mpd'))]:
            self.assertEqual([a.arg for a in fn.args.args], ['A', 'rl', 'run', 'project', 'as_of'], fn.name)

    def test_every_mkt_module_says_which_blueprint_text_it_answers(self):
        for f in sorted(os.listdir(MKT)):
            if f.endswith('.py') and f != '__init__.py':
                doc = ast.get_docstring(tree(f[:-3])) or ''
                self.assertTrue(any(k in doc for k in ('Blueprint', 'Section', 'EDR-0', 'RFC-01', 'M6')), f)


class TestConsistency(unittest.TestCase):
    def test_every_registered_rule_has_a_version_a_policy_entry_and_a_formula_id(self):
        ids = [rid for rid, _ in R.PROJECT_RULES + R.TENANT_RULES]
        self.assertEqual(sorted(set(ids)), sorted(set(MP.RULES) | {'MPD1'}))
        from apg.mkt import common as C
        self.assertEqual(sorted(set(ids)), sorted(C.RULE_VERSIONS))
        self.assertEqual(len(ids) - len(set(ids)), 1)                                        # MPD1 is registered at both scopes, nothing else

    def test_the_project_and_tenant_rule_lists_match_the_module_constants(self):
        self.assertEqual(tuple(r for r, _ in R.PROJECT_RULES), R.PROJECT_RULE_IDS)
        self.assertEqual(tuple(r for r, _ in R.TENANT_RULES), R.TENANT_RULE_IDS)

    def test_every_policy_parameter_a_rule_names_exists_in_the_schema_and_nothing_has_a_default(self):
        for rid, ent in MP.RULES.items():
            for path in ent[1]:
                head = path.split('.')[0]
                self.assertIn(head, MP.SCHEMA, (rid, path))
        demo = __import__('apg.mkt.demo_mkt', fromlist=['x']).demo_mkt_fields()
        for rid, ent in MP.RULES.items():
            for path in ent[1]:
                self.assertIsNotNone(MP.get_path(demo, path), (rid, path))

    def test_the_shipped_procurement_templates_regenerate_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE_ROOT, 'tools', 'make_mkt_templates.py'), d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            made = sorted(os.listdir(d))
            self.assertEqual(made, sorted(os.listdir(os.path.join(HERE_ROOT, 'mkt_templates'))))
            for n in made:
                self.assertEqual(open(os.path.join(d, n), 'rb').read(), open(os.path.join(HERE_ROOT, 'mkt_templates', n), 'rb').read(), n)

    def test_no_procurement_template_repeats_an_entity_that_an_earlier_milestone_already_ingests(self):
        import json
        from apg.mkt.intake import MKT_ENTITIES
        earlier = set()
        for d in ('ingest_templates', 'import_templates', 'fin_templates', 'det_templates'):
            for f in os.listdir(os.path.join(HERE_ROOT, d)):
                if f.endswith('.json'):
                    earlier.add(json.load(open(os.path.join(HERE_ROOT, d, f), encoding='utf-8')).get('entity'))
        self.assertEqual(set(MKT_ENTITIES) & earlier, set())

    def test_the_supplement_data_files_are_marked_synthetic(self):
        d = os.path.join(HERE_ROOT, 'mkt_data', 'zero_one')
        self.assertTrue(os.listdir(d))
        readme = os.path.join(HERE_ROOT, 'mkt_data', 'README.txt')
        if os.path.exists(readme):
            self.assertIn('SYNTHETIC', open(readme, encoding='utf-8').read())

    def test_the_policy_and_specification_demo_values_are_labelled_illustrative(self):
        from apg.mkt import demo_mkt as DM
        self.assertIn('ILLUSTRATIVE', DM.demo_mkt_policy()['note'].upper())
        self.assertIn('SYNTHETIC', DM.demo_mkt_spec()['note'].upper())


class TestClaimsScan(unittest.TestCase):
    """Text the layer can put in front of a person must not claim a realised saving, an approval, a compliance, a chosen supplier or a verified outcome."""
    BANNED = [r'\bsaved\b', r'\bproved?\b', r'\bfraud\b', r'\bnegligen', r'\bblame', r'\bguilty\b', r'\bcompliant\b', r'\bcleared\b', r'\bbest supplier\b', r'\bwe recommend\b', r'\byou should buy\b',
              r'\bapproved for production\b', r'\bguarantee']
    ALLOWED = ('does not declare', 'not declare', 'not a product compliant', 'nor declares', 'no supplier cleared', 'never declares', 'declare a product compliant', 'supplier cleared', 'not compliant', 'is not proof', 'needs a person', 'declares a product compliant', 'realised saving needs')

    def strings(self, mod):
        out = []
        for n in ast.walk(tree(mod)):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 20 and not n.value.startswith('apg-'):
                out.append((n.lineno, n.value))
            if isinstance(n, ast.JoinedStr):
                out.append((n.lineno, ''.join(p.value for p in n.values if isinstance(p, ast.Constant) and isinstance(p.value, str))))
        return out

    def test_no_rule_or_message_text_claims_a_realised_saving_an_approval_or_a_compliance(self):
        for mod in PURE:
            for line, s in self.strings(mod):
                low = s.lower()
                for pat in self.BANNED:
                    if re.search(pat, low) and not any(a in low for a in self.ALLOWED):
                        self.fail(f'{mod}:{line}: {s[:100]!r} matches {pat}')

    def test_the_word_realised_only_appears_to_say_nothing_is_realised(self):
        for mod in PURE:
            for line, s in self.strings(mod):
                low = s.lower()
                if re.search(r'\brealised\b', low):
                    self.assertTrue(any(a in low for a in ('never realised', 'not realised', 'no saving realised', 'not a realised', 'realised until', 'never be realised', 'cannot be realised', 'realised saving needs', 'realised outcome', 'reported as realised', 'always refuses')), f'{mod}:{line}: {s[:100]!r}')

    def test_the_savings_gate_has_no_path_that_returns_a_realised_status(self):
        src = open(os.path.join(MKT, 'opportunity.py'), encoding='utf-8').read()
        self.assertNotIn("'status': 'realised'", src)
        self.assertNotIn("'status': 'verified'", src)
        self.assertIn('SavingNotVerified', src)

    def test_human_approval_is_always_required_in_every_ranking_and_opportunity(self):
        src = open(os.path.join(MKT, 'compare.py'), encoding='utf-8').read() + open(os.path.join(MKT, 'opportunity.py'), encoding='utf-8').read()
        self.assertNotIn("'human_approval_required': False", src)
        self.assertNotIn('"human_approval_required": False', src)

    def test_no_market_provider_is_named_or_implied_in_the_code(self):
        for mod in PURE + ['intake', 'gather', 'demo_mkt', 'detect']:
            src = open(os.path.join(MKT, mod + '.py'), encoding='utf-8').read().lower()
            for w in ('bloomberg', 'reuters', 'refinitiv', 'lme.com', 'api key', 'api_key', 'requests.get', 'urlopen'):
                self.assertNotIn(w, src, (mod, w))


if __name__ == '__main__':
    unittest.main()
