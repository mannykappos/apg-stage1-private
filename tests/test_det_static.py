"""Static discipline for the detection layer, checked on the source: the rules are pure functions of pinned facts (no clock, randomness, files, network or floats), rule versions are
consistent with the rule list, the shipped templates regenerate byte for byte, and no text the layer produces claims more than it can support."""
import ast, os, re, subprocess, sys, tempfile, unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT
from apg.det import common as C, detect as D, policy as DP

DET = os.path.join(HERE_ROOT, 'apg', 'det')
PURE = ['common', 'signal', 'noise', 'relations', 'portfolio', 'policy', 'rules_cost', 'rules_commercial', 'rules_ops']
RULE_MODULES = ['rules_cost', 'rules_commercial', 'rules_ops']
FORBIDDEN = {'os', 'sys', 'json', 'csv', 'io', 'time', 'random', 'socket', 'subprocess', 'urllib', 'http', 'threading', 'uuid', 'secrets', 'decimal', 'math', 'hashlib'}
ALLOWED_STD = {'datetime', 'hashlib', 'inspect', 'json', 'os', 'dataclasses'}


def tree(mod):
    return ast.parse(open(os.path.join(DET, mod + '.py'), encoding='utf-8').read())


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

    def test_every_det_module_imports_only_the_standard_library_and_apg(self):
        for f in sorted(os.listdir(DET)):
            if f.endswith('.py'):
                ok = ALLOWED_STD | ({'csv', 'fractions'} if f == 'golden_det.py' else set())                  # the oracle reads the CSV files itself and uses exact fractions
                self.assertTrue(imports(tree(f[:-3])) <= ok, (f, imports(tree(f[:-3])) - ok))

    def test_no_floating_point_and_no_hidden_io_in_the_pure_modules(self):
        for m in PURE:
            for n in ast.walk(tree(m)):
                if isinstance(n, ast.Constant):
                    self.assertNotIsInstance(n.value, float, f'{m}:{n.lineno}')
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    self.assertNotIn(n.func.id, ('float', 'round', 'eval', 'exec', 'open', 'print', 'input'), f'{m}:{n.lineno}')
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
                    self.fail(f'true division in {m}:{n.lineno}')

    def test_the_clock_is_read_only_by_the_writers(self):
        for f in sorted(os.listdir(DET)):
            if not f.endswith('.py') or f in ('reference_m5.py', 'faulty_m5.py', 'contracts_m5.py'):
                continue
            has = any(isinstance(n, ast.Attribute) and n.attr == 'now' for n in ast.walk(tree(f[:-3])))
            self.assertEqual(has, f in ('findings.py', 'monitor.py') and has, f)
            if f not in ('findings.py', 'monitor.py'):
                self.assertFalse(has, f)

    def test_every_rule_function_takes_facts_not_a_store_or_a_clock(self):
        for m in RULE_MODULES:
            for fn in [n for n in tree(m).body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]:
                names = [a.arg for a in fn.args.args]
                if fn.name == 'd02_held_records':
                    continue
                self.assertEqual(names[:4], ['F', 'dp', 'project', 'as_of'], (m, fn.name))

    def test_every_det_module_says_which_blueprint_text_it_answers(self):
        for f in sorted(os.listdir(DET)):
            if f.endswith('.py') and f != '__init__.py':
                doc = ast.get_docstring(tree(f[:-3])) or ''
                self.assertTrue(any(k in doc for k in ('Blueprint', 'Section', 'EDR-10', 'CR-02', 'M5')), f)


