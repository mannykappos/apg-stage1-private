"""Contract suites for the two M3 ports: FileStorePort (EDR-07, cases FS-*) and JobRunnerPort (EDR-04, cases JR-*).  Same method as the M2 suites: an implementation
supplies a FACTORY returning a fresh environment for every case; a case passes if it returns without raising; failure behaviour is tested as hard as success.

  FileEnv(provider, files, advance)
  JobEnv(provider, store, audit, make_runner, advance, sleeps)   make_runner(handler, max_attempts=3) -> a runner with run(job), requeue(job), unrecorded
                                                                 sleeps: a list the runner's injected sleep appends to"""
import dataclasses, hashlib
from .. import ports
from ..contracts.framework import check, raises, session
from .ports_m3 import FileNotFound, IntegrityError, NotPermitted, ScanInfected, ScanRequired, SCANNER_ROLE
from .jobs import TransientError

CASES = []


@dataclasses.dataclass
class FileEnv:
    provider: object
    files: object
    advance: object


@dataclasses.dataclass
class JobEnv:
    provider: object
    store: object
    audit: object
    make_runner: object
    advance: object
    sleeps: list


def case(suite, cid, text):
    def deco(fn):
        CASES.append((suite, cid, text, fn))
        return fn
    return deco


AUTH = (ports.Unauthenticated, ports.NoContext)
FS, JR = 'file_store', 'job_runner'


def two(env):
    return session(env, 'tokA', 'tenant-A', 'alice', ('importer',)), session(env, 'tokB', 'tenant-B', 'bob', ('importer',))


def scanner(env, tenant='tenant-A'):
    return session(env, 'scan-' + tenant, tenant, 'scanner-svc', (SCANNER_ROLE,), kind='service')


# ---------------------------------------------------------------- FileStorePort
@case(FS, 'FS-01', 'a new file is stored unscanned with its SHA-256, size and name; the id depends only on the bytes')
def fs01(env):
    a, b = two(env)
    m = env.files.put(a, 'inv.csv', b'abc')
    check(m.sha256 == hashlib.sha256(b'abc').hexdigest() and m.size == 3 and m.name == 'inv.csv' and m.scan_status == 'unscanned' and m.tenant_id == 'tenant-A', 'metadata wrong')
    check(env.files.put(b, 'other-name.csv', b'abc').file_id == m.file_id, 'the id must depend on the bytes only')
    check(env.files.put(a, 'x.csv', b'abd').file_id != m.file_id, 'different bytes must give a different id')


@case(FS, 'FS-02', 'storing the same bytes again is one file; different bytes under the same name never replace the first file')
def fs02(env):
    a, _ = two(env)
    m1 = env.files.put(a, 'f.csv', b'one'); m1b = env.files.put(a, 'f.csv', b'one'); m2 = env.files.put(a, 'f.csv', b'two')
    check(m1 == m1b and len(env.files.list(a)) == 2 and m1.file_id != m2.file_id, 'idempotence or immutability broken')
    sc = scanner(env)
    for m in (m1, m2):
        env.files.record_scan(sc, m.file_id, 'clean')
    check(env.files.read(a, m1.file_id) == b'one' and env.files.read(a, m2.file_id) == b'two', 'a later file replaced an earlier one')


@case(FS, 'FS-03', 'bytes returned are the exact bytes stored, as an independent immutable copy')
def fs03(env):
    a, _ = two(env)
    data = bytearray(b'hello')
    m = env.files.put(a, 'f.csv', data)
    data[0] = 0x58                                                      # changing the caller's buffer afterwards must not change the stored file
    env.files.record_scan(scanner(env), m.file_id, 'clean')
    r = env.files.read(a, m.file_id)
    check(type(r) is bytes and r == b'hello', 'stored bytes changed or returned as a mutable buffer')
    check(env.files.read(a, m.file_id) == b'hello' and env.files.meta(a, m.file_id).sha256 == hashlib.sha256(b'hello').hexdigest(), 'second read differs')


