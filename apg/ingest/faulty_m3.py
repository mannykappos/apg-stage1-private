"""DELIBERATELY BROKEN FileStore and JobRunner implementations.  They exist only to prove the M3 contract suites have teeth: each fault must make at least the listed
cases fail.  Never use these for anything else.   FAULTS maps id -> (description, kind, factory, expected failing case ids)."""
import hashlib
from .. import canon, tenancy
from ..ports import ConflictError, PortError
from ..reference_impl import _need
from .filestore import InMemoryFileStore, _is_scanner
from .jobs import JobRunner, TransientError
from .ports_m3 import CLEAN, INFECTED, UNSCANNED, FileMeta, FileNotFound, NotPermitted, ScanInfected
from .reference_m3 import file_env, job_env


# ------------------------------------------------------------------ file store faults
class ReadsUnscanned(InMemoryFileStore):
    def read(self, ctx, file_id):
        _need(self.provider, ctx)
        return bytes(self._bytes(ctx, file_id)['data'])


class AnyoneCanScan(InMemoryFileStore):
    def record_scan(self, ctx, file_id, verdict):
        r = self._d.get((ctx.tenant_id, file_id))
        if r is None:
            raise FileNotFound(file_id)
        r['scan'] = verdict
        return self._meta(ctx.tenant_id, file_id)


class InfectedCanBeCleaned(InMemoryFileStore):
    def record_scan(self, ctx, file_id, verdict):
        _need(self.provider, ctx)
        if not _is_scanner(ctx):
            raise NotPermitted('scanner only')
        r = self._d.get((ctx.tenant_id, file_id))
        if r is None:
            raise FileNotFound(file_id)
        r['scan'] = verdict
        return self._meta(ctx.tenant_id, file_id)


class GlobalFileIds(InMemoryFileStore):
    """Files are looked up by id across all tenants."""
    def _bytes(self, ctx, file_id):
        for (t, f), r in self._d.items():
            if f == file_id:
                return r
        raise FileNotFound(file_id)

    def meta(self, ctx, file_id):
        _need(self.provider, ctx)
        for (t, f) in self._d:
            if f == file_id:
                return self._meta(t, f)
        return None

    def read(self, ctx, file_id):
        _need(self.provider, ctx)
        for (t, f), r in self._d.items():
            if f == file_id:
                return bytes(r['data'])
        raise FileNotFound(file_id)


class ScanVerdictSharedAcrossTenants(InMemoryFileStore):
    """A clean verdict on some tenant's copy of the same bytes applies to everybody's copy."""
    _verdicts = None

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._verdicts = {}

    def record_scan(self, ctx, file_id, verdict):
        m = super().record_scan(ctx, file_id, verdict)
        self._verdicts[file_id] = verdict
        return m

    def put(self, ctx, name, data, media_type=''):
        m = super().put(ctx, name, data, media_type)
        if m.file_id in self._verdicts:
            self._d[(ctx.tenant_id, m.file_id)]['scan'] = self._verdicts[m.file_id]
        return super().meta(ctx, m.file_id)


class OverwriteByName(InMemoryFileStore):
    """Identity is the name: the second upload under a name replaces the first."""
    def put(self, ctx, name, data, media_type=''):
        _need(self.provider, ctx)
        from .filestore import check_name
        check_name(name)
        from ..ports import PayloadInvalid
        if not isinstance(data, (bytes, bytearray)):
            raise PayloadInvalid('bytes')
        if len(data) > self.max_bytes:
            raise PayloadInvalid('big')
        data = bytes(data)
        fid = 'F-' + hashlib.sha256(name.encode()).hexdigest()[:32]
        self._d[(ctx.tenant_id, fid)] = {'name': name, 'sha': hashlib.sha256(data).hexdigest(), 'size': len(data), 'media': media_type, 'scan': UNSCANNED, 'data': data}
        return self._meta(ctx.tenant_id, fid)


class NoIntegrityCheck(InMemoryFileStore):
    def _bytes(self, ctx, file_id):
        r = self._d.get((ctx.tenant_id, file_id))
        if r is None:
            raise FileNotFound(file_id)
        return r


class AliasedBuffer(InMemoryFileStore):
    """Keeps the caller's buffer and hands back the stored mutable buffer."""
    def put(self, ctx, name, data, media_type=''):
        _need(self.provider, ctx)
        from .filestore import check_name
        check_name(name)
        from ..ports import PayloadInvalid
        if not isinstance(data, (bytes, bytearray)):
            raise PayloadInvalid('bytes')
        sha = hashlib.sha256(bytes(data)).hexdigest()
        fid = self._id(sha)
        if (ctx.tenant_id, fid) not in self._d:
            self._d[(ctx.tenant_id, fid)] = {'name': name, 'sha': sha, 'size': len(data), 'media': media_type, 'scan': UNSCANNED, 'data': data}
        return self._meta(ctx.tenant_id, fid)

    def read(self, ctx, file_id):
        _need(self.provider, ctx)
        r = self._d.get((ctx.tenant_id, file_id))
        if r is None:
            raise FileNotFound(file_id)
        if r['scan'] != CLEAN:
            return super().read(ctx, file_id)
        return r['data']

    def _bytes(self, ctx, file_id):
        r = self._d.get((ctx.tenant_id, file_id))
        if r is None:
            raise FileNotFound(file_id)
        return r


