# Fills draft 5's own markers from FILL_v5.json and the generated counts; assemble.py then fills its three.  Builder tool.
import json, re, sys
src, outdir, dst = sys.argv[1:4]
s = open(src).read(); F = json.load(open('FILL_v5.json'))
c = open(outdir + '/CIA_COUNTS.txt').read()
m = re.search(r'Impact rows: (\d+); distinct locked items touched: (\d+) \((\d+) with an RTM ID, (\d+) paragraphs and (\d+) table rows', c)
fmt = lambda x: '{:,}'.format(int(x))
F.update({'N_ROWS': fmt(m[1]), 'N_ITEMS': fmt(m[2]), 'N_RTM': fmt(m[3]), 'N_PARA': m[4], 'N_TROW': m[5], 'N_BACK': str(int(m[4]) + int(m[5]))})
for k, v in F.items():
    s = s.replace('<<%s>>' % k, v)
left = set(re.findall(r'<<([A-Z0-9_]+)>>', s)) - {'SECTION_SUMMARY', 'PROPOSED_TEXT', 'COUNTS'}
if left: sys.exit('unfilled: %s' % sorted(left))
open(dst, 'w').write(s)