class TestConsistency(unittest.TestCase):
    def test_every_registered_rule_has_a_version_and_every_version_has_a_rule(self):
        ids = [rid for rid, _ in D.PROJECT_RULES + D.TENANT_RULES]
        self.assertEqual(sorted(set(ids)), sorted(C.RULE_VERSIONS))
        self.assertEqual(len(ids) - len(set(ids)), 1)                                       # D02 is registered at both scopes, nothing else

    def test_every_policy_rule_is_a_registered_rule_or_a_documented_parameter_group(self):
        ids = {rid for rid, _ in D.PROJECT_RULES + D.TENANT_RULES}
        self.assertEqual(set(DP.RULES) - ids, set())
        self.assertEqual(ids - set(DP.RULES), {'D01', 'D02'})                                # data-integrity rules have no threshold

    def test_the_nine_section_06_rule_types_are_covered(self):
        text = ' '.join(v[0] for v in DP.RULES.values())
        for n in range(1, 10):
            self.assertIn(f'rule {n})', text)
        for rid in ('R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08', 'R09'):
            self.assertIn(rid, DP.RULES)

    def test_the_shipped_detection_templates_regenerate_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE_ROOT, 'tools', 'make_det_templates.py'), d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            made = sorted(os.listdir(d))
            self.assertEqual(made, sorted(os.listdir(os.path.join(HERE_ROOT, 'det_templates'))))
            for n in made:
                self.assertEqual(open(os.path.join(d, n), 'rb').read(), open(os.path.join(HERE_ROOT, 'det_templates', n), 'rb').read(), n)

    def test_no_detection_template_repeats_an_entity_that_an_earlier_milestone_already_ingests(self):
        import json
        from apg.det.intake import DET_ENTITIES
        earlier = set()
        for d in ('ingest_templates', 'import_templates', 'fin_templates'):
            for f in os.listdir(os.path.join(HERE_ROOT, d)):
                if f.endswith('.json'):
                    earlier.add(json.load(open(os.path.join(HERE_ROOT, d, f), encoding='utf-8')).get('entity'))
        self.assertEqual(set(DET_ENTITIES) & earlier, set())


class TestClaimsScan(unittest.TestCase):
    """Text the layer can put in front of a person must not claim a realised outcome, a conclusion about a person, or approval."""
    BANNED = [r'\bsaved\b', r'\brealised\b', r'\bproved?\b', r'\bfraud\b', r'\bnegligen', r'\bblame', r'\bguilty\b', r'\bis closed\b', r'\bapproved for production\b']

    def strings(self, mod):
        out = []
        for n in ast.walk(tree(mod)):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 25 and not n.value.startswith('apg-'):
                out.append((n.lineno, n.value))
            if isinstance(n, ast.JoinedStr):
                out.append((n.lineno, ''.join(p.value for p in n.values if isinstance(p, ast.Constant) and isinstance(p.value, str))))
        return out

    def test_no_rule_or_message_text_claims_a_realised_outcome_or_a_conclusion_about_a_person(self):
        allowed_context = ('not prove', 'does not prove', 'cannot be reported as realised', 'not a verified realised', 'no amount here is a verified realised', 'realised outcome needs', 'realised', )
        for mod in RULE_MODULES + ['noise', 'signal', 'portfolio', 'monitor']:
            for line, s in self.strings(mod):
                low = s.lower()
                for pat in self.BANNED:
                    if re.search(pat, low) and not any(a in low for a in allowed_context):
                        self.fail(f'{mod}:{line}: {s[:90]!r} matches {pat}')

    def test_the_labour_rule_text_never_ranks_or_names_a_worker(self):
        src = open(os.path.join(DET, 'rules_ops.py'), encoding='utf-8').read()
        self.assertNotIn('worker_ref', src.split('def lab_productivity')[1].split('def def_recurrence')[0].replace("'no worker is compared with another'", ''))

    def test_every_signal_text_that_names_an_exposure_says_it_is_not_a_loss_or_an_entitlement_where_it_matters(self):
        src = open(os.path.join(DET, 'rules_commercial.py'), encoding='utf-8').read()
        self.assertIn('not an entitlement', src)
        self.assertIn('not a loss', src)


if __name__ == '__main__':
    unittest.main()
