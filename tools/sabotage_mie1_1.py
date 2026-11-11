#!/usr/bin/env python3
"""Package-level sabotage for MIE-1.1: the sixty MIE-1 catalogue cases (tools/sabotage_mie1.py, reused unchanged except SB-29, whose target text moved because MIE-1.1
adds a branch after it), plus cases for the two MIE-1.1 corrections (C-01 to C-06).  Each corruption is applied to a COPY of this package and the named check must then
FAIL.  Regression steps are those of tools/run_regression_mie1_1.py.
Usage: python3 -I tools/sabotage_mie1_1.py [--list] [--only ID[,ID]]   (from the package root; works in temporary folders; changes nothing here)"""
import importlib.util, os, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('sab_mie1', os.path.join(ROOT, 'tools', 'sabotage_mie1.py'))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)
E, O, S, R = 'mie/core/engine.py', 'mie/core/observations.py', 'mie/core/signals.py', 'mie/core/reference.py'
FIX = 'test_mie_core_m11_corrections.py'
CASES = []
for c in B.CASES:
    if c[0] == 'SB-29':
        c = (c[0], c[1], c[2], "                raise MieError('STORE_UNAVAILABLE')\n            except Exception:", "                pass\n            except Exception:", c[5])
    CASES.append(c)
CASES += [
    ('C-01', 'F-70: an unexpected exception at the commit escapes again', E, "            except Exception:                                     # MIE-1.1, F-70", "            except ZeroDivisionError:                             # MIE-1.1, F-70", FIX),
    ('C-02', 'F-70: an unexpected commit failure leaves no FAILED event', E, "                self._try_append(tenant, op, 'FAILED', 'INTERNAL_ERROR_FAIL_CLOSED', refs, must=False)\n                raise MieError('INTERNAL_ERROR_FAIL_CLOSED')\n        return",
     "                raise MieError('INTERNAL_ERROR_FAIL_CLOSED')\n        return", FIX),
    ('C-03', 'F-70: an unexpected audit-sink exception escapes again', E, "        except Exception:\n            raise AuditFailure()", "        except ZeroDivisionError:\n            raise AuditFailure()", FIX),
    ('C-04', 'F-70: the observation batch is written item by item again', E, "                self.obs.append_batch(tenant, new)", "                for oid, ob in new:\n                    self.obs.append(tenant, oid, ob)", FIX),
    ('C-05', 'F-70: the reference batch write applies items before the batch is complete', R, "            staged[k] = canon.copy(obs)\n", "            staged[k] = canon.copy(obs)\n            self.d[k] = staged[k]\n", FIX),
    ('C-06', 'F-71: a correction is checked only for an existing identifier again', O, "    if prior is not None and not S.corrects(obs, prior):", "    if False:", FIX),
    ('C-07', 'F-71: a correction may name another subject (only the subject check is dropped)', S, "    return (series_key(new) == series_key(old)", "    return (series_key(new)[1:] == series_key(old)[1:]", FIX),
    ('C-08', 'F-71: a correction may name another date', S, " and new['as_of'] == old['as_of']", "", FIX),
    ('C-09', 'F-71: a correction may name another source', S, " and new['source_id'] == old['source_id']", "", FIX),
    ('C-10', 'F-71: classification honours any supersedes link again', S, " and o['supersedes'] in observations and corrects(o, observations[o['supersedes']])", "", FIX),
]


def check(work, target, env):
    if target.startswith('R'):
        r = subprocess.run([sys.executable, '-I', 'tools/run_regression_mie1_1.py', '--step', target], cwd=work, env=env, capture_output=True, text=True, timeout=1800)
        return r.returncode != 0 and ('FAIL ' + target) in r.stdout, (r.stdout.strip().splitlines() or [''])[-1]
    return B.check(work, target, env)


def main():
    if '--list' in sys.argv:
        for c in CASES:
            print(c[0], c[1], '->', c[5])
        return 0
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    bad = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for cid, what, path, old, new, target in CASES:
        if only and cid not in only:
            continue
        with tempfile.TemporaryDirectory(prefix='mie11_sab_') as tmp:
            work = B.copy(tmp)
            p = os.path.join(work, path)
            text = open(p, encoding='utf-8').read()
            if text.count(old) != 1:
                print('ERROR', cid, 'the text to corrupt is not in %s exactly once (%d)' % (path, text.count(old)))
                return 2
            open(p, 'w', encoding='utf-8').write(text.replace(old, new, 1))
            caught, detail = check(work, target, env)
            print('%s %s %s -> %s  [%s]' % ('CAUGHT' if caught else 'MISSED', cid, what, target, detail), flush=True)
            if not caught:
                bad.append(cid)
    n = len([c for c in CASES if not only or c[0] in only])
    print('sabotage cases %d  missed %d%s' % (n, len(bad), ('  MISSED: %r' % bad) if bad else ''))
    print('EVERY SABOTAGE CASE IS CAUGHT' if not bad else 'SABOTAGE GAPS')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
