"""Factories that build the M3 contract environments around the in-memory reference implementations."""
from ..reference_impl import FakeClock, InMemoryAuditLog, InMemoryRecordStore, StaticContextProvider
from .contracts_m3 import FileEnv, JobEnv
from .filestore import InMemoryFileStore
from .jobs import JobRunner


def file_env(files_cls=InMemoryFileStore, provider_cls=StaticContextProvider):
    def factory():
        c = FakeClock(); p = provider_cls(c)
        return FileEnv(p, files_cls(p), c.advance)
    return factory


def job_env(runner_cls=JobRunner):
    def factory():
        c = FakeClock(); p = StaticContextProvider(c); st = InMemoryRecordStore(p); au = InMemoryAuditLog(p, c)
        sleeps = []
        def make(handler, max_attempts=3):
            return runner_cls(p, st, au, handler, max_attempts=max_attempts, backoff_seconds=(1, 2, 4), sleep=sleeps.append)
        return JobEnv(p, st, au, make, c.advance, sleeps)
    return factory
