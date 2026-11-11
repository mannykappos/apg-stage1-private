#!/usr/bin/env python3
"""Reproduces the finding of the independent audit of APG-M7.1 (F-68): a source change that lands between the source-freshness check and the write of the recommendation.
The competing change is inserted deterministically, at two points:
  A. right after the freshness check has returned "current" (lifecycle.source_check is wrapped);
  B. at the store, immediately before the recommendation write is applied (the record store's atomic batch is wrapped).
At each of the three checked boundaries (submission, approval, start of work) the finding is dismissed; at submission the mandatory review is also changed to not_cleared.
A case is closed only if the act is refused AND nothing is recorded (the recommendation keeps its revision: no act, and no act-then-reversal).
On the delivered M7.1 package it prints DEFECT PRESENT for each case and exits 1; on M7.2 it prints THE RACE IS CLOSED and exits 0.
Usage: python3 -I tools/probe_m71_race.py   (from the package root; writes nothing to disk).  To try it on M7.1, copy this file into the extracted M7.1 package's tools/ folder."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from tests.helpers_rec import RecWorld                              # noqa: E402
from apg.det import findings as FD                                  # noqa: E402
from apg.rec import inputs as IN, lifecycle as L                    # noqa: E402

present = []


def after_check(change):
    """Point A: the competing change runs once, right after the freshness check returns."""
    real = L.source_check
    state = {'done': False}

    def wrapped(*a, **k):
        out = real(*a, **k)
        if not state['done']:
            state['done'] = True
            change()
        return out
    L.source_check = wrapped
    return lambda: setattr(L, 'source_check', real)


def before_commit(w, change):
    """Point B: the competing change runs once, at the store, immediately before the batch that writes the recommendation is applied."""
    store = w.s._store
    real = store.atomic
    state = {'done': False}

    def wrapped(ctx, ops):
        if not state['done'] and any(op[0] == L.KIND for op in ops):
            state['done'] = True
            change()
        return real(ctx, ops)
    store.atomic = wrapped
    return lambda: setattr(store, 'atomic', real)


def world(stage):
    w = RecWorld()
    f = w.finding(family='quality_defects', gross=500000)
    rid = w.ready(f)
    w.run()
    if stage in ('approve', 'start'):
        L.submit(w.owner2, w.clock, rid)
    if stage == 'start':
        t = L.approval_token(L.get(w.s, rid))
        L.approve(w.pm, w.clock, rid, t['version'], t['digest'], t['submission'], 'ok')
    return w, f, rid


def act(w, rid, stage):
    if stage == 'submit':
        L.submit(w.owner2, w.clock, rid)
    elif stage == 'approve':
        t = L.approval_token(L.get(w.s, rid))
        L.approve(w.pm, w.clock, rid, t['version'], t['digest'], t['submission'], 'ok')
    else:
        L.transition(w.owner2, w.clock, rid, 'in_progress')


EXPECT = {'submit': 'awaiting_approval', 'approve': 'approved', 'start': 'in_progress'}
CHANGES = {
    'the finding is dismissed': lambda w, f, rid: FD.transition(w.rev, w.clock, f, 'dismissed', rationale='not a real issue after all'),
    'the mandatory review is changed to not_cleared': lambda w, f, rid: IN.record_review(w.creview, w.clock, rid, 'quality', 'not_cleared', 'the substitute fails the specification'),
}
CASES = [(stage, point, what) for stage in ('submit', 'approve', 'start') for point in ('A', 'B') for what in CHANGES if stage == 'submit' or what == 'the finding is dismissed']

for stage, point, what in CASES:
    w, f, rid = world(stage)
    before = L.get(w.s, rid)['status']
    rev = w.s.get(L.KIND, rid).revision
    change = lambda: CHANGES[what](w, f, rid)
    undo = after_check(change) if point == 'A' else before_commit(w, change)
    try:
        try:
            act(w, rid, stage)
            refused = None
        except L.RecError as e:
            refused = e.code
    finally:
        undo()
    status = L.get(w.s, rid)['status']
    recorded = w.s.get(L.KIND, rid).revision - rev
    defect = refused is None or recorded != 0 or status != before
    present.append(defect)
    print('%s %s, competing change at point %s (%s): %s' % ('DEFECT PRESENT ' if defect else 'closed         ', stage, point, what,
          ('accepted; the recommendation is %s' % status) if refused is None else
          ('refused (%s); the recommendation is %s; %s' % (refused, status, 'nothing was recorded' if not recorded else '%d revision(s) were recorded' % recorded))))

print('DEFECT PRESENT' if any(present) else 'THE RACE IS CLOSED', '(%d of %d present)' % (sum(present), len(present)))
sys.exit(1 if any(present) else 0)
