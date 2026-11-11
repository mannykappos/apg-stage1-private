#!/usr/bin/env python3
"""Reproduces the failure the independent audit of APG-M9.3 found (F-63) in a few lines each:  python3 -I tools/probe_m93_clock_failure.py
On APG-M9.3 a clock whose now() raises makes present, request_approval and check_for_execution raise to the caller (no refusal, no audit event); a clock that fails on its second read can stop an approval half way; an expiry or actor kind that cannot be read
raises too.  Nothing was approved by any of it (the audit did not claim a bypass): the failure handling was wrong.  On APG-M9.4 each is the ordinary refusal, audited best-effort, and nothing is approved.
Exit 0 only if all are corrected; exit 1 and the words DEFECT PRESENT otherwise.  It uses the in-memory test world of the unit tests and changes nothing outside it."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_api_approval_boundary import Grants, AB, FD, TEXT1
from tests.test_api_m93_corrections import Expiring
from tests.test_api_m94_corrections import RaisingClock, FailsAfter, WithCtx, broken_ctx, NOW, FUTURE
from tests.test_det_findings import breach, first
from tests.test_det_proposal_binding import proposed

bad = []


def world():
    m = breach()
    fid, _ = first(m)
    proposed(m, fid, TEXT1)
    return m, fid, Grants({('zero_one', 'abby', 'PRJ-001'): ('view', 'approve')})


def req(m, fid, rid):
    tok = FD.approval_token(FD.get(m.svc, fid))
    return {'request_id': rid, 'finding_id': fid, 'version': tok['version'], 'digest': tok['digest'], 'proposal': tok['proposal'], 'rationale': 'I approve what I was shown'}


def events(m):
    return len([e for e in m.w.audit.read(m.s.ctx) if e.event_type.startswith('approval_request.')])


def verdict(label, corrected, what):
    print(f'{label:<72} -> ' + ('corrected' if corrected else 'DEFECT PRESENT: ' + what))
    if not corrected:
        bad.append(label)


def attempt(fn):
    try:
        return fn(), None
    except Exception as e:                                   # the probe reports what escaped; it does not hide it
        return None, f'{type(e).__name__}: {e}'


def check(label, call, expect, m, fid, n0):
    out, err = attempt(call)
    ok = err is None and expect(out) and FD.get(m.svc, fid)['status'] == 'action_proposed' and events(m) == n0 + 1
    verdict(label, ok, f"escaped {err}" if err else f"answer {out}; the finding is {FD.get(m.svc, fid)['status']}; {events(m) - n0} new audit events")


m, fid, sc = world(); n0 = events(m)
check('F-63 present, clock.now() raises RuntimeError', lambda: AB.present(m.approver, sc, RaisingClock(RuntimeError('clock unavailable')), fid), lambda r: (r['status'], r['code']) == ('refused', 'NOT_ALLOWED'), m, fid, n0)
m, fid, sc = world(); n0 = events(m)
check('F-63 request_approval, clock.now() raises RuntimeError', lambda: AB.request_approval(m.approver, sc, RaisingClock(RuntimeError('clock unavailable')), req(m, fid, 'R-2')), lambda r: (r['status'], r['code']) == ('refused', 'SESSION_EXPIRED'), m, fid, n0)
m, fid, sc = world(); n0 = events(m); tok = FD.approval_token(FD.get(m.svc, fid))
check('F-63 check_for_execution, clock.now() raises RuntimeError', lambda: AB.check_for_execution(m.approver, sc, RaisingClock(RuntimeError('clock unavailable')), fid, tok['version'], tok['digest'], tok['proposal']), lambda r: r == {'valid': False, 'code': 'NOT_ALLOWED'}, m, fid, n0)

m, fid, sc = world()
c = FailsAfter(NOW, 1)
out, err = attempt(lambda: AB.request_approval(Expiring(m.approver, FUTURE), sc, c, req(m, fid, 'R-4')))
st = FD.get(m.svc, fid)['status']
verdict('F-63 a clock that fails after its first read does not halve an approval', err is None and out['status'] == 'approved' and st == 'action_approved', f"escaped {err}; the finding is {st}" if err else f"answer {out['status']} {out['code']}; the finding is {st}")

m, fid, sc = world(); n0 = events(m)
check('F-63 an expiry that cannot be read ends the session', lambda: AB.request_approval(WithCtx(m.approver, broken_ctx(m.approver.ctx, 'expires_at', RuntimeError('x'))), sc, m.clock, req(m, fid, 'R-5')), lambda r: (r['status'], r['code']) == ('refused', 'SESSION_EXPIRED'), m, fid, n0)

m, fid, sc = world()
out, err = attempt(lambda: AB.request_approval(m.approver, sc, m.clock, req(m, fid, 'R-6')))
verdict('a working clock still approves', err is None and out['status'] == 'approved', f"escaped {err}" if err else f"answer {out['status']} {out['code']}")
if bad:
    print('DEFECT PRESENT in', len(bad), 'of 6:', bad)
    sys.exit(1)
print('THE CLOCK FAILURE IS HANDLED SAFELY (builder test world; no independent review)')
