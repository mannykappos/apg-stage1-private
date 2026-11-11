#!/usr/bin/env python3
"""Builder tool (outside the successor tree), corrective pass 2, section P.2 / P.9: the outside-service audit.
How it is started (amendment 5, discrepancy 7, rewritten in the 2026-11-11 recovery from Appendix A part 1, row 7): by the builder with
env -i and exactly five names (PATH TMPDIR LANG LC_ALL TZ), as python3 -I -S, from a fresh extraction of a frozen ZIP.
How it starts its children: the subprocess unit through the freeze's own tools/evkit.py run_unit (cmd evkit.child_cmd(probe),
env evkit.clean_env(tmp), cwd the extraction root), and the forked unit through the freeze's own run_forked (env evkit.clean_env(tmp)),
so the record shows what the freeze itself gives a unit (AM-4: stdin /dev/null; the P.2 scrub).  As a labelled control only, one raw
os.fork with no scrub shows what the auditor process itself holds (an extra descriptor and variable planted on purpose); it is not how
the freeze starts a unit.  Each child records what it actually received and can reach.  Nothing is sent to any socket: a connect is
attempted and closed at once.
Secret-bearing variables are reported by name only (P.2).
Usage: python3 -I -S audit_outside_services_s1.py EXTRACTION_ROOT OUT.txt      BUILDER-EXECUTED: NOT INDEPENDENT."""
import json, os, re, socket, stat, subprocess, sys, tempfile

SECRET = re.compile(r'(TOKEN|SECRET|PASSW|PASSWD|CREDENTIAL|AUTH|API_?KEY|PRIVATE|COOKIE|SESSION)', re.I)
SOCKET_DIRS = ['/run', '/var/run', '/tmp', '/var/tmp', '/dev/shm', os.path.expanduser('~') if os.path.expanduser('~') != '~' else '/root']
LAUNCHERS = ['at', 'batch', 'atq', 'crontab', 'systemd-run', 'systemctl', 'dbus-send', 'busctl', 'docker', 'podman', 'nerdctl', 'ctr',
             'runc', 'nsenter', 'unshare', 'setsid', 'nohup', 'daemonize', 'start-stop-daemon', 'sudo', 'su', 'pkexec', 'ssh']
KNOWN_SOCKETS = ['/run/dbus/system_bus_socket', '/var/run/dbus/system_bus_socket', '/run/systemd/private', '/run/systemd/notify',
                 '/run/docker.sock', '/var/run/docker.sock', '/run/containerd/containerd.sock', '/run/podman/podman.sock',
                 '/run/crio/crio.sock', '/run/user']
SPOOLS = ['/var/spool/cron', '/var/spool/cron/crontabs', '/var/spool/at', '/var/spool/atjobs', '/etc/cron.d', '/etc/crontab']

PROBE = r'''
import json, os, re, socket, stat, sys
SECRET = re.compile(%r, re.I)
out = {}
fds = {}
for fd in sorted(os.listdir('/proc/self/fd'), key=int):
    try:
        fds[fd] = os.readlink('/proc/self/fd/' + fd)
    except OSError as e:
        fds[fd] = 'unreadable %%s' %% e
out['fds'] = fds
out['env'] = {k: ('<secret-bearing: value not recorded>' if SECRET.search(k) or re.search(r'//[^/@]+@', v) else v) for k, v in sorted(os.environ.items())}
out['secret_bearing_names'] = sorted(k for k, v in os.environ.items() if SECRET.search(k) or re.search(r'//[^/@]+@', v))
out['uid'], out['gid'], out['groups'] = os.getuid(), os.getgid(), os.getgroups()
out['pid'], out['ppid'], out['pgid'], out['sid'] = os.getpid(), os.getppid(), os.getpgid(0), os.getsid(0)
def can_connect(path):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(path)
        return 'connect accepted (closed at once, nothing sent)'
    except OSError as e:
        return 'connect refused: %%s' %% e.__class__.__name__ + ' ' + str(e.errno)
    finally:
        s.close()
unix = []
try:
    for line in open('/proc/net/unix').read().splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 8:
            name = parts[7]
            unix.append(name)
except OSError as e:
    unix = ['unreadable %%s' %% e]
out['proc_net_unix_named'] = sorted(set(unix))
checked = {}
for name in sorted(set(unix)):
    if name.startswith('@'):
        checked[name] = 'abstract socket (not connectable by path; listed for the record)'
    elif name.startswith('/') and os.path.exists(name):
        st = os.stat(name)
        checked[name] = 'owner %%d:%%d mode %%o; %%s' %% (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode), can_connect(name))
out['proc_net_unix_checked'] = checked
found = {}
import time as _t
_deadline = _t.monotonic() + 30
walk_notes = []
for d in %r:
    depth = 3 if d in ('/tmp', '/var/tmp') else 5
    for root, dirs, files in os.walk(d, onerror=lambda e: None):
        if _t.monotonic() > _deadline:
            walk_notes.append('walk stopped at the 30 s budget in %%s (the complete list of bound sockets is /proc/net/unix above)' %% root)
            dirs[:] = []
            break
        if root.count(os.sep) - d.count(os.sep) >= depth:
            dirs[:] = []
            continue
        for f in files + dirs:
            p = os.path.join(root, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if stat.S_ISSOCK(st.st_mode):
                found[p] = 'owner %%d:%%d mode %%o; %%s' %% (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode), can_connect(p))
out['socket_files'] = found
out['socket_walk'] = {'depths': 'tmp and var/tmp 3, others 5', 'notes': walk_notes}
known = {}
for p in %r:
    known[p] = ('exists' if os.path.exists(p) else 'absent') + ((' ' + oct(stat.S_IMODE(os.stat(p).st_mode))) if os.path.exists(p) else '')
out['known_service_paths'] = known
spools = {}
for p in %r:
    if os.path.exists(p):
        st = os.stat(p)
        spools[p] = 'exists owner %%d:%%d mode %%o writable_by_unit=%%s' %% (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode), os.access(p, os.W_OK))
    else:
        spools[p] = 'absent'
out['spools'] = spools
path_dirs = os.environ.get('PATH', '').split(':')
launch = {}
for name in %r:
    hits = [os.path.join(d, name) for d in path_dirs if d and os.access(os.path.join(d, name), os.X_OK)]
    launch[name] = hits or 'not on the unit PATH'
out['launchers_on_unit_path'] = launch
suid = []
for d in path_dirs:
    try:
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if stat.S_ISREG(st.st_mode) and st.st_mode & (stat.S_ISUID | stat.S_ISGID):
                suid.append('%%s mode %%o owner %%d' %% (p, stat.S_IMODE(st.st_mode), st.st_uid))
    except OSError:
        pass
out['setuid_setgid_on_unit_path'] = suid
net = {}
net['proxy_variables_in_unit_env'] = sorted(k for k in os.environ if 'proxy' in k.lower())
try:
    net['proc_net_route'] = open('/proc/net/route').read().splitlines()[:6]
except OSError as e:
    net['proc_net_route'] = 'unreadable %%s' %% e
try:
    net['resolv_conf'] = [l for l in open('/etc/resolv.conf').read().splitlines() if l.strip() and not l.startswith('#')]
except OSError as e:
    net['resolv_conf'] = 'unreadable %%s' %% e
for host, port in (('1.1.1.1', 443), ('8.8.8.8', 53)):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((host, port))
        net['direct_tcp_%%s_%%d' %% (host, port)] = 'connect accepted (closed at once, nothing sent)'
    except OSError as e:
        net['direct_tcp_%%s_%%d' %% (host, port)] = 'connect failed: %%s %%s' %% (e.__class__.__name__, e.errno)
    finally:
        s.close()
out['network'] = net
print(json.dumps(out, indent=1, sort_keys=True))
''' % (SECRET.pattern, SOCKET_DIRS, KNOWN_SOCKETS, SPOOLS, LAUNCHERS)


