"""Contract for the guards in RecordStorePort.atomic (APG-M7.3, EDR-35).  Kept apart from the M2 record-store suite: it registers nothing in framework.CASES, so the M2 suite and its
deliberately faulty implementations are unchanged.  Run it with run_guard_suite(factory); every case gets a fresh environment.
What an Engine store must guarantee for APG's consequential acts (submission, approval, start of work) to commit only on the sources they were checked against:
a guard holds a record at a revision (0 = absent) or a whole query at an exact set of (key, revision); it writes nothing; if any guard fails nothing in the batch is applied; guards see the state
before the batch's own writes; guards are tenant-scoped; malformed guards are refused; and the batch is indivisible with respect to every other call, from any number of concurrent callers."""
import sys, threading
from .. import ports
from .framework import check, raises, session

G = ports.Guard
GUARD_CASES = []


def gcase(cid, text):
    def deco(fn):
        GUARD_CASES.append((cid, text, fn))
        return fn
    return deco


def two(env):
    return session(env, 'tokA', 'tenant-A', 'alice'), session(env, 'tokB', 'tenant-B', 'bob')


@gcase('RG-01', 'a revision guard holds at the exact latest revision, and 0 holds only for an absent record')
def rg01(env):
    a, _ = two(env)
    env.store.put(a, 'finding', 'F1', {'v': 1})
    check(env.store.atomic(a, [G('revision', 'finding', 'F1', 1), G('revision', 'finding', 'F2', 0)]) == (), 'a guard-only batch returns nothing')
    raises(ports.ConflictError, lambda: env.store.atomic(a, [G('revision', 'finding', 'F1', 2)]), 'wrong revision')
    raises(ports.ConflictError, lambda: env.store.atomic(a, [G('revision', 'finding', 'F1', 0)]), 'existing record held as absent')
    raises(ports.ConflictError, lambda: env.store.atomic(a, [G('revision', 'finding', 'F2', 1)]), 'absent record held at a revision')


@gcase('RG-02', 'a query guard holds only for exactly the same set: an added, changed or missing record fails it')
def rg02(env):
    a, _ = two(env)
    env.store.put(a, 'finding', 'F1', {'p': 'X'}); env.store.put(a, 'finding', 'F2', {'p': 'Y'})
    held = (('F1', 1), ('F2', 1))
    env.store.atomic(a, [G('query', 'finding', None, held)])
    env.store.atomic(a, [G('query', 'finding', {}, tuple(reversed(held)))])
    raises(ports.ConflictError, lambda: env.store.atomic(a, [G('query', 'finding', None, held[:1])]), 'a record missing from the guard')
    raises(ports.ConflictError, lambda: env.store.atomic(a, [G('query', 'finding', None, held + (('F3', 1),))]), 'a record that does not exist')
    env.store.put(a, 'finding', 'F3', {'p': 'X'})
    raises(ports.ConflictError, lambda: env.store.atomic(a, [G('query', 'finding', None, held)]), 'a record was added')
    env.store.put(a, 'finding', 'F1', {'p': 'X', 'v': 2})
    raises(ports.ConflictError, lambda: env.store.atomic(a, [G('query', 'finding', None, held + (('F3', 1),))]), 'a record changed')


@gcase('RG-03', 'a query guard with a filter covers exactly the records the filter returns')
def rg03(env):
    a, _ = two(env)
    env.store.put(a, 'finding', 'F1', {'p': 'X'}); env.store.put(a, 'finding', 'F2', {'p': 'Y'})
    env.store.atomic(a, [G('query', 'finding', {'p': 'X'}, (('F1', 1),))])
    env.store.put(a, 'finding', 'F2', {'p': 'Y', 'v': 2})                         # outside the filter: irrelevant
    env.store.atomic(a, [G('query', 'finding', {'p': 'X'}, (('F1', 1),))])
    env.store.put(a, 'finding', 'F4', {'p': 'X'})                                 # a new record inside the filter
    raises(ports.ConflictError, lambda: env.store.atomic(a, [G('query', 'finding', {'p': 'X'}, (('F1', 1),))]), 'a new matching record')


