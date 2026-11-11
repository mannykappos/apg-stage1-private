"""Reference in-memory FileStorePort (TEST DOUBLE) and the scan-gated import path.  EDR-07."""
import hashlib, re
from . import pipeline
from .ports_m3 import (CLEAN, INFECTED, SCANNER_ROLE, UNSCANNED, FileMeta, FileNotFound, FileStorePort, IntegrityError, NotPermitted, ScanInfected, ScanRequired)
from ..ports import PayloadInvalid
from .. import ports as _p
from ..reference_impl import _need

_NAME_BAD = re.compile(r'[\x00-\x1f\x7f/\\]')


def check_name(name):
    if not isinstance(name, str) or not name or len(name) > 200 or _NAME_BAD.search(name) or '..' in name:
        raise PayloadInvalid('file name must be 1-200 characters with no control characters, path separators or ..')


def _is_scanner(ctx):
    return ctx.actor_kind == 'service' and SCANNER_ROLE in ctx.roles


class InMemoryFileStore(FileStorePort):
    def __init__(self, provider, max_bytes=5_000_000):
        self.provider, self.max_bytes, self._d = provider, max_bytes, {}

    @staticmethod
    def _id(sha):
        return 'F-' + sha[:32]

    def _meta(self, t, fid):
        r = self._d[(t, fid)]
        return FileMeta(t, fid, r['name'], r['sha'], r['size'], r['media'], r['scan'])

    def put(self, ctx, name, data, media_type=''):
        _need(self.provider, ctx)
        check_name(name)
        if not isinstance(data, (bytes, bytearray)):
            raise PayloadInvalid('data must be bytes')
        if len(data) > self.max_bytes:
            raise PayloadInvalid('file larger than the store allows')
        if not isinstance(media_type, str):
            raise PayloadInvalid('media_type must be a string')
        data = bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        fid = self._id(sha)
        if (ctx.tenant_id, fid) not in self._d:
            self._d[(ctx.tenant_id, fid)] = {'name': name, 'sha': sha, 'size': len(data), 'media': media_type, 'scan': UNSCANNED, 'data': data}
        return self._meta(ctx.tenant_id, fid)

    def meta(self, ctx, file_id):
        _need(self.provider, ctx)
        return self._meta(ctx.tenant_id, file_id) if (ctx.tenant_id, file_id) in self._d else None

    def list(self, ctx):
        _need(self.provider, ctx)
        return tuple(self._meta(t, f) for (t, f) in sorted(self._d, key=lambda k: k[1]) if t == ctx.tenant_id)

    def _bytes(self, ctx, file_id):
        r = self._d.get((ctx.tenant_id, file_id))
        if r is None:
            raise FileNotFound(file_id)
        if hashlib.sha256(r['data']).hexdigest() != r['sha']:
            raise IntegrityError(file_id)
        return r

    def read(self, ctx, file_id):
        _need(self.provider, ctx)
        r = self._bytes(ctx, file_id)
        if r['scan'] == INFECTED:
            raise ScanInfected(file_id)
        if r['scan'] != CLEAN:
            raise ScanRequired(file_id)
        return bytes(r['data'])

    def read_for_scan(self, ctx, file_id):
        _need(self.provider, ctx)
        if not _is_scanner(ctx):
            raise NotPermitted('only the file scanner service may read an unscanned file')
        return bytes(self._bytes(ctx, file_id)['data'])

    def record_scan(self, ctx, file_id, verdict):
        _need(self.provider, ctx)
        if not _is_scanner(ctx):
            raise NotPermitted('only the file scanner service may record a scan verdict')
        if verdict not in (CLEAN, INFECTED):
            raise PayloadInvalid('verdict must be clean or infected')
        r = self._d.get((ctx.tenant_id, file_id))
        if r is None:
            raise FileNotFound(file_id)
        if r['scan'] == INFECTED and verdict == CLEAN:
            raise NotPermitted('an infected verdict is terminal')
        r['scan'] = verdict
        return self._meta(ctx.tenant_id, file_id)

    def _contract_corrupt(self, tenant_id, file_id):
        r = self._d[(tenant_id, file_id)]
        b = bytearray(r['data'] or b'\x00')
        b[0] ^= 0xFF
        r['data'] = bytes(b)


def ingest_stored_file(scoped, files, clock, template, file_id, source, policy=None, revision_field=None):
    """Parse and ingest a file held in the file store.  Nothing is parsed unless the scanner has recorded 'clean' and the bytes still match their hash.
    -> the ingest receipt (plus file_id), or {'status': 'not_ingested', 'code': ...} with nothing written to the record store."""
    ctx = scoped.ctx

    def refuse(code, detail=''):
        scoped.log('ingest.file_not_ingested', file_id if isinstance(file_id, str) and file_id else 'file', code, reason=detail)
        return {'status': 'not_ingested', 'code': code, 'file_id': file_id}
    try:
        meta = files.meta(ctx, file_id)
        if meta is None:
            return refuse('FILE_NOT_FOUND')
        data = files.read(ctx, file_id)
    except ScanRequired:
        return refuse('SCAN_REQUIRED', 'the file has not been scanned')
    except ScanInfected:
        return refuse('SCAN_INFECTED', 'the scanner marked the file unsafe')
    except IntegrityError:
        return refuse('FILE_INTEGRITY', 'stored bytes do not match the recorded hash')
    except FileNotFound:
        return refuse('FILE_NOT_FOUND')
    if hashlib.sha256(data).hexdigest() != meta.sha256:
        return refuse('FILE_INTEGRITY', 'returned bytes do not match the recorded hash')
    rec = pipeline.ingest_file(scoped, clock, template, data, source, meta.name, policy, revision_field)
    rec = dict(rec, file_id=file_id)
    scoped.log('ingest.stored_file', file_id, rec.get('status', 'ingested'), reason=meta.sha256, detail={'sha256': meta.sha256, 'name': meta.name})
    return rec
