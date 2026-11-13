"""Section 18 cascade impact assessment, data supply design (draft 7) and Data Readiness CR revision 4: the requirement-level tables.
Builder work (Claude): BUILDER-EXECUTED: NOT INDEPENDENT.   Version 3 (after the third independent check).

From the locked package (the Master RTM and the 19 section documents, v1.0) and the change items defined below, it writes:
  CIA_PROPOSED_TEXT.csv   every paragraph, bullet, table row and acceptance criterion this change request proposes to add, and the version
                          lines it rewords (the only locked text it rewords), with the proposed ID, the section, the anchor it follows
                          (RTM ID; or paragraph index, or table and row, where the RTM has none), the locked text there, and the new text.
  CIA_RTM_IMPACT.csv      every locked paragraph and table row each change item touches, as an insertion point, a reworded version line,
                          or a dependent reviewed with no text change.  Tables and rows are numbered from 0, as python-docx counts them, like paragraph indices; row 0 is a table's header row, so body rows start at 1.  Spans are read from the section documents themselves (paragraphs
                          and table rows between a heading and the next heading of the same or a higher level), so locked text the RTM
                          does not map is listed too, as "Sxx paragraph N (no RTM row)" or "Sxx table T row R (no RTM row)".
  CIA_DEPENDENT_TEXT.txt  the full locked text of every dependent, for the reviewer.
  CIA_COUNTS.txt          counts; per amended section, the RTM rows after the first insertion point; the RTM's unmapped text (observation).
It fails if an anchor or heading named below is not in the locked package, if a proposed ID is already used, or if an insertion point is not
the true end of its block (the next item must be a heading, or for a list item the end of that list, or for a table row the last row).
usage: python3 -I build_cia.py <folder holding the extracted locked package> <output folder>"""
import csv, glob, os, re, sys, collections
import docx
from docx.oxml.ns import qn

PKG, OUT = sys.argv[1], sys.argv[2]
RTM = os.path.join(PKG, 'MASTER_REQUIREMENTS_TRACEABILITY_MATRIX.csv')
rows = list(csv.DictReader(open(RTM, encoding='utf-8-sig')))
for x in rows:
    m = re.search(r'paragraph_index=(\d+);(?: style=([^;]+);)? text_prefix=(.*)', x['source_anchor'], re.S)
    x['pi'] = int(m.group(1))
byid = {x['requirement_id']: x for x in rows}
bypi = {(x['source_section'], x['pi']): x for x in rows}
docs, body = {}, {}
for f in sorted(glob.glob(os.path.join(PKG, '*Section_*_v1.0_LOCKED.docx'))):
    s = re.search(r'Section_(\d+)', f).group(1)
    d = docx.Document(f); docs[s] = d
    items, pi, ti = [], 0, 0          # body order: ('p', index, style, text) and ('t', table, row, text)
    for el in d.element.body.iterchildren():
        if el.tag == qn('w:p'):
            p = d.paragraphs[pi]
            items.append(('p', pi, p.style.name, p.text)); pi += 1
        elif el.tag == qn('w:tbl'):
            t = d.tables[ti]
            for ri, r in enumerate(t.rows):
                if ri:
                    items.append(('t', ti, ri, ' | '.join(c.text for c in r.cells)))
            ti += 1
    body[s] = items

def hlevel(style):
    m = re.match(r'Heading (\d)', style)
    return int(m.group(1)) if m else (1 if style.startswith('Title') else None)

def ref(sec, it):
    """-> (RTM ID or anchor text, locked text) for a body item"""
    if it[0] == 'p':
        x = bypi.get((sec, it[1]))
        return (x['requirement_id'], it[3]) if x else ('S%s paragraph %d (no RTM row)' % (sec, it[1]), it[3])
    return ('S%s table %d row %d (no RTM row)' % (sec, it[1], it[2]), it[3])

