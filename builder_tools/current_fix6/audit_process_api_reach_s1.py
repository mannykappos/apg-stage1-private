#!/usr/bin/env python3
"""Builder tool (outside the tree), rewritten in the 2026-11-11 recovery from the format of the c9b324eb record
audit_final/process_api_reach.txt (d14/s1/tools/audit_process_api_reach_s1.py was lost): can a unit reach PID 1's process API?
(P.2 / P.9 audit; amendment 5 row 7, with the PID 1 line and the process listing the mapping asked for.)
Started by the builder with env -i and five names (PATH TMPDIR LANG LC_ALL TZ), as python3 -I -S, from a fresh extraction of the freeze.
The probe runs as a unit started through the freeze's own tools/evkit.py run_unit (env evkit.clean_env), and records:
  - a TCP connect to port 2024 on 127.0.0.1 and on each local IPv4 address in /proc/net/fib_trie (closed at once, nothing sent);
  - an AF_VSOCK connect to port 2024 on cids 1, 2 and 3 (2 s limit; closed at once, nothing sent);
  - PID 1's command line and the user-space process list (pid, ppid, user, command) as /proc shows them to the unit.
Usage: python3 -I -S audit_process_api_reach_s1.py EXTRACTION_ROOT OUT.txt        BUILDER-EXECUTED: NOT INDEPENDENT."""
import os, sys, tempfile

PROBE = r'''
import os, pwd, re, socket
out = []
addrs = ['127.0.0.1']
try:
    t = open('/proc/net/fib_trie').read().splitlines()
    for i, l in enumerate(t):
        if '/32 host LOCAL' in l:
            a = t[i - 1].split()[-1]
            if a not in addrs:
                addrs.append(a)
except OSError:
    pass
for a in addrs:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((a, 2024))
        out.append('tcp %s 2024 connect accepted (closed at once, nothing sent)' % a)
    except OSError as e:
        out.append('tcp %s 2024 %s %s' % (a, e.__class__.__name__, e.errno))
    finally:
        s.close()
for cid in (1, 2, 3):
    try:
        s = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
    except (AttributeError, OSError) as e:
        out.append('vsock cid %d 2024 socket not available: %s' % (cid, e.__class__.__name__))
        continue
    s.settimeout(2)
    try:
        s.connect((cid, 2024))
        out.append('vsock cid %d 2024 connect accepted (closed at once, nothing sent)' % cid)
    except OSError as e:
        out.append('vsock cid %d 2024 %s %s' % (cid, e.__class__.__name__, e.errno))
    finally:
        s.close()
out.append('')
try:
    out.append('PID 1: ' + open('/proc/1/cmdline', 'rb').read().replace(b'\0', b' ').decode('utf-8', 'replace'))
except OSError as e:
    out.append('PID 1: unreadable %s' % e)
out.append('user-space processes:')
out.append('%5s %5s %-8s %s' % ('PID', 'PPID', 'USER', 'COMMAND'))
for p in sorted((int(x) for x in os.listdir('/proc') if x.isdigit())):
    try:
        st = open('/proc/%d/stat' % p).read()
        comm = st[st.index('(') + 1:st.rindex(')')]
        ppid = int(st[st.rindex(')') + 2:].split()[1])
        uid = os.stat('/proc/%d' % p).st_uid
        try:
            user = pwd.getpwuid(uid).pw_name
        except KeyError:
            user = str(uid)
        if ppid == 2 or p == 2:
            continue                     # kernel threads
        out.append('%5d %5d %-8s %s' % (p, ppid, user, comm))
    except (OSError, ValueError):
        continue
print('\n'.join(out))
'''


def main(root, outp):
    root = os.path.realpath(root)
    sys.path.insert(0, root)
    import tools.evkit as E
    d = tempfile.mkdtemp(prefix='audit_api_')
    probe = os.path.join(d, 'probe.py')
    open(probe, 'w').write(PROBE)
    u = E.run_unit('audit-process-api-reach', E.child_cmd(probe), 120, E.clean_env(d), root)
    with open(outp, 'w') as fh:
        fh.write('BUILDER-EXECUTED: NOT INDEPENDENT. Process-API reach from a unit started by evkit.run_unit (how=%s, exit=%s, leaked=%s); '
                 'auditor environment names: %s\n' % (u.how, u.returncode, u.leaked, sorted(os.environ)))
        fh.write(u.stdout)
        if u.stderr.strip():
            fh.write('\nstderr:\n' + u.stderr[-2000:])
    print('wrote', outp, 'how=%s exit=%s' % (u.how, u.returncode))
    return 0 if u.how == 'exit' and u.returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
