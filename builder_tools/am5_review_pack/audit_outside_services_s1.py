#!/usr/bin/env python3
"""Builder tool (outside the successor tree), corrective pass 2, section P.2 / P.9: the outside-service audit.
Run as the run index runs a runner (python3 -I -S, env PATH TMPDIR LANG LC_ALL TZ only), from a fresh extraction of a frozen ZIP.
It starts one child exactly as tools/evkit.py run_child starts a unit today (subprocess.run, cwd=root, env=evkit.clean_env(tmp),
capture_output, close_fds default), and one child by os.fork (before any scrub, and after the scrub P.2 authorises), and has each
record what it actually received and can reach.  Nothing is sent to any socket: a connect is attempted and closed at once.
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
    # 1. a subprocess unit, started exactly as run_child starts one today
    p = subprocess.run(E.child_cmd(probe), cwd=root, env=E.clean_env(tmp), capture_output=True, text=True, timeout=120)
    report['subprocess_unit'] = {'returncode': p.returncode, 'stderr': p.stderr[-2000:], 'record': json.loads(p.stdout) if p.returncode == 0 else p.stdout[-2000:]}
    # 2. a forked unit, before any scrub: the parent holds an extra descriptor and an extra environment variable on purpose
    extra = open(os.path.join(probe_dir, 'parent_only.txt'), 'w')
    os.environ['AUDIT_PARENT_ONLY'] = 'parent-only-value'
    for scrub in (False, True):
        r, w = os.pipe()
        pid = os.fork()
        if pid == 0:
            try:
                os.close(r)
                if scrub:   # the scrub P.2 authorises for forked units
                    os.closerange(3, w)
                    os.closerange(w + 1, 65536)
                    os.environ.clear()
                    os.environ.update(E.clean_env(tmp))
                g = {'__name__': '__main__'}
                import io, contextlib
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    exec(compile(PROBE, probe, 'exec'), g)
                os.write(w, buf.getvalue().encode())
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
        report['forked_unit_%s' % ('after_scrub' if scrub else 'before_scrub')] = json.loads(data.decode())
    extra.close()
    del os.environ['AUDIT_PARENT_ONLY']
    with open(outp, 'w') as fh:
        fh.write('BUILDER-EXECUTED: NOT INDEPENDENT. Corrective pass 2, P.2 outside-service audit, from %s\n' % root)
        fh.write(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print('wrote', outp)


if __name__ == '__main__':
    main()
