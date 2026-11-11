#!/usr/bin/env python3
"""A short, readable demonstration of the M7 guarantees on a small synthetic world (each line is one guarantee of Section 10 or Section 05 section 10.1, tried the way a reviewer would try it).
Prints PASS or FAIL per line and 'THE M7 GUARANTEES HOLD' at the end when every line passes.  Usage: python3 -I tools/probe_rec_m7.py   (from the package root; writes nothing to disk)"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from tests.helpers_rec import AS_OF, RecWorld                     # noqa: E402
from apg import canon, repro                                       # noqa: E402
from apg.det import findings as FD                                 # noqa: E402
from apg.fin import forecast_book as FB                            # noqa: E402
from apg.rec import inputs as IN, lifecycle as L, verify as V      # noqa: E402

results = []


def check(name, fn):
    try:
        ok = bool(fn())
    except Exception as e:                                         # a probe that crashes is a failure, never a pass
        ok = False
        name += ' (raised %s: %s)' % (type(e).__name__, str(e)[:120])
    results.append(ok)
    print('PASS' if ok else 'FAIL', name)


def refused(fn, code):
    try:
        fn()
    except (L.RecError, IN.InputError, V.VerifyError) as e:
        return e.code == code
    return False


def g1():
    w = RecWorld()
    w.set_policy(rank_order=['magnitude'])
    f = w.finding(family='quality_defects', gross=90000000)
    rid = w.ready(f, reviews=False)
    e = w.entry(w.run(), f)
    return e['rank'] == 1 and refused(lambda: L.submit(w.owner2, w.clock, rid), 'NOT_SUBMITTABLE')


def g2():
    w = RecWorld()
    big = w.finding(gross=90000000, strength='weak', label='estimate')
    small = w.finding(gross=200000, date='2026-10-03', time_sensitive=True)
    run = w.run(ingest=False)
    return w.entry(run, small)['rank'] < w.entry(run, big)['rank'] and w.entry(run, big)['route'] == 'investigate' and 'below' in w.entry(run, big)['rank_reason']


def g3():
    w = RecWorld()
    a, b = w.finding(gross=3000000, overlap='g'), w.finding(gross=5000000, overlap='g')
    t = w.run(ingest=False)['result']['totals']['forecast_exposure']
    return t['potential_gross_counted_cents'] == 5000000 and t['not_counted_overlap'] == [w.rid(a)]


def g4():
    w = RecWorld()
    key = FB.slot_key('PRJ-001', AS_OF)
    before = canon.digest(w.s.get(FB.SLOT_KIND, key).payload)
    f = w.finding(gross=5000000)
    w.to_completed(f)
    V.verify(w.verifier, w.clock, w.reg, w.m.reg, w.rid(f), w.baseline['run_key'], 1, w.offsets(), 'checked', w.policy)
    return canon.digest(w.s.get(FB.SLOT_KIND, key).payload) == before


def g5():
    w = RecWorld()
    f = w.finding()
    w.to_approved(f)
    return refused(lambda: L.execute(w.director, w.rid(f), 'place the order'), 'NO_AUTONOMOUS_EXECUTION')


def g6():
    w = RecWorld()
    f = w.finding()
    w.to_approved(f)
    a = refused(lambda: L.transition(w.owner2, w.clock, w.rid(f), 'verified_outcome'), 'USE_VERIFICATION')
    b = refused(lambda: V.verify(w.verifier, w.clock, w.reg, w.m.reg, w.rid(f), w.baseline['run_key'], 1, w.offsets(), 'x', w.policy), 'NOT_COMPLETED')
    try:
        FD.claim_realised(w.s, f, 1)
        c = False
    except FD.LifecycleError:
        c = True
    return a and b and c


def g7():
    w = RecWorld()
    f = w.finding()
    w.to_completed(f)
    o = w.offsets()
    o.pop('financing')
    return refused(lambda: V.verify(w.verifier, w.clock, w.reg, w.m.reg, w.rid(f), w.baseline['run_key'], 1, o, 'x', w.policy), 'OFFSETS_NOT_ADDRESSED')


def g8():
    w = RecWorld()
    f = w.finding()
    rid = w.ready(f)
    w.run()
    L.submit(w.owner2, w.clock, rid)
    t = L.approval_token(L.get(w.s, rid))
    IN.set_inputs(w.owner, w.clock, rid, expected_benefit={'cents': 1, 'basis': 'changed'})
    w.run(as_of='2026-10-01')
    a = refused(lambda: L.approve(w.pm, w.clock, rid, t['version'], t['digest'], t['submission'], 'x'), 'TRANSITION_NOT_ALLOWED')      # the change sent it back to generated
    L.submit(w.owner2, w.clock, rid)
    b = refused(lambda: L.approve(w.pm, w.clock, rid, t['version'], t['digest'], t['submission'], 'x'), 'STALE_APPROVAL')             # resubmitted: the old token is stale
    return a and b and L.get(w.s, rid)['version'] == 2


def g9():
    w = RecWorld()
    f = w.finding()
    w.run()
    IN.set_inputs(w.owner, w.clock, w.rid(f), expected_benefit={'cents': 5, 'basis': 'b'})
    w.run(as_of='2026-10-01')
    x = L.reconstruct(w.s, w.reg, w.rid(f), 1)
    return x['replay_ok'] and x['matches_recorded_digest'] and x['entry']['dimensions']['expected_benefit']['cents'] is None


def g10():
    w = RecWorld()
    f = w.finding()
    rid = w.ready(f)
    w.run()
    return refused(lambda: L.submit(w.ai, w.clock, rid), 'HUMAN_REQUIRED') and refused(lambda: IN.set_inputs(w.ai, w.clock, rid, risks=['x']), 'HUMAN_REQUIRED')


def g11():
    w = RecWorld()
    f = w.finding(interp='potential_opportunity', family='procurement_materials', label='estimate', date='2026-09-29', time_sensitive=True)
    run = w.run(ingest=False)
    e = w.entry(run, f)
    return e['route'] == 'close' and e['rank'] is None and not e['overlap']['counted_in_totals']


def g12():
    w = RecWorld()
    w.finding()
    r = w.run(ingest=False)
    return repro.replay(w.s, w.reg, r['run_key']).ok


check('a pending mandatory review blocks submission of the first-ranked recommendation (PG-RS-AC-05)', g1)
check('a large weak estimate does not outrank a small well-supported time-critical issue, and the order is explained (PG-RS-AC-01, 02, 03)', g2)
check('overlapping findings are counted once in the totals (PG-RS-AC-04)', g3)
check('the whole path including verification leaves the authoritative forecast slot unchanged (PG-RS-AC-07)', g4)
check('an approved recommendation is never executed by APG (PG-RS-AC-08)', g5)
check('there is no path to a realised benefit except the verification gate (PG-RS-AC-10)', g6)
check('a verification that leaves an offsetting cost component unaddressed is refused (Section 05 10.1)', g7)
check('an approval naming a version that has since changed is refused (PG-RS-AC-09)', g8)
check('a past recommendation version is rebuilt from its pinned run (PG-RS-AC-12)', g9)
check('no machine actor submits or writes inputs (Section 10 section 9)', g10)
check('an expired opportunity is routed to close, not ranked and not counted (PG-RS-AC-13)', g11)
check('a recommendation run replays from its pinned inputs (Section 05 section 13)', g12)
print('THE M7 GUARANTEES HOLD' if all(results) else 'A GUARANTEE FAILED', '(%d of %d)' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
