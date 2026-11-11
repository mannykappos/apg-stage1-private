"""Contract for the revision history of RecordStorePort (APG-F67.3, EDR-41).  Kept apart from the M2 record-store suite: it registers nothing in framework.CASES, so the M2 suite
and its deliberately faulty implementations are unchanged.  Run it with run_history_suite(factory); every case gets a fresh environment.
What an Engine store must guarantee for a policy approval to be judged (apg/policy_approval.py: added_at, holds; I-132): revisions are numbered 1..n in the order written; a
revision, once written, reads back exactly the same for ever, and nothing a caller does with what it reads can change it; a revision outside 1..n reads as nothing; writing a
payload identical to the latest appends nothing, and any other payload appends exactly one revision; history and get agree; all of it per tenant.  A run pins a revision, and
replay reads that exact revision (apg/repro.py) - which these guarantees make reliable."""
from .. import ports
from .framework import check, session

HISTORY_CASES = []


def hcase(cid, text):
    def deco(fn):
        HISTORY_CASES.append((cid, text, fn))
        return fn
    return deco


def _a(env):
    return session(env, 'tokA', 'tenant-A', 'alice')


@hcase('RH-01', 'revisions are numbered 1..n in the order written; put returns the revision it wrote; history lists them oldest first')
def rh01(env):
    a = _a(env)
    got = [env.store.put(a, 'policy', 'P1', {'v': i}).revision for i in range(1, 5)]
    check(got == [1, 2, 3, 4], 'put returned revisions %r' % got)
    h = env.store.history(a, 'policy', 'P1')
    check([r.revision for r in h] == [1, 2, 3, 4] and [r.payload['v'] for r in h] == [1, 2, 3, 4], 'history %r' % [(r.revision, r.payload) for r in h])


@hcase('RH-02', 'a past revision reads back exactly as written, payload and hash, after later writes')
def rh02(env):
    a = _a(env)
    first = env.store.put(a, 'policy', 'P1', {'v': 1, 'approvals': [{'approver': 'olive'}]})
    for i in range(2, 6):
        env.store.put(a, 'policy', 'P1', {'v': i, 'approvals': []})
    again = env.store.get(a, 'policy', 'P1', 1)
    check(again is not None and again.payload == {'v': 1, 'approvals': [{'approver': 'olive'}]} and again.payload_hash == first.payload_hash, 'revision 1 changed: %r' % (again,))


@hcase('RH-03', 'a revision outside 1..n reads as nothing: 0, -1, n+1, a boolean, a text or a fraction')
def rh03(env):
    a = _a(env)
    for i in range(3):
        env.store.put(a, 'policy', 'P1', {'v': i})
    for rev in (0, -1, -3, 4, 99, True, False, '1', 1.0):
        check(env.store.get(a, 'policy', 'P1', rev) is None, 'revision %r read as %r' % (rev, env.store.get(a, 'policy', 'P1', rev)))
    check(env.store.get(a, 'policy', 'NOPE', 1) is None, 'a missing record read as something')


@hcase('RH-04', 'an identical payload appends nothing; any other payload appends exactly one revision')
def rh04(env):
    a = _a(env)
    env.store.put(a, 'policy', 'P1', {'v': 1})
    same = env.store.put(a, 'policy', 'P1', {'v': 1})
    check(same.revision == 1 and len(env.store.history(a, 'policy', 'P1')) == 1, 'an identical payload appended a revision')
    other = env.store.put(a, 'policy', 'P1', {'v': 1, 'x': 0})
    check(other.revision == 2 and len(env.store.history(a, 'policy', 'P1')) == 2, 'a changed payload did not append exactly one revision')


@hcase('RH-05', 'history and get(revision) agree for every revision, and another tenant sees none of it')
def rh05(env):
    a = _a(env)
    b = session(env, 'tokB', 'tenant-B', 'bob')
    for i in range(4):
        env.store.put(a, 'policy', 'P1', {'v': i})
    for r in env.store.history(a, 'policy', 'P1'):
        g = env.store.get(a, 'policy', 'P1', r.revision)
        check(g is not None and (g.revision, g.payload, g.payload_hash) == (r.revision, r.payload, r.payload_hash), 'history and get disagree at %d' % r.revision)
    check(env.store.get(b, 'policy', 'P1', 1) is None and env.store.history(b, 'policy', 'P1') == (), 'another tenant read the history')


@hcase('RH-06', 'nothing a caller does with what it reads or writes changes a stored revision')
def rh06(env):
    a = _a(env)
    payload = {'v': 1, 'approvals': [{'approver': 'olive'}]}
    w = env.store.put(a, 'policy', 'P1', payload)
    payload['approvals'].append({'approver': 'mallory'})
    w.payload['approvals'].append({'approver': 'mallory'})
    env.store.get(a, 'policy', 'P1', 1).payload['approvals'].append({'approver': 'mallory'})
    env.store.history(a, 'policy', 'P1')[0].payload['approvals'].append({'approver': 'mallory'})
    check(env.store.get(a, 'policy', 'P1', 1).payload == {'v': 1, 'approvals': [{'approver': 'olive'}]}, 'a stored revision was changed through an object a caller held')


def run_history_suite(factory):
    """-> list of (case_id, description, passed, detail)."""
    out = []
    for cid, text, fn in HISTORY_CASES:
        try:
            fn(factory())
            out.append((cid, text, True, ''))
        except Exception as e:
            out.append((cid, text, False, f'{type(e).__name__}: {e}'))
    return out