def main():
    root, outp = os.path.realpath(sys.argv[1]), sys.argv[2]
    sys.path.insert(0, root)
    import tools.evkit as E
    probe_dir = tempfile.mkdtemp(prefix='audit_probe_')
    probe = os.path.join(probe_dir, 'probe.py')
    open(probe, 'w').write(PROBE)
    tmp = tempfile.mkdtemp(prefix='audit_unit_tmp_')
    report = {'zip_extraction': root, 'auditor_pid': os.getpid(), 'auditor_env_names': sorted(os.environ)}
    import io, contextlib

    def run_probe():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(compile(PROBE, probe, 'exec'), {'__name__': '__main__'})
        return json.loads(buf.getvalue())

    # The parent holds an extra descriptor and an extra environment variable on purpose, so the record shows whether a unit inherits them.
    extra = open(os.path.join(probe_dir, 'parent_only.txt'), 'w')
    os.environ['AUDIT_PARENT_ONLY'] = 'parent-only-value'
    # 1. a subprocess unit, through the freeze's run_unit (discrepancy 7)
    u = E.run_unit('audit-subprocess-unit', E.child_cmd(probe), 120, E.clean_env(tmp), root)
    rec = u.stdout
    try:
        rec = json.loads(u.stdout) if u.how == 'exit' and u.returncode == 0 else u.stdout[-2000:]
    except ValueError:
        rec = u.stdout[-2000:]
    report['subprocess_unit'] = {'started_by': 'evkit.run_unit', 'how': u.how, 'returncode': u.returncode, 'leaked': u.leaked,
                                 'stderr': u.stderr[-2000:], 'record': rec}
    # 2. a forked unit, through the freeze's run_forked (discrepancy 7)
    f = E.run_forked('audit-forked-unit', run_probe, 120, E.clean_env(tmp))
    msg = f.get('message')
    try:
        frec = json.loads(msg.decode('utf-8')) if msg else None
    except ValueError:
        frec = msg.decode('utf-8', 'replace')[-2000:]
    report['forked_unit'] = {'started_by': 'evkit.run_forked', 'how': f.get('how'), 'status': f.get('status'),
                             'leaked': f.get('leaked'), 'record': frec}
    # 3. control only (not how the freeze starts a unit): a raw fork with no scrub, to show what the auditor itself holds
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:
        try:
            os.close(r)
            os.write(w, json.dumps(run_probe()).encode())
        finally:
            os._exit(0)
    os.close(w)
    data = b''
    while True:
        b = os.read(r, 65536)
        if not b:
            break
        data += b
    os.close(r)
    os.waitpid(pid, 0)
    report['control_raw_fork_no_scrub'] = json.loads(data.decode())
    extra.close()
    del os.environ['AUDIT_PARENT_ONLY']
    with open(outp, 'w') as fh:
        fh.write('BUILDER-EXECUTED: NOT INDEPENDENT. Corrective pass 2, P.2 outside-service audit, from %s\n' % root)
        fh.write(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print('wrote', outp)


if __name__ == '__main__':
    main()
