"""Bounded retries, a dead-letter list and replay that never repeats an effect.  Blueprint: Section 04 section 15 (bounded retry/backoff and defined terminal handling,
no infinite retries and no silent data loss; replay idempotent), PG-DI-AC-08, 14, 17.

A job is {'job_id', 'credentials', 'payload'}.  EVERY attempt re-authenticates from the credentials (a worker never inherits a tenant from the message): expired,
revoked or unknown credentials are a permanent failure.  The handler gets (scoped_store, clean_payload).
  * TransientError  -> retried up to max_attempts with growing waits (the wait is the injected `sleep`, so tests need no real time)
  * any other error -> permanent: dead-lettered at once, with the error kept
  * after max_attempts transient failures -> dead-lettered; nothing retries forever
  * a job id that already succeeded is NOT run again: the stored result comes back (replay)
  * a dead-lettered job is run again only by an explicit `requeue`
The job record lives in the tenant's own store, so one tenant can neither see nor replay another tenant's jobs."""
from .. import canon, tenancy
from ..ports import ConflictError, PortError


class TransientError(Exception):
    pass


class JobRunner:
    def __init__(self, provider, store, audit, handler, max_attempts=3, backoff_seconds=(1, 2, 4), sleep=lambda s: None):
        if not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError('max_attempts must be at least 1')
        self.provider, self.store, self.audit, self.handler = provider, store, audit, handler
        self.max_attempts, self.backoff, self.sleep = max_attempts, tuple(backoff_seconds), sleep
        self.unrecorded = []        # terminal failures that could not be written to the tenant's store (for example because the credentials were revoked mid-job)

    def _record(self, scoped, job_id, status, attempts, errors, result):
        """Write the job record.  If the tenant store refuses (the submitting credentials were revoked), the failure is NOT lost: it is kept in `unrecorded` and
        reported.  A real worker needs its own service identity to record such failures (handoff register EDR-04)."""
        try:
            cur = scoped.get('job', job_id)
            payload = {'job_id': job_id, 'status': status, 'attempts': attempts, 'errors': errors, 'result': result}
            return scoped.put('job', job_id, payload, expected_revision=cur.revision if cur else 0)
        except PortError as e:
            self.unrecorded.append({'job_id': job_id, 'status': status, 'attempts': attempts, 'errors': list(errors), 'why_unrecorded': type(e).__name__})
            return None

    def run(self, job):
        if not isinstance(job, dict) or not isinstance(job.get('job_id'), str) or not job['job_id']:
            raise ValueError('a job needs a job_id')
        jid, errors, attempts = job['job_id'], [], 0
        scoped = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                scoped, clean = tenancy.bind_job(self.provider, self.store, self.audit, job)       # re-authenticated on EVERY attempt
            except PortError as e:
                if scoped is None:                                                                  # no tenant could be established: nothing to record against
                    return {'job_id': jid, 'status': 'refused', 'reason': type(e).__name__}
                rec = self._record(scoped, jid, 'dead_letter', attempts, errors + [f'{type(e).__name__}: {e}'], None)
                return {'job_id': jid, 'status': 'dead_letter', 'attempts': attempts, 'recorded': rec is not None}
            prior = scoped.get('job', jid)
            if prior is not None and prior.payload['status'] == 'succeeded':
                scoped.log('job.replay', jid, 'no_change', reason='already succeeded')
                return {'job_id': jid, 'status': 'succeeded', 'attempts': prior.payload['attempts'], 'result': prior.payload['result'], 'replay': True}
            if prior is not None and prior.payload['status'] == 'dead_letter' and attempt == 1:
                scoped.log('job.refused', jid, 'dead_letter', reason='requeue is explicit')
                return {'job_id': jid, 'status': 'dead_letter', 'attempts': prior.payload['attempts'], 'replay': True}
            attempts = attempt + (prior.payload['attempts'] if prior is not None and prior.payload['status'] == 'queued_again' else 0)
            try:
                result = self.handler(scoped, clean)
                result = canon.deep_copy(result) if result is not None else None
                rec = self._record(scoped, jid, 'succeeded', attempts, errors, result)
                if rec is not None:
                    result = rec.payload['result']                  # what was stored (tenant-like keys are stripped), so a replay returns exactly what the first run returned
                try:
                    scoped.log('job.succeeded', jid, 'ok', reason=f'attempt {attempt}')
                except PortError:
                    pass
                return {'job_id': jid, 'status': 'succeeded', 'attempts': attempts, 'result': result, 'replay': False, 'recorded': rec is not None}
            except TransientError as e:
                errors.append(f'attempt {attempt}: {e}')
                if attempt < self.max_attempts:
                    self.sleep(self.backoff[min(attempt - 1, len(self.backoff) - 1)] if self.backoff else 0)
                    continue
            except ConflictError as e:
                errors.append(f'attempt {attempt}: conflict {e}')
                if attempt < self.max_attempts:
                    continue
            except Exception as e:                                                                  # permanent
                self._record(scoped, jid, 'dead_letter', attempts, errors + [f'{type(e).__name__}: {e}'], None)
                scoped.log('job.dead_letter', jid, 'permanent', reason=type(e).__name__)
                return {'job_id': jid, 'status': 'dead_letter', 'attempts': attempts}
        self._record(scoped, jid, 'dead_letter', attempts, errors, None)
        scoped.log('job.dead_letter', jid, 'attempts_exhausted', reason=f'{self.max_attempts} attempts')
        return {'job_id': jid, 'status': 'dead_letter', 'attempts': attempts}

    def requeue(self, job):
        """An explicit decision to run a dead-lettered job again (the caller must already be authenticated as a person with the right to do so)."""
        scoped, _ = tenancy.bind_job(self.provider, self.store, self.audit, job)
        prior = scoped.get('job', job['job_id'])
        if prior is None or prior.payload['status'] != 'dead_letter':
            raise ValueError('only a dead-lettered job can be requeued')
        p = dict(canon.deep_copy(prior.payload), status='queued_again')
        scoped.put('job', job['job_id'], p, expected_revision=prior.revision)
        scoped.log('job.requeued', job['job_id'], 'queued_again', reason=scoped.ctx.user_id)
        return self.run(job)
