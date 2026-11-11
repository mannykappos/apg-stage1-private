"""Static discipline for the M9.1 package apg/api, checked on the source: it imports only the standard library and apg, the logic reads no clock of its own (it is given one), has no randomness, files,
network, floats or hidden output, every module says which blueprint text it answers, and no text it produces claims more than it can support."""
import ast, os, re, unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT

API = os.path.join(HERE_ROOT, 'apg', 'api')
LOGIC = ['approval_boundary']                                # the logic; the contract suite, the reference port and the faulty ports are test inputs
FORBIDDEN = {'os', 'sys', 'json', 'csv', 'io', 'time', 'random', 'socket', 'subprocess', 'urllib', 'http', 'threading', 'uuid', 'secrets', 'decimal', 'math', 'hashlib', 'datetime'}
ALLOWED_STD = {'re', 'dataclasses'}


def tree(mod):
    return ast.parse(open(os.path.join(API, mod + '.py'), encoding='utf-8').read())


def imports(t):
    out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            out |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0:
            out.add((n.module or '').split('.')[0])
    return out


class TestPurity(unittest.TestCase):
    def mods(self):
        return [f[:-3] for f in sorted(os.listdir(API)) if f.endswith('.py')]

    def test_the_package_imports_only_the_standard_library_and_apg(self):
        for m in self.mods():
            self.assertTrue(imports(tree(m)) <= ALLOWED_STD, (m, imports(tree(m)) - ALLOWED_STD))

    def test_the_logic_imports_nothing_that_could_make_it_impure(self):
        for m in LOGIC:
            self.assertEqual(imports(tree(m)) & FORBIDDEN, set(), m)

    def test_no_floating_point_no_hidden_output_and_no_dynamic_code_in_the_logic(self):
        for m in LOGIC:
            for n in ast.walk(tree(m)):
                if isinstance(n, ast.Constant):
                    self.assertNotIsInstance(n.value, float, f'{m}:{n.lineno}')
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    self.assertNotIn(n.func.id, ('float', 'round', 'eval', 'exec', 'open', 'print', 'input', '__import__', 'compile'), f'{m}:{n.lineno}')
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
                    self.fail(f'true division in {m}:{n.lineno}')

    def test_the_clock_is_only_ever_the_one_the_caller_passed_in(self):
        for m in LOGIC:
            for n in ast.walk(tree(m)):
                if isinstance(n, ast.Attribute) and n.attr == 'now':
                    self.assertIsInstance(n.value, ast.Name, f'{m}:{n.lineno}')
                    self.assertEqual(n.value.id, 'clock', f'{m}:{n.lineno}')

    def test_every_module_says_which_blueprint_text_it_answers(self):
        for m in self.mods():
            if m == '__init__':
                doc = ast.get_docstring(tree(m)) or ''
            else:
                doc = ast.get_docstring(tree(m)) or ''
            self.assertTrue(any(k in doc for k in ('Blueprint', 'Section', 'EDR-31', 'EDR-')), m)

    def test_the_logic_never_writes_a_finding_field_or_a_status(self):
        src = open(os.path.join(API, 'approval_boundary.py'), encoding='utf-8').read()
        self.assertNotIn("['status'] =", src)
        for fn in ('scoped.put(FD.KIND', "scoped.put('finding'"):
            self.assertNotIn(fn, src)
        puts = [n for n in ast.walk(tree('approval_boundary')) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'put']
        for c in puts:
            self.assertEqual(ast.unparse(c.args[0]), 'REQUEST_KIND')                    # the only record kind the boundary writes is its own request record


class TestNoOverclaim(unittest.TestCase):
    CLAIM = re.compile(r'\b(production[- ]ready|independently (reviewed|verified)|approved by the auditor|guarantee[sd]?|certified|compliant with|complies with|secure by)\b', re.I)

    def test_no_text_in_the_package_claims_review_readiness_or_compliance(self):
        for f in sorted(os.listdir(API)):
            if f.endswith('.py'):
                text = ' '.join(open(os.path.join(API, f), encoding='utf-8').read().split())
                for m in self.CLAIM.finditer(text):
                    window = text[max(0, m.start() - 80):m.end()]
                    self.assertRegex(window, r'(?i)\b(no|not|nothing|never|without|has not been)\b', (f, window))


if __name__ == '__main__':
    unittest.main()
