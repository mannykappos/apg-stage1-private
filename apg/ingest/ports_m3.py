"""PORTS added in M3 (handoff register EDR-04 JobRunnerPort, EDR-07 FileStorePort).  Amir implements these on the real Engine; the contract suites in
apg/ingest/contracts_m3.py define what an implementation must guarantee, including failure behaviour.  The in-memory references are test doubles, not a design.

FileStorePort rules
  * the tenant is taken only from a verified AuthenticatedContext; another tenant's file is indistinguishable from a missing one
  * stored bytes never change; a file is identified by the tenant plus the SHA-256 of its bytes
  * a file is NOT readable by ordinary callers until a scanner has recorded a 'clean' verdict; 'infected' is terminal
  * only a service identity holding the role 'file_scanner' may read an unscanned file or record a verdict
  * every read re-checks the hash, so silent corruption is refused, not parsed
JobRunnerPort rules (the reference is apg.ingest.jobs.JobRunner)
  * a worker never inherits a tenant from a message: every attempt re-authenticates from the credentials
  * retries are bounded; permanent errors are dead-lettered at once; a succeeded job id is replayed, never re-run; requeue is an explicit act
"""
from dataclasses import dataclass
from ..ports import PortError

SCANNER_ROLE = 'file_scanner'
CLEAN, INFECTED, UNSCANNED = 'clean', 'infected', 'unscanned'


class FileNotFound(PortError):
    """No such file in this tenant (also what another tenant's file looks like)."""


class ScanRequired(PortError):
    """The file has not been scanned yet, so it may not be read or parsed."""


class ScanInfected(PortError):
    """The scanner found the file unsafe."""


class IntegrityError(PortError):
    """Stored bytes no longer match the recorded hash."""


class NotPermitted(PortError):
    """The caller's identity may not do this."""


@dataclass(frozen=True)
class FileMeta:
    tenant_id: str
    file_id: str
    name: str
    sha256: str
    size: int
    media_type: str
    scan_status: str


class FileStorePort:
    max_bytes = 0

    def put(self, ctx, name, data, media_type=''):
        """Store immutable bytes.  -> FileMeta (scan_status 'unscanned' for a new file).  The same bytes again return the existing file.  Refuses non-bytes, over-size
        data and unsafe names (control characters, path separators, '..')."""
        raise NotImplementedError

    def meta(self, ctx, file_id):
        """-> FileMeta or None."""
        raise NotImplementedError

    def list(self, ctx):
        """-> tuple of this tenant's FileMeta ordered by file_id."""
        raise NotImplementedError

    def read(self, ctx, file_id):
        """-> bytes.  FileNotFound / ScanRequired / ScanInfected / IntegrityError otherwise."""
        raise NotImplementedError

    def read_for_scan(self, ctx, file_id):
        """-> bytes of a file in any scan state.  Only a service identity with the role file_scanner."""
        raise NotImplementedError

    def record_scan(self, ctx, file_id, verdict):
        """Only a service identity with the role file_scanner.  verdict 'clean' or 'infected'.  'infected' is terminal.  -> FileMeta."""
        raise NotImplementedError

    def _contract_corrupt(self, tenant_id, file_id):
        """Contract-test seam: damage the stored bytes directly."""
        raise NotImplementedError