def span(sec, num):
    """the non-empty paragraphs and table rows from heading `num` to the next heading of the same or a higher level"""
    b = body[sec]
    for i, it in enumerate(b):
        if it[0] == 'p' and hlevel(it[2]) and re.match(r'\s*%s\.?\s' % re.escape(num), it[3]):
            lv, out = hlevel(it[2]), [it]
            for jt in b[i + 1:]:
                if jt[0] == 'p' and hlevel(jt[2]) and hlevel(jt[2]) <= lv:
                    break
                if jt[3].strip():
                    out.append(jt)
            return out
    sys.exit('heading %s not found in section %s' % (num, sec))

def locate(sec, a):
    """an RTM ID, ('p', index) or ('t', table, row) -> its position in the body list"""
    b = body[sec]
    if isinstance(a, str):
        if a not in byid or byid[a]['source_section'] != sec:
            sys.exit('anchor %s not in section %s' % (a, sec))
        a = ('p', byid[a]['pi'])
    for i, it in enumerate(b):
        if it[0] == a[0] and it[1] == a[1] and (a[0] == 'p' or it[2] == a[2]):
            return i
    sys.exit('anchor %r not in section %s' % (a, sec))

LIST = ('List Bullet', 'List Number')

def check_end(sec, a, kind):
    """the insertion point must be the true end of its block"""
    b = body[sec]; i = locate(sec, a); it = b[i]
    if kind == 'amendment record':        # appended to the lock record, before any closing 'next section' line
        return
    nxt = next((jt for jt in b[i + 1:] if jt[3].strip()), None)
    if it[0] == 't':
        if nxt is not None and nxt[0] == 't' and nxt[1] == it[1]:
            sys.exit('table insertion %r in S%s is not the last row' % (a, sec))
        return
    if nxt is None or (nxt[0] == 'p' and hlevel(nxt[2])):
        return
    if kind in ('bullet', 'acceptance criterion') and it[2] in LIST and not (nxt[0] == 'p' and nxt[2] in LIST):
        return
    sys.exit('insertion after %r in S%s is not the end of its block: next is %r' % (a, sec, nxt[3][:60]))

exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cia_data.py')).read())   # ADD, REWORD, DEP

# ---------------------------------------------------------------------------------------------------------------------------------
os.makedirs(OUT, exist_ok=True)
used = set(byid); prop = []
for sec, after, nid, kind, text, item in ADD:
    if nid in used:
        sys.exit('proposed ID already used: ' + nid)
    used.add(nid)
    check_end(sec, after, kind)
    a, t = ref(sec, body[sec][locate(sec, after)])
    prop.append({'proposed ID': nid, 'section': sec, 'change': 'added after', 'anchor': a, 'locked text there': t, 'kind': kind, 'proposed text': text, 'change item': item})
for rw in REWORD:
    sec, at, nid, text, item = rw[:5]
    kind = rw[5] if len(rw) > 5 else 'version line'
    if nid in used:
        sys.exit('proposed ID already used: ' + nid)
    used.add(nid)
    a, t = ref(sec, body[sec][locate(sec, at)])
    change = 'reworded (version line)' if kind == 'version line' else 'reworded (owner-approved relaxation)'
    prop.append({'proposed ID': nid, 'section': sec, 'change': change, 'anchor': a, 'locked text there': t, 'kind': kind, 'proposed text': text, 'change item': item})