@case(FS, 'FS-04', 'files are invisible across tenants: another tenant gets None or FileNotFound, exactly as for a missing file, and lists only its own')
def fs04(env):
    a, b = two(env)
    m = env.files.put(a, 'secret.csv', b'only-a')
    env.files.record_scan(scanner(env, 'tenant-A'), m.file_id, 'clean')
    check(env.files.meta(b, m.file_id) is None and env.files.list(b) == (), 'tenant B can see tenant A metadata')
    raises(FileNotFound, lambda: env.files.read(b, m.file_id), 'cross-tenant read')
    raises(FileNotFound, lambda: env.files.read(b, 'F-doesnotexist'), 'missing read')
    raises((FileNotFound, NotPermitted), lambda: env.files.record_scan(scanner(env, 'tenant-B'), m.file_id, 'infected'), 'cross-tenant scan verdict')
    check(env.files.read(a, m.file_id) == b'only-a' and env.files.meta(a, m.file_id).scan_status == 'clean', "tenant B's attempt changed tenant A's file")
    mb = env.files.put(b, 'secret.csv', b'only-a')
    check(mb.scan_status == 'unscanned', "tenant A's clean verdict leaked to tenant B's copy of the same bytes")


@case(FS, 'FS-05', 'every operation refuses a missing, forged, expired or revoked context')
def fs05(env):
    a, _ = two(env)
    m = env.files.put(a, 'f.csv', b'x')
    forged = dataclasses.replace(a, tenant_id='tenant-B')
    ops = [lambda c: env.files.put(c, 'f.csv', b'y'), lambda c: env.files.meta(c, m.file_id), lambda c: env.files.list(c), lambda c: env.files.read(c, m.file_id),
           lambda c: env.files.read_for_scan(c, m.file_id), lambda c: env.files.record_scan(c, m.file_id, 'clean')]
    for i, op in enumerate(ops):
        raises(AUTH, lambda: op(None), f'op {i} with no context')
        raises(AUTH, lambda: op(forged), f'op {i} with a forged context')
    env.provider._contract_revoke('tokA')
    raises(AUTH, lambda: env.files.read(a, m.file_id), 'revoked context')


@case(FS, 'FS-06', 'SCAN GATE: an unscanned file cannot be read; clean can; infected cannot')
def fs06(env):
    a, _ = two(env)
    m = env.files.put(a, 'f.csv', b'payload')
    raises(ScanRequired, lambda: env.files.read(a, m.file_id), 'read of an unscanned file')
    sc = scanner(env)
    env.files.record_scan(sc, m.file_id, 'infected')
    raises(ScanInfected, lambda: env.files.read(a, m.file_id), 'read of an infected file')
    m2 = env.files.put(a, 'g.csv', b'payload2')
    env.files.record_scan(sc, m2.file_id, 'clean')
    check(env.files.read(a, m2.file_id) == b'payload2', 'clean file should be readable')


@case(FS, 'FS-07', 'only the scanner service may record a verdict or read an unscanned file; infected is terminal; bad verdicts are refused')
def fs07(env):
    a, _ = two(env)
    m = env.files.put(a, 'f.csv', b'payload')
    for who in (a, session(env, 'svc', 'tenant-A', 'other-svc', ('importer',), kind='service'), session(env, 'hum', 'tenant-A', 'carl', (SCANNER_ROLE,), kind='human')):
        raises(NotPermitted, lambda: env.files.record_scan(who, m.file_id, 'clean'), 'verdict by a non-scanner')
        raises(NotPermitted, lambda: env.files.read_for_scan(who, m.file_id), 'raw read by a non-scanner')
    sc = scanner(env)
    check(env.files.read_for_scan(sc, m.file_id) == b'payload', 'scanner could not read the file to scan it')
    raises(ports.PayloadInvalid, lambda: env.files.record_scan(sc, m.file_id, 'probably-fine'), 'bad verdict')
    env.files.record_scan(sc, m.file_id, 'infected')
    raises(NotPermitted, lambda: env.files.record_scan(sc, m.file_id, 'clean'), 'infected must be terminal')
    raises(ScanInfected, lambda: env.files.read(a, m.file_id), 'file became readable')
    m2 = env.files.put(a, 'g.csv', b'second')
    env.files.record_scan(sc, m2.file_id, 'clean'); env.files.record_scan(sc, m2.file_id, 'clean')
    env.files.record_scan(sc, m2.file_id, 'infected')                                    # a later rescan may withdraw a clean verdict
    raises(ScanInfected, lambda: env.files.read(a, m2.file_id), 'rescan did not withdraw the clean verdict')


