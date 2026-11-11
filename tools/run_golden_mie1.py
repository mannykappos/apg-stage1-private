#!/usr/bin/env python3
"""The construction pack on Builder Zero (tests/helpers_mie_construction.golden_run): prints the run and compares it with regression/mie1/golden_mie1.json.
Every owner input in that run is TEST-ONLY.  Usage: python3 -I tools/run_golden_mie1.py [--record]   (--record rewrites the golden file; use only when a change is declared)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from tests.helpers_mie_construction import golden_run          # noqa: E402

GOLDEN = os.path.join(ROOT, 'regression', 'mie1', 'golden_mie1.json')


def dumps(g):
    return json.dumps(g, indent=1, sort_keys=True, ensure_ascii=True) + '\n'


def main():
    g = dumps(golden_run(ROOT))
    if sys.argv[1:] == ['--record']:
        open(GOLDEN, 'w', encoding='utf-8', newline='\n').write(g)
        print('recorded', GOLDEN)
        return 0
    print(g)
    same = os.path.exists(GOLDEN) and open(GOLDEN, encoding='utf-8').read() == g
    print('THE GOLDEN MIE-1 RUN EQUALS THE RECORDED ANSWER' if same else 'THE GOLDEN MIE-1 RUN DIFFERS FROM THE RECORDED ANSWER')
    return 0 if same else 1


if __name__ == '__main__':
    sys.exit(main())