class NoAuthOnList(InMemoryFileStore):
    def list(self, ctx):
        return tuple(self._meta(t, f) for (t, f) in sorted(self._d, key=lambda k: k[1]) if ctx is not None and t == ctx.tenant_id)


class UnsafeNames(InMemoryFileStore):
    def put(self, ctx, name, data, media_type=''):
        import apg.ingest.filestore as fs
        old = fs.check_name
        fs.check_name = lambda n: None
        try:
            return super().put(ctx, name, data, media_type)
        finally:
            fs.check_name = old


class ScannerRoleOnly(InMemoryFileStore):
    """Checks the role but not that the caller is a service identity (a person with the role may scan)."""
    def record_scan(self, ctx, file_id, verdict):
        _need(self.provider, ctx)
        from .ports_m3 import SCANNER_ROLE
        if SCANNER_ROLE not in ctx.roles:
            raise NotPermitted('role')
        return super().record_scan(type(ctx)(ctx.tenant_id, ctx.user_id, ctx.roles, 'service', ctx.session_id, ctx.expires_at, ctx.seal), file_id, verdict) if False else self._force(ctx, file_id, verdict)

    def _force(self, ctx, file_id, verdict):
        r = self._d.get((ctx.tenant_id, file_id))
        if r is None:
            raise FileNotFound(file_id)
        if r['scan'] == INFECTED and verdict == CLEAN:
            raise NotPermitted('terminal')
        r['scan'] = verdict
        return self._meta(ctx.tenant_id, file_id)


# ------------------------------------------------------------------ job runner faults
class RetriesTooLong(JobRunner):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.max_attempts += 3


class AuthenticatesOnce(JobRunner):
    """Re-authentication happens once; later attempts keep the first context."""
    def run(self, job):
        scoped, clean = tenancy.bind_job(self.provider, self.store, self.audit, job)
        orig = tenancy.bind_job
        tenancy.bind_job = lambda *a, **k: (scoped, clean)
        try:
            return super().run(job)
        finally:
            tenancy.bind_job = orig


class RerunsSucceeded(JobRunner):
    def run(self, job):
        scoped, clean = tenancy.bind_job(self.provider, self.store, self.audit, job)
        prior = scoped.get('job', job['job_id'])
        if prior is not None and prior.payload['status'] == 'succeeded':
            scoped.put('job', job['job_id'], dict(canon.deep_copy(prior.payload), status='queued_again'), expected_revision=prior.revision)
        return super().run(job)


class NoDeadLetterRecord(JobRunner):
    def _record(self, scoped, job_id, status, attempts, errors, result):
        if status == 'dead_letter':
            return None
        return super()._record(scoped, job_id, status, attempts, errors, result)


class AutoRequeue(JobRunner):
    def run(self, job):
        scoped, _ = tenancy.bind_job(self.provider, self.store, self.audit, job)
        prior = scoped.get('job', job['job_id'])
        if prior is not None and prior.payload['status'] == 'dead_letter':
            scoped.put('job', job['job_id'], dict(canon.deep_copy(prior.payload), status='queued_again'), expected_revision=prior.revision)
        return super().run(job)


class TrustsMessage(JobRunner):
    """Skips the tenant-claim screen: whatever is in the message is passed to the handler."""
    def run(self, job):
        orig = tenancy.bind_job
        def loose(provider, store, audit, j):
            ctx = provider.resolve(j['credentials'])
            return tenancy.ScopedStore(store, audit, ctx), j.get('payload', {})
        tenancy.bind_job = loose
        try:
            return super().run(job)
        finally:
            tenancy.bind_job = orig


class GlobalJobTable(JobRunner):
    """Job results are remembered by job id only, across tenants."""
    _seen = {}

    def run(self, job):
        key = job['job_id']
        if key in GlobalJobTable._seen:
            return dict(GlobalJobTable._seen[key], replay=True)
        r = super().run(job)
        if r.get('status') == 'succeeded':
            GlobalJobTable._seen[key] = r
        return r

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        GlobalJobTable._seen = {}


class SharesResultObject(JobRunner):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._cache = {}

    def run(self, job):
        r = super().run(job)
        if r.get('status') == 'succeeded':
            key = (job['credentials'], job['job_id'])
            if key in self._cache:
                return dict(r, result=self._cache[key])
            self._cache[key] = r['result']
        return r


class SwallowsUnrecorded(JobRunner):
    def _record(self, scoped, job_id, status, attempts, errors, result):
        rec = super()._record(scoped, job_id, status, attempts, errors, result)
        self.unrecorded.clear()
        return rec

    def run(self, job):
        r = super().run(job)
        if 'recorded' in r:
            r['recorded'] = True
        return r


class RetriesPermanentErrors(JobRunner):
    def run(self, job):
        orig = self.handler
        def wrapped(scoped, payload):
            try:
                return orig(scoped, payload)
            except TransientError:
                raise
            except Exception as e:
                raise TransientError(str(e))
        self.handler = wrapped
        try:
            return super().run(job)
        finally:
            self.handler = orig