@case(FS, 'FS-08', 'damaged stored bytes are refused on every read path, never returned')
def fs08(env):
    a, _ = two(env)
    m = env.files.put(a, 'f.csv', b'precious')
    sc = scanner(env)
    env.files.record_scan(sc, m.file_id, 'clean')
    env.files._contract_corrupt('tenant-A', m.file_id)
    raises(IntegrityError, lambda: env.files.read(a, m.file_id), 'read of damaged bytes')
    raises(IntegrityError, lambda: env.files.read_for_scan(sc, m.file_id), 'scan-read of damaged bytes')


@case(FS, 'FS-09', 'oversize data, non-bytes and unsafe names are refused and leave nothing behind')
def fs09(env):
    a, _ = two(env)
    raises(ports.PayloadInvalid, lambda: env.files.put(a, 'big.csv', b'x' * (env.files.max_bytes + 1)), 'oversize')
    for bad in ('text', None, 12, ['a']):
        raises(ports.PayloadInvalid, lambda: env.files.put(a, 'f.csv', bad), f'data {bad!r}')
    for name in ('', '../etc/passwd', 'a/b.csv', 'a\\b.csv', 'bad\x00.csv', 'new\nline.csv', None, 5, 'x' * 201):
        raises(ports.PayloadInvalid, lambda: env.files.put(a, name, b'ok'), f'name {name!r}')
    check(env.files.list(a) == (), 'a refused put left a file behind')
    check(env.files.put(a, 'empty.csv', b'').size == 0, 'an empty file is a valid stored file (the pipeline refuses it later)')


@case(FS, 'FS-10', 'list is ordered by id, shows only the caller tenant, and reflects scan status')
def fs10(env):
    a, b = two(env)
    ms = [env.files.put(a, f'f{i}.csv', f'content-{i}'.encode()) for i in range(5)]
    env.files.put(b, 'b.csv', b'other')
    env.files.record_scan(scanner(env), ms[2].file_id, 'clean')
    lst = env.files.list(a)
    check([m.file_id for m in lst] == sorted(m.file_id for m in ms) and len(lst) == 5, 'list wrong')
    check(sorted(m.scan_status for m in lst) == ['clean', 'unscanned', 'unscanned', 'unscanned', 'unscanned'], 'scan status not reflected')


# ---------------------------------------------------------------- JobRunnerPort
def job(env, jid='J-1', payload=None, token='tokA', **extra):
    return dict({'job_id': jid, 'credentials': token, 'payload': payload if payload is not None else {'n': 1}}, **extra)


def counting(env, fn=None):
    calls = []
    def h(scoped, payload):
        calls.append(payload)
        return fn(scoped, payload, len(calls)) if fn else {'done': len(calls)}
    return h, calls


def jobrec(env, token, jid):
    from .. import tenancy
    return tenancy.ScopedStore(env.store, env.audit, env.provider.resolve(token)).get('job', jid)


def setup(env):
    env.provider._contract_register_session('tokA', 'tenant-A', 'alice', ('importer',), 'human', 360000)
    env.provider._contract_register_session('tokB', 'tenant-B', 'bob', ('importer',), 'human', 360000)


@case(JR, 'JR-01', 'a job runs once with a store bound to the credentials\' tenant and a clean payload; the result is recorded in that tenant')
def jr01(env):
    setup(env)
    seen = []
    h, calls = counting(env, lambda s, p, n: seen.append((s.ctx.tenant_id, p)) or {'ok': True})
    r = env.make_runner(h).run(job(env))
    check(r['status'] == 'succeeded' and r['attempts'] == 1 and r['result'] == {'ok': True} and r['replay'] is False, f'bad result {r}')
    check(seen == [('tenant-A', {'n': 1})], 'handler did not get the tenant-bound store and payload')
    rec = jobrec(env, 'tokA', 'J-1')
    check(rec is not None and rec.payload['status'] == 'succeeded', 'job record missing')


@case(JR, 'JR-02', 'REPLAY: a job id that already succeeded is not run again, even if resubmitted with a different payload; the stored result comes back')
def jr02(env):
    setup(env)
    h, calls = counting(env)
    run = env.make_runner(h)
    first = run.run(job(env))
    again = run.run(job(env, payload={'n': 999}))
    third = env.make_runner(h).run(job(env))                                        # a different runner object (a restarted worker)
    check(len(calls) == 1, f'handler ran {len(calls)} times: a second financial effect')
    check(again['replay'] is True and third['replay'] is True and again['result'] == first['result'] == third['result'], 'replay result wrong')


