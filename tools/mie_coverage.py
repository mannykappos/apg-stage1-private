#!/usr/bin/env python3
"""QA-02: the MIE-1 test inventory against the planned cases of spec/MIE1_SPEC_v0.3/MIE1_TEST_STRATEGY.csv (175 cases).  A case is TESTED when a test function in tests/test_mie_*.py
names it in its name or docstring; TOOL when a named tool step is its evidence; NOT_APPLICABLE when it checks the specification package itself, with the reason.  Every planned case
must be accounted for, and no test may cite a case identifier of a planned family that the strategy does not list.
Usage: python3 -I tools/mie_coverage.py [--write]   (--write rewrites programme/MIE1_CASE_COVERAGE.csv; without it the file must equal what this tool makes)."""
import ast, csv, glob, io, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
STRATEGY = os.path.join(ROOT, 'spec', 'MIE1_SPEC_v0.3', 'MIE1_TEST_STRATEGY.csv')
OUT = os.path.join(ROOT, 'programme', 'MIE1_CASE_COVERAGE.csv')
TOOL = {
    'IG-03': 'tools/run_mie1_all.py groups 9 to 18 (the whole unit suite, counted) and tools/run_regression_mie1.py R12',
    'IG-04': 'tools/run_regression_mie1.py R01 to R03 (every M7.3 file byte-identical except the declared changes; no APG application file or existing test changed)',
    'QA-01': 'tools/sabotage_mie1.py (one corruption per SB case on a copy; each must be caught) and tools/mie_mutants.py (every site in the core logic)',
    'QA-02': 'tools/mie_coverage.py (this file) and tools/run_regression_mie1.py R13',
    'QA-03': 'The documents file: the section that separates what the build ran from what has been independently verified (nothing yet)',
    'QA-04': 'tools/run_regression_mie1.py R08 (release text scan for readiness, acceptance, predictive and coverage claims)',
}
NA = {
    'QA-05': 'A check of the specification package (the draft change request and its locked-file hashes). MIE-1 does not change the specification; R01 shows the M7.3 files are unchanged.',
    'QA-06': 'A check of the specification package (the open-question dispositions register). MIE-1 records no disposition; CF-37 keeps the blockers open.',
    'QA-07': 'A check of the specification package (the v0.2 change log mapping). Not part of the code.',
    'QA-08': 'A check of the specification package (re-hashing the delivered v0.1 ZIP). Not part of the code.',
    'QA-09': 'A check of the specification package (the blockers register). The build carries the blockers as open in CF-37; R05 fails if one is marked resolved.',
}
CASE_RE = re.compile(r'\b([A-Z]{2})-(\d{2})\b')


def planned():
    return [(r['test_id'], r['family'], r['case']) for r in csv.DictReader(open(STRATEGY, encoding='utf-8', newline=''))]


def cited():
    """-> {case id: [test file::function, ...]} from test function names (UT_01 -> UT-01) and docstrings."""
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'test_mie_*.py'))):
        tree = ast.parse(open(f, encoding='utf-8').read())
        for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
                text = (ast.get_docstring(fn) or '') + ' ' + fn.name.replace('_', '-')
                ids = set('%s-%s' % m for m in CASE_RE.findall(text))
                for i in ids:
                    out.setdefault(i, []).append('%s::%s.%s' % (os.path.basename(f), cls.name, fn.name))
                for lo_f, lo, hi in re.findall(r'\b([A-Z]{2})-(\d{2})\.\.(?:[A-Z]{2}-)?(\d{2})\b', text):     # ranges written UT-26..UT-41
                    for n in range(int(lo), int(hi) + 1):
                        out.setdefault('%s-%02d' % (lo_f, n), []).append('%s::%s.%s' % (os.path.basename(f), cls.name, fn.name))
    return {k: sorted(set(v)) for k, v in out.items()}


def build():
    plan = planned()
    families = {f for _, f, _ in plan}
    ids = {i for i, _, _ in plan}
    c = cited()
    unknown = sorted(i for i in c if i.split('-')[0] in families and i not in ids)
    rows, missing = [], []
    for i, fam, case in plan:
        if i in c:
            rows.append({'case_id': i, 'family': fam, 'case': case, 'coverage': 'TESTED', 'evidence': '; '.join(c[i]), 'note': ''})
        elif i in TOOL:
            rows.append({'case_id': i, 'family': fam, 'case': case, 'coverage': 'TOOL', 'evidence': TOOL[i], 'note': ''})
        elif i in NA:
            rows.append({'case_id': i, 'family': fam, 'case': case, 'coverage': 'NOT_APPLICABLE', 'evidence': '', 'note': NA[i]})
        else:
            missing.append(i)
            rows.append({'case_id': i, 'family': fam, 'case': case, 'coverage': 'MISSING', 'evidence': '', 'note': ''})
    return rows, missing, unknown


def text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=['case_id', 'family', 'case', 'coverage', 'evidence', 'note'], lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    rows, missing, unknown = build()
    t = text(rows)
    if '--write' in sys.argv:
        open(OUT, 'w', encoding='utf-8', newline='').write(t)
    same = os.path.exists(OUT) and open(OUT, encoding='utf-8', newline='').read() == t
    counts = {}
    for r in rows:
        counts[r['coverage']] = counts.get(r['coverage'], 0) + 1
    print('planned cases %d  %s' % (len(rows), '  '.join('%s %d' % kv for kv in sorted(counts.items()))))
    if missing:
        print('MISSING:', missing)
    if unknown:
        print('CITED BUT NOT PLANNED:', unknown)
    if not same:
        print('programme/MIE1_CASE_COVERAGE.csv is not what this tool makes')
    ok = not missing and not unknown and same and len(rows) == 175
    print('EVERY PLANNED CASE IS ACCOUNTED FOR' if ok else 'COVERAGE INCOMPLETE')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
