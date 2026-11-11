"""Static discipline for the financial core, checked on the source itself: the calculation modules are pure (no clock, no randomness, no files, no network, no floats),
every module says which blueprint text it answers, and nothing outside the standard library and the apg package is imported."""
import ast, os, subprocess, sys, tempfile, unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT
from apg.fin import calc_records as C

FIN = os.path.join(HERE_ROOT, 'apg', 'fin')
HASHED = [m.__name__.rsplit('.', 1)[1] for m in C.MODULES]
STDLIB_OK = {'datetime', 'hashlib', 'inspect', 'json', 'os', 'csv', 'io', 'fractions', 'dataclasses', 'sys'}
FORBIDDEN_IN_CALC = {'os', 'sys', 'json', 'csv', 'io', 'time', 'random', 'socket', 'subprocess', 'urllib', 'http', 'threading', 'uuid', 'secrets', 'decimal', 'math'}


def tree(mod):
    return ast.parse(open(os.path.join(FIN, mod + '.py'), encoding='utf-8').read())


def imports(t):
    out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            out |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0:
            out.add((n.module or '').split('.')[0])
    return out


class StaticDiscipline(unittest.TestCase):
    def test_calculation_modules_import_nothing_that_could_make_them_impure(self):
        for m in HASHED:
            bad = imports(tree(m)) & FORBIDDEN_IN_CALC
            self.assertEqual(bad, set(), m)

    def test_every_fin_module_imports_only_the_standard_library_and_apg(self):
        for f in os.listdir(FIN):
            if f.endswith('.py'):
                self.assertTrue(imports(tree(f[:-3])) <= STDLIB_OK, (f, imports(tree(f[:-3])) - STDLIB_OK))

    def test_no_floating_point_in_calculation_modules(self):
        for m in HASHED:
            t = tree(m)
            for n in ast.walk(t):
                if isinstance(n, ast.Constant):
                    self.assertNotIsInstance(n.value, float, f'{m}:{n.lineno}')
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    self.assertNotIn(n.func.id, ('float', 'round', 'eval', 'exec', 'open', 'print', 'input'), f'{m}:{n.lineno}')

    def test_true_division_appears_only_in_the_display_helper(self):
        for m in HASHED:
            t = tree(m)
            for fn in [n for n in ast.walk(t) if isinstance(n, (ast.FunctionDef,))]:
                divs = [n for n in ast.walk(fn) if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)]
                if divs:
                    self.assertEqual((m, fn.name), ('figure', 'explain'))
            # nothing outside a function either
        t = tree('figure')
        top = [n for n in t.body if not isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        self.assertFalse([n for s in top for n in ast.walk(s) if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)])

    def test_the_clock_is_read_in_exactly_one_place(self):
        hits = []
        for m in HASHED:
            for fn in [n for n in ast.walk(tree(m)) if isinstance(n, ast.FunctionDef)]:
                if any(isinstance(n, ast.Attribute) and n.attr == 'now' for n in ast.walk(fn)):
                    hits.append((m, fn.name))
        self.assertEqual(hits, [('cash_states', 'record_event')])                          # the writer stamps the event time; every calculation is a function of its pinned inputs only

    def test_every_module_says_which_blueprint_text_it_answers(self):
        for f in os.listdir(FIN):
            if f.endswith('.py') and f != '__init__.py':
                doc = ast.get_docstring(tree(f[:-3])) or ''
                self.assertTrue(any(k in doc for k in ('Blueprint', 'CR-02', 'M4', 'Section')), f)

    def test_calculation_functions_take_facts_not_stores(self):
        """Builders receive a Facts object (pinned inputs only); none of them is handed a store, a session or a clock."""
        for m in ('costs', 'commitments', 'revenue', 'forecast', 'margins', 'cashview'):
            for fn in [n for n in tree(m).body if isinstance(n, ast.FunctionDef) and n.name.startswith('build_')]:
                names = [a.arg for a in fn.args.args]
                self.assertEqual(names[0], 'F', (m, fn.name))
                self.assertFalse({'scoped', 'store', 'clock', 'ctx'} & set(names), (m, fn.name))

    def test_the_shipped_financial_templates_regenerate_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE_ROOT, 'tools', 'make_fin_templates.py'), d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            made = sorted(os.listdir(d))
            self.assertEqual(made, sorted(os.listdir(os.path.join(HERE_ROOT, 'fin_templates'))))
            for n in made:
                self.assertEqual(open(os.path.join(d, n), 'rb').read(), open(os.path.join(HERE_ROOT, 'fin_templates', n), 'rb').read(), n)


if __name__ == '__main__':
    unittest.main()