@case(JR, 'JR-03', 'retries are BOUNDED: a handler that always fails transiently is called exactly max_attempts times, then dead-lettered with the errors kept')
def jr03(env):
    setup(env)
    def always(s, p, n):
        raise TransientError(f'flaky {n}')
    h, calls = counting(env, always)
    r = env.make_runner(h, 4).run(job(env))
    check(len(calls) == 4 and r['status'] == 'dead_letter' and r['attempts'] == 4, f'not bounded: {len(calls)} calls, {r}')
    rec = jobrec(env, 'tokA', 'J-1')
    check(rec.payload['status'] == 'dead_letter' and len(rec.payload['errors']) == 4, 'dead-letter record missing or errors lost')


@case(JR, 'JR-04', 'waits between retries are taken from the injected sleep, one fewer than the attempts, never decreasing')
def jr04(env):
    setup(env)
    def always(s, p, n):
        raise TransientError('x')
    h, _ = counting(env, always)
    env.make_runner(h, 4).run(job(env))
    w = list(env.sleeps)
    check(len(w) == 3 and all(w[i] <= w[i + 1] for i in range(2)) and all(isinstance(x, (int, float)) and x >= 0 for x in w), f'waits wrong: {w}')


@case(JR, 'JR-05', 'a transient failure followed by success is a success, with the number of attempts recorded')
def jr05(env):
    setup(env)
    def flaky(s, p, n):
        if n < 3:
            raise TransientError('try again')
        return {'finally': n}
    h, calls = counting(env, flaky)
    r = env.make_runner(h).run(job(env))
    check(r['status'] == 'succeeded' and r['attempts'] == 3 and r['result'] == {'finally': 3} and len(calls) == 3, f'bad {r}')


@case(JR, 'JR-06', 'a permanent error is dead-lettered at once: no retry, no wait, and the error is kept')
def jr06(env):
    setup(env)
    def boom(s, p, n):
        raise ValueError('bad record layout')
    h, calls = counting(env, boom)
    r = env.make_runner(h, 5).run(job(env))
    check(len(calls) == 1 and r['status'] == 'dead_letter' and env.sleeps == [], f'permanent error retried: {len(calls)} calls')
    rec = jobrec(env, 'tokA', 'J-1')
    check(rec is not None and rec.payload['status'] == 'dead_letter' and 'ValueError' in ' '.join(rec.payload['errors']), 'dead-letter record missing or error lost')


@case(JR, 'JR-07', 'RE-AUTHENTICATION: if the credentials are revoked mid-job, the next attempt does not run the handler')
def jr07(env):
    setup(env)
    def revoke_then_fail(s, p, n):
        env.provider._contract_revoke('tokA')
        raise TransientError('worker lost its session')
    h, calls = counting(env, revoke_then_fail)
    r = env.make_runner(h).run(job(env))
    check(len(calls) == 1 and r['status'] == 'dead_letter', f'handler ran with revoked credentials ({len(calls)} calls, {r})')


@case(JR, 'JR-08', 'a terminal failure that cannot be recorded (credentials revoked) is reported as unrecorded and kept by the runner, never dropped silently')
def jr08(env):
    setup(env)
    def revoke_then_fail(s, p, n):
        env.provider._contract_revoke('tokA')
        raise TransientError('worker lost its session')
    h, _ = counting(env, revoke_then_fail)
    run = env.make_runner(h)
    r = run.run(job(env))
    check(r.get('recorded') is False and len(run.unrecorded) == 1 and run.unrecorded[0]['job_id'] == 'J-1', f'lost failure: {r}, {run.unrecorded}')


@case(JR, 'JR-09', 'TENANT ISOLATION: the same job id in two tenants is two jobs; one tenant\'s success is not a replay for the other and records are not shared')
def jr09(env):
    setup(env)
    h, calls = counting(env, lambda s, p, n: {'ran_as': s.ctx.tenant_id, 'tenant': s.ctx.tenant_id})
    run = env.make_runner(h)
    ra, rb = run.run(job(env)), run.run(job(env, token='tokB'))
    check(len(calls) == 2 and ra['result'] == {'ran_as': 'tenant-A'} and rb['result'] == {'ran_as': 'tenant-B'} and rb['replay'] is False, f'tenants mixed: {ra} {rb}')
    check(jobrec(env, 'tokA', 'J-1').payload['result'] == {'ran_as': 'tenant-A'} and jobrec(env, 'tokB', 'J-1').payload['result'] == {'ran_as': 'tenant-B'}, 'job records mixed')
    check(run.run(job(env))['result'] == ra['result'], 'a replay returned something other than what the first run returned')