@gcase('RG-04', 'if any guard fails, none of the batch\'s writes is applied')
def rg04(env):
    a, _ = two(env)
    env.store.put(a, 'finding', 'F1', {'v': 1})
    raises(ports.ConflictError, lambda: env.store.atomic(a, [('rec', 'R1', {'s': 'submitted'}, 0), G('revision', 'finding', 'F1', 7), ('rec', 'R2', {'s': 'x'}, None)]), 'guard failed')
    check(env.store.get(a, 'rec', 'R1') is None and env.store.get(a, 'rec', 'R2') is None, 'a write was applied although a guard failed')
    out = env.store.atomic(a, [('rec', 'R1', {'s': 'submitted'}, 0), G('revision', 'finding', 'F1', 1)])
    check(len(out) == 1 and out[0].key == 'R1' and out[0].revision == 1, 'guards return nothing; writes return their records in order')


@gcase('RG-05', 'guards see the state before the batch\'s own writes')
def rg05(env):
    a, _ = two(env)
    env.store.atomic(a, [('finding', 'F1', {'v': 1}, 0), G('revision', 'finding', 'F1', 0), G('query', 'finding', None, ())])
    check(env.store.get(a, 'finding', 'F1').revision == 1, 'the write was not applied')


@gcase('RG-06', 'guards are tenant-scoped: records of another tenant are invisible to them')
def rg06(env):
    a, b = two(env)
    env.store.put(b, 'finding', 'F1', {'v': 1})
    env.store.atomic(a, [G('revision', 'finding', 'F1', 0), G('query', 'finding', None, ())])
    raises(ports.ConflictError, lambda: env.store.atomic(a, [G('revision', 'finding', 'F1', 1)]), 'another tenant\'s record seen')


@gcase('RG-07', 'a malformed guard is refused and nothing is applied')
def rg07(env):
    a, _ = two(env)
    env.store.put(a, 'finding', 'F1', {'v': 1})
    bad = [G('maybe', 'finding', 'F1', 1), G('maybe', 'finding', None, ()), G('revision', 'finding', 'F1', -1), G('revision', 'finding', 'F1', True), G('revision', 'finding', 'F1', '1'), G('revision', '', 'F1', 1),
           G('query', 'finding', 'p=X', ()), G('query', 'finding', None, (('F1', 1), ('F1', 2))), G('query', 'finding', None, (('F1',),)), G('query', 'finding', None, (('F1', 0),)),
           G('query', 'finding', None, 5)]
    for g in bad:
        raises(ports.PayloadInvalid, lambda g=g: env.store.atomic(a, [('rec', 'R1', {'s': 1}, None), g]), 'malformed guard %r' % (g,))
    check(env.store.get(a, 'rec', 'R1') is None, 'a write was applied with a malformed guard')


@gcase('RG-08', 'concurrent callers: "add a record only if the query is unchanged" never lets two callers both succeed on the same state')
def rg08(env):
    a, _ = two(env)
    wins, errors = [], []

    def worker(n):
        for i in range(30):
            try:
                recs = env.store.query(a, 'slot')
                held = tuple((r.key, r.revision) for r in recs)
                env.store.atomic(a, [G('query', 'slot', None, held), ('slot', 'S-%d-%02d' % (n, i), {'saw': len(recs)}, 0)])     # each caller writes its own key
                wins.append(len(recs))
            except ports.ConflictError:
                pass
            except Exception as e:                                       # pragma: no cover - reported as a failure
                errors.append(repr(e))
    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)                                          # switch between threads as often as the interpreter can, so that interleavings actually occur
    try:
        ts = [threading.Thread(target=worker, args=(n,)) for n in range(6)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
    finally:
        sys.setswitchinterval(old)
    recs = env.store.query(a, 'slot')
    check(not errors, 'errors: %r' % errors[:3])
    check(sorted(wins) == list(range(len(recs))), 'two callers succeeded on the same state, or a success was lost: %r' % sorted(wins)[:12])
    check(sorted(r.payload['saw'] for r in recs) == list(range(len(recs))), 'two stored records were written on the same state')


def run_guard_suite(factory):
    """-> list of (case_id, description, passed, detail)."""
    out = []
    for cid, text, fn in GUARD_CASES:
        try:
            fn(factory())
            out.append((cid, text, True, ''))
        except Exception as e:
            out.append((cid, text, False, f'{type(e).__name__}: {e}'))
    return out