with open(os.path.join(OUT, 'CIA_PROPOSED_TEXT.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(prop[0]), lineterminator='\n'); w.writeheader(); w.writerows(prop)

imp, seen = [], set()
def put(item, sec, a, rel, text):
    key = (item, a, rel[:9])
    if key not in seen:
        seen.add(key); imp.append({'change item': item, 'section': sec, 'RTM ID or source anchor': a, 'relation': rel, 'locked text': text})
for p in prop:
    rel = {'added after': 'insertion point (text added after it; its own wording unchanged)',
           'reworded (version line)': 'reworded: version line (see CIA_PROPOSED_TEXT.csv)'}.get(p['change'], 'reworded: owner-approved relaxation (see CIA_PROPOSED_TEXT.csv)')
    for it in p['change item'].split(', '):
        put(it, p['section'], p['anchor'], rel, p['locked text there'])
for item, sec, keys, why in DEP:
    for k in keys:
        if isinstance(k, tuple) or k in byid:
            its = [body[sec][locate(sec, k)]]
        else:
            its = span(sec, k)
        for it in its:
            a, t = ref(sec, it)
            put(item, sec, a, 'dependent: reviewed, no text change (' + why + ')', t)
with open(os.path.join(OUT, 'CIA_RTM_IMPACT.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(imp[0]), lineterminator='\n'); w.writeheader(); w.writerows(imp)
with open(os.path.join(OUT, 'CIA_DEPENDENT_TEXT.txt'), 'w') as fh:
    done = set()
    for r in imp:
        if r['RTM ID or source anchor'] not in done:
            done.add(r['RTM ID or source anchor'])
            fh.write('%s\t%s\n' % (r['RTM ID or source anchor'], r['locked text'].replace('\n', ' ')))

# counts
L = []
adds = [p for p in prop if p['change'] == 'added after']
amended = sorted({p['section'] for p in prop})
nac = sum(1 for p in adds if p['kind'] == 'acceptance criterion')
L.append('Proposed additions: %d (%d paragraphs or bullets, %d headings, %d table rows, %d acceptance criteria PG-DS-AC-01 to %02d, %d amendment records); each is one new RTM row' %
         (len(adds), sum(1 for p in adds if p['kind'] in ('paragraph', 'bullet')), sum(1 for p in adds if p['kind'].startswith('heading')),
          sum(1 for p in adds if p['kind'] == 'table row'), nac, nac, sum(1 for p in adds if p['kind'] == 'amendment record')))
vl = [p for p in prop if p['kind'] == 'version line']; rx = [p for p in prop if p['change'] == 'reworded (owner-approved relaxation)']
L.append('Locked text reworded: %d version lines (two in each of S01, S02 and S03, one in each of S04, S05, S06 and S11), and %d sentence(s) reworded as an owner-approved relaxation (%s); nothing else' %
         (len(vl), len(rx), ', '.join('S%s %s' % (p['section'], p['anchor']) for p in rx)))
L.append('Sections amended (v1.0 -> v1.1): ' + ', '.join(amended))
anchors = {r['RTM ID or source anchor'] for r in imp}
L.append('Impact rows: %d; distinct locked items touched: %d (%d with an RTM ID, %d paragraphs and %d table rows the RTM does not map); insertion points: %d distinct anchors' %
         (len(imp), len(anchors), sum(1 for a in anchors if a in byid), sum(1 for a in anchors if 'paragraph' in a), sum(1 for a in anchors if 'table' in a),
          len({p['anchor'] for p in adds})))
L.append('Sections reviewed as dependents only: ' + ', '.join(sorted({r['section'] for r in imp} - set(amended))))
L.append('')
L.append('Existing RTM rows whose paragraph-index anchor moves (they sit after the first inserted paragraph; their IDs are kept):')
for sec in amended:
    pis = [locate(sec, a[1]) for a in ADD if a[0] == sec and (isinstance(a[1], str) or a[1][0] == 'p')]
    if not pis:
        L.append('  S%s: none (table rows only)' % sec); continue
    first = min(body[sec][i][1] for i in pis)
    n = sum(1 for x in rows if x['source_section'] == sec and x['pi'] > first)
    L.append('  S%s: %d of %d rows (after paragraph %d)' % (sec, n, sum(1 for x in rows if x['source_section'] == sec), first))
L.append('')
L.append('Pre-existing observation (outside this change request): locked text the RTM does not map, Sections 00-18')
tp = tt = 0
for sec in sorted(docs):
    un = [it for it in body[sec] if it[0] == 'p' and it[3].strip() and (sec, it[1]) not in bypi]
    tr = [it for it in body[sec] if it[0] == 't']
    tp += len(un); tt += len(tr)
    L.append('  S%s: %d paragraphs not mapped (of %d non-empty), %d table body rows not mapped' %
             (sec, len(un), sum(1 for it in body[sec] if it[0] == 'p' and it[3].strip()), len(tr)))
L.append('  total: %d paragraphs (cover lines and lock-record lines included; all 140 of Section 18), %d table body rows' % (tp, tt))
open(os.path.join(OUT, 'CIA_COUNTS.txt'), 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