@case(JR, 'JR-10', 'a job that names another tenant, in the message or the payload, is refused and the handler never runs')
def jr10(env):
    setup(env)
    h, calls = counting(env)
    run = env.make_runner(h)
    r1 = run.run(job(env, claimed_tenant='tenant-B'))
    r2 = run.run(job(env, jid='J-2', payload={'rows': [{'Tenant ID': 'tenant-B'}]}))
    r3 = run.run(job(env, jid='J-3', token='no-such-token'))
    check(calls == [] and all(r['status'] in ('refused', 'dead_letter') for r in (r1, r2, r3)), f'a hostile job reached the handler: {calls}, {r1}, {r2}, {r3}')
    check(jobrec(env, 'tokB', 'J-1') is None and jobrec(env, 'tokB', 'J-2') is None, 'a record appeared in the named tenant')


@case(JR, 'JR-11', 'a dead-lettered job is not re-run by resubmission; only an explicit requeue runs it again, and that works once the cause is fixed')
def jr11(env):
    setup(env)
    state = {'broken': True}
    def h(scoped, payload):
        state.setdefault('calls', 0); state['calls'] += 1
        if state['broken']:
            raise ValueError('bad input')
        return {'fixed': True}
    run = env.make_runner(h)
    r = run.run(job(env))
    again = run.run(job(env))
    check(r['status'] == 'dead_letter' and again['status'] == 'dead_letter' and state['calls'] == 1, 'a dead-lettered job was re-run on resubmission')
    state['broken'] = False
    q = run.requeue(job(env))
    check(q['status'] == 'succeeded' and state['calls'] == 2 and jobrec(env, 'tokA', 'J-1').payload['status'] == 'succeeded', f'requeue failed: {q}')
    check(run.run(job(env))['replay'] is True and state['calls'] == 2, 'after requeue success the job must replay, not re-run')


@case(JR, 'JR-12', 'requeue is refused for a job that is unknown, already succeeded, or submitted with bad credentials')
def jr12(env):
    setup(env)
    h, calls = counting(env)
    run = env.make_runner(h)
    raises(ValueError, lambda: run.requeue(job(env, jid='J-never')), 'requeue of an unknown job')
    run.run(job(env))
    raises(ValueError, lambda: run.requeue(job(env)), 'requeue of a succeeded job')
    raises(AUTH, lambda: run.requeue(job(env, token='bad')), 'requeue with bad credentials')
    check(len(calls) == 1, 'requeue ran a handler it should not have')


@case(JR, 'JR-13', 'the audit chain of the tenant records success, dead-letter and replay; the chain verifies; nothing is written to another tenant\'s chain')
def jr13(env):
    setup(env)
    def fail(s, p, n):
        raise ValueError('x')
    run = env.make_runner(counting(env)[0]); run.run(job(env)); run.run(job(env))
    env.make_runner(counting(env, fail)[0]).run(job(env, jid='J-2'))
    ctx = env.provider.resolve('tokA'); ctxb = env.provider.resolve('tokB')
    types = [e.event_type for e in env.audit.read(ctx)]
    check({'job.succeeded', 'job.replay', 'job.dead_letter'} <= set(types), f'events missing: {types}')
    check(env.audit.verify(ctx).ok and env.audit.read(ctxb) == (), 'chain broken or another tenant was written to')


@case(JR, 'JR-14', 'the result returned to the caller is an independent copy: changing it changes neither the record nor a later replay')
def jr14(env):
    setup(env)
    h, _ = counting(env, lambda s, p, n: {'items': [1, 2, 3]})
    run = env.make_runner(h)
    r = run.run(job(env))
    r['result']['items'].append(999)
    again = run.run(job(env))
    again['result']['items'].append(1000)
    check(jobrec(env, 'tokA', 'J-1').payload['result'] == {'items': [1, 2, 3]} and run.run(job(env))['result'] == {'items': [1, 2, 3]}, 'a returned result was shared with stored state')


def run_all(file_factory, job_factory, suites=None):
    """-> list of (suite, case_id, description, passed, detail)."""
    out = []
    for suite, cid, text, fn in CASES:
        if suites and suite not in suites:
            continue
        try:
            fn((file_factory if suite == FS else job_factory)())
            out.append((suite, cid, text, True, ''))
        except Exception as e:
            out.append((suite, cid, text, False, f'{type(e).__name__}: {e}'))
    return out
