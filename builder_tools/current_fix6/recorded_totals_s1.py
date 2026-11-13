#!/usr/bin/env python3
"""Builder tool (outside the tree), new in the 2026-11-11 recovery, for the owner's B.6 / K.2 answer of 2026-11-11 22:47 ("e4531a35 +
recorded totals"): freeze d5f87d6b was lost, so its per-item verdicts cannot be compared.  This tool compares, runner by runner, the
totals of a b6 or k2 summary made now (compare_pass2_s1.py, new freeze against e4531a35) with the totals recorded in the c9b324eb-era
summary of the same mode and Python (the AM5 review pack's compare_py31x/<mode>.txt), whose "old" side is d5f87d6b and whose "new" side
is c9b324eb.  Compared per runner: item count, exit, status, both control outcomes and, for b6, the CONTROL values and causes.  The RESULT
format version v is not compared (it changed by design).  It cannot show per-item equality with d5f87d6b and does not claim to.
Usage: python3 -I -S recorded_totals_s1.py MODE NOW.txt RECORDED.txt OUT.txt      BUILDER-EXECUTED: NOT INDEPENDENT."""
import re, sys

ROW = re.compile(r'^(\S+)\s+items new=(\d+) old=(\d+)\s+exit new=(-?\d+) old=(-?\d+)\s+status new=(\S+) old=(\S+)\s+'
                 r'controls new=(\S+)/(\S+) old=(\S+)/(\S+)')
CTL = re.compile(r'^(\S+)\s+CONTROL lines new=(\[.*\]) old=(\[.*\])$')


def read(path):
    rows, ctl = {}, {}
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        m = ROW.match(line)
        if m:
            g = m.groups()
            rows[g[0]] = {'new': (int(g[1]), int(g[3]), g[5], g[7], g[8]), 'old': (int(g[2]), int(g[4]), g[6], g[9], g[10])}
        m = CTL.match(line)
        if m:
            ctl[m.group(1)] = {'new': m.group(2), 'old': m.group(3)}
    return rows, ctl


def main(mode, now_p, rec_p, out_p):
    now, now_c = read(now_p)
    rec, rec_c = read(rec_p)
    lines, diffs = [], 0
    if sorted(now) != sorted(rec):
        lines.append('DIFFERENT runner sets: now %s recorded %s' % (sorted(now), sorted(rec)))
        diffs += 1
    for r in sorted(set(now) & set(rec)):
        mine = now[r]['new']
        for label, side in (('d5f87d6b (recorded old)', 'old'), ('c9b324eb (recorded new)', 'new')):
            same = mine == rec[r][side]
            diffs += not same
            lines.append('%-24s %s: e9e11d9 (freeze ee1ce3ec) items/exit/status/controls=%s recorded=%s %s' % (r, label, mine, rec[r][side], 'SAME' if same else 'DIFFERENT'))
            if mode == 'b6':
                cs = now_c.get(r, {}).get('new') == rec_c.get(r, {}).get(side)
                diffs += not cs
                lines.append('%-24s %s: CONTROL lines %s' % (r, label, 'SAME' if cs else 'DIFFERENT now=%s recorded=%s' % (
                    now_c.get(r, {}).get('new'), rec_c.get(r, {}).get(side))))
    lines.append('runners compared: %d' % len(set(now) & set(rec)))
    lines.append('RESULT %s_recorded_totals %s' % (mode, 'SAME' if not diffs else 'DIFFERENT %d' % diffs))
    open(out_p, 'w').write('\n'.join(lines) + '\n')
    print(lines[-1])
    return 0 if not diffs else 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:5]))