class NoBackoff(JobRunner):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.sleep = lambda s: None


class RequeueAnything(JobRunner):
    def requeue(self, job):
        scoped, _ = tenancy.bind_job(self.provider, self.store, self.audit, job)
        return self.run(job)


class SizeOffByOne(InMemoryFileStore):
    def _meta(self, t, fid):
        m = super()._meta(t, fid)
        return FileMeta(m.tenant_id, m.file_id, m.name, m.sha256, m.size + 1, m.media_type, m.scan_status)


class ListShowsAllTenants(InMemoryFileStore):
    def list(self, ctx):
        _need(self.provider, ctx)
        return tuple(self._meta(t, f) for (t, f) in sorted(self._d, key=lambda k: k[1]))


class GivesUpTooEarly(JobRunner):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.max_attempts = min(self.max_attempts, 2)


class NoAuditEvents(JobRunner):
    def run(self, job):
        orig = tenancy.ScopedStore.log
        tenancy.ScopedStore.log = lambda self, *a, **k: None
        try:
            return super().run(job)
        finally:
            tenancy.ScopedStore.log = orig


class ForgetsSuccess(JobRunner):
    def _record(self, scoped, job_id, status, attempts, errors, result):
        if status == 'succeeded':
            return None
        return super()._record(scoped, job_id, status, attempts, errors, result)


FAULTS = {
    'FF-01': ('an unscanned file can be read', 'files', file_env(ReadsUnscanned), ['FS-06']),
    'FF-02': ('anyone, even the uploader, can record a scan verdict', 'files', file_env(AnyoneCanScan), ['FS-07']),
    'FF-03': ('an infected verdict can be overwritten with clean', 'files', file_env(InfectedCanBeCleaned), ['FS-07']),
    'FF-04': ('file ids are looked up across tenants', 'files', file_env(GlobalFileIds), ['FS-04']),
    'FF-05': ('a clean verdict for the same bytes leaks to every tenant', 'files', file_env(ScanVerdictSharedAcrossTenants), ['FS-04']),
    'FF-06': ('a later upload under the same name replaces the earlier file', 'files', file_env(OverwriteByName), ['FS-02']),
    'FF-07': ('stored bytes are not re-checked against their hash on read', 'files', file_env(NoIntegrityCheck), ['FS-08']),
    'FF-08': ('the stored buffer is aliased to the caller and returned mutable', 'files', file_env(AliasedBuffer), ['FS-03']),
    'FF-09': ('list works without a context', 'files', file_env(NoAuthOnList), ['FS-05']),
    'FF-10': ('path separators and control characters accepted in names', 'files', file_env(UnsafeNames), ['FS-09']),
    'FF-11': ('a person holding the scanner role may record verdicts', 'files', file_env(ScannerRoleOnly), ['FS-07']),
    'FF-12': ('the reported size is wrong', 'files', file_env(SizeOffByOne), ['FS-01']),
    'FF-13': ('list shows other tenants\' files', 'files', file_env(ListShowsAllTenants), ['FS-10']),
    'JF-01': ('retries are not bounded by max_attempts', 'jobs', job_env(RetriesTooLong), ['JR-03']),
    'JF-02': ('authenticates once and keeps the first context for later attempts', 'jobs', job_env(AuthenticatesOnce), ['JR-07']),
    'JF-03': ('re-runs a job that already succeeded', 'jobs', job_env(RerunsSucceeded), ['JR-02']),
    'JF-04': ('dead-lettered jobs are not recorded', 'jobs', job_env(NoDeadLetterRecord), ['JR-03', 'JR-06']),
    'JF-05': ('re-runs a dead-lettered job on resubmission', 'jobs', job_env(AutoRequeue), ['JR-11']),
    'JF-06': ('does not screen tenant claims in the message payload', 'jobs', job_env(TrustsMessage), ['JR-10']),
    'JF-07': ('results are remembered by job id across tenants', 'jobs', job_env(GlobalJobTable), ['JR-09']),
    'JF-08': ('the stored result object is shared with the caller', 'jobs', job_env(SharesResultObject), ['JR-14']),
    'JF-09': ('an unrecordable failure is hidden', 'jobs', job_env(SwallowsUnrecorded), ['JR-08']),
    'JF-10': ('permanent errors are retried', 'jobs', job_env(RetriesPermanentErrors), ['JR-06']),
    'JF-11': ('no wait between retries', 'jobs', job_env(NoBackoff), ['JR-04']),
    'JF-12': ('requeue works for any job, even unknown or succeeded', 'jobs', job_env(RequeueAnything), ['JR-12']),
    'JF-13': ('gives up one attempt early', 'jobs', job_env(GivesUpTooEarly), ['JR-05']),
    'JF-14': ('writes no audit events', 'jobs', job_env(NoAuditEvents), ['JR-13']),
    'JF-15': ('success is not recorded in the job table', 'jobs', job_env(ForgetsSuccess), ['JR-01', 'JR-02']),
}
