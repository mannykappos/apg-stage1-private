#!/usr/bin/env python3
"""Builder tool (outside the tree), rewritten in the 2026-11-11 recovery from the format of the c9b324eb record static/route_children.txt
(the tool that made it was lost): the first route proof (I.3; amendment 5 row 119).  On a fresh extraction of the freeze, the plan of
each of the 19 successor wrappers is read with the freeze's own evkit.wrapper_plan (the plan the wrapper itself runs, checked against
the pins).  For every CHECK group that starts a child (classes P, N and B with a command; W is built in) the script it starts is
classified: a successor (tools/*_s1.py), an M10 tool with no successor, or an old tool that HAS a successor (a route failure: it
must be none).  It also lists the scripts the FILE groups run (classes S-T, S-R, NW) and the freeze's REGRESSION_REDIRECTS.
Usage: python3 -I -S route_children_s1.py NEW.zip OUT.txt        BUILDER-EXECUTED: NOT INDEPENDENT."""
import os, shutil, sys, tempfile, zipfile

WRAPPERS = ['run_m4_all', 'run_m3_all', 'run_m6_all', 'run_m7_all', 'run_m71_all', 'run_m72_all', 'run_m73_all', 'run_m91_all',
            'run_m92_all', 'run_m93_all', 'run_m94_all', 'run_f67_all', 'run_f671_all', 'run_f672_all', 'run_f673_all', 'run_f674_all',
            'run_mie1_all', 'run_mie1_1_all', 'run_m8_all']


def script(run):
    return next((a for a in run if a.endswith('.py')), None)


def main(zp, outp):
    tmp = tempfile.mkdtemp(prefix='s1_rc_')
    try:
        with zipfile.ZipFile(zp) as z:
            z.extractall(tmp)
        root = os.path.join(tmp, 'APG-M11-S1')
        sys.path.insert(0, root)
        import tools.evkit as E
        pins, _ = E.load_pins(os.path.join(root, 'tools', 'expected_counts.json'))
        checks, file_scripts, bad, per = [], set(), [], []
        for w in WRAPPERS:
            tool = w + '_s1'
            _, plan = E.wrapper_plan(tool, w, root, pins, pins['wrapper_inventories'][tool]['m10_sha256'])
            n = 0
            for g in plan:
                run = g.get('run') or []
                s = script(run)
                if g['class'] in ('P', 'N', 'B') and s:
                    n += 1
                    succ = s.endswith('_s1.py')
                    has_succ = (not succ) and os.path.exists(os.path.join(root, s[:-3] + '_s1.py'))
                    checks.append((tool, g['id'], s, 'successor' if succ else 'old tool WITH a successor' if has_succ else 'M10 tool, no successor'))
                    if has_succ:
                        bad.append('%s %s %s' % (tool, g['id'], s))
                elif g['class'] in ('S-T', 'S-R', 'NW') and s:
                    file_scripts.add(s)
            per.append('  %-18s CHECK groups that start a child: %d' % (tool, n))
        lines = ['CHECK groups that start a child: %d' % len(checks),
                 '  M10 tool, no successor: %d' % sum(c[3] == 'M10 tool, no successor' for c in checks),
                 '  successor: %d' % sum(c[3] == 'successor' for c in checks),
                 'children that name an old tool that has a successor: %d %s' % (len(bad), bad),
                 'FILE groups run: %s' % sorted(file_scripts),
                 'REGRESSION_REDIRECTS: %s' % sorted(E.REGRESSION_REDIRECTS.items())]
        lines += ['per wrapper:'] + per + ['every CHECK group:'] + ['  %s %s %s  [%s]' % c for c in checks]
        lines.append('RESULT route_children %s' % ('HOLDS' if not bad else 'DOES NOT HOLD'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    open(outp, 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:4] + lines[-1:]))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
