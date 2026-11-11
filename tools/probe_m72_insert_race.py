#!/usr/bin/env python3
"""Reproduces the finding of the independent audit of APG-M7.2 (F-69): a NEW overlapping finding created while a checked act (submission, approval, start of work) is in progress.
The finding is created deterministically at each point the auditor named:
  1A  right after the freshness check returns              1B  at the store, immediately before the act's batch is applied
  2   right after the act's batch has committed (where M7.2 ran its second check)
  3   after the call has returned (in M7.2: after the second check returned and the call completed)
The requirement (the auditor's): an act must never be committed on sources that had already changed.  So, at points 1A and 1B, the act must be refused and NOTHING may be committed, not even
an act that is reversed afterwards: DEFECT PRESENT if any revision of the recommendation with the act's status was ever written.
At points 2 and 3 the act has already committed when the finding is created, so the finding is a later change, handled as any later change: the probe shows that the act committed first
(from the store's commit order, where the store records it) and that the next checked act is refused (for the start of work, which no later act checks, that the next run ends the approval).
On the delivered M7.2 package points 1A and 1B print DEFECT PRESENT (the act is committed, then reversed) and the probe exits 1; on M7.3 it prints THE INSERT RACE IS CLOSED and exits 0.
Usage: python3 -I tools/probe_m72_insert_race.py   (from the package root; writes nothing to disk).  To try it on M7.2, copy this file into the extracted M7.2 package's tools/ folder."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from tests.helpers_rec import RecWorld                              # noqa: E402
from apg.det import findings as FD                                  # noqa: E402
from apg.rec import lifecycle as L                                  # noqa: E402

EXPECT = {'submit': 'awaiting_approval', 'approve': 'approved', 'start': 'in_progress'}
present = []


def is_write(op):
    return isinstance(op, tuple) and len(op) == 4 and op[0] == L.KIND and not type(op).__name__ == 'Guard'


def world(stage):
    w = RecWorld()
    f = w.finding(family='quality_defects', gross=500000)
    rid = w.ready(f)
    w.run()
    if stage in ('approve', 'start'):
        L.submit(w.owner2, w.clock, rid)
    if stage == 'start':
        approve(w, rid)
    return w, f, rid


def approve(w, rid):
    t = L.approval_token(L.get(w.s, rid))
    L.approve(w.pm, w.clock, rid, t['version'], t['digest'], t['submission'], 'ok')


def act(w, rid, stage):
    try:
        {'submit': lambda: L.submit(w.owner2, w.clock, rid), 'approve': lambda: approve(w, rid),
         'start': lambda: L.transition(w.owner2, w.clock, rid, 'in_progress')}[stage]()
        return None
    except L.RecError as e:
        return e.code


def run_case(stage, point):
    w, f, rid = world(stage)
    ref = w.s.get(FD.KIND, f).payload['signal']['evidence'][0]['ref']
    made = []
    create = lambda: made.append(w.finding(family='quality_defects', gross=900000, refs=[ref]))
    rev0 = w.s.get(L.KIND, rid).revision
    store, real_atomic, real_check, fired = w.s._store, w.s._store.atomic, L.source_check, []

    def check_then(*a, **k):
        out = real_check(*a, **k)
        if not fired:
            fired.append(1); create()
        return out

    def before_batch(ctx, ops):
        if not fired and any(is_write(op) for op in ops):
            fired.append(1); create()
        return real_atomic(ctx, ops)

    def after_batch(ctx, ops):
        out = real_atomic(ctx, ops)
        if not fired and any(is_write(op) for op in ops):
            fired.append(1); create()
        return out
    if point == '1A':
        L.source_check = check_then
    elif point == '1B':
        store.atomic = before_batch
    elif point == '2':
        store.atomic = after_batch
    try:
        got = act(w, rid, stage)
    finally:
        L.source_check = real_check
        store.__dict__.pop('atomic', None)
    if point == '3':
        create()
    hist = w.s.history(L.KIND, rid)
    committed = [h.revision for h in hist[rev0:] if h.payload['status'] == EXPECT[stage]]
    now = w.s.get(L.KIND, rid).payload['status']
    if point in ('1A', '1B'):
        defect = bool(committed)
        present.append(defect)
        print('%s %-7s point %-2s: %s; %s; the recommendation is %s' % (
            'DEFECT PRESENT ' if defect else 'closed         ', stage, point, 'refused (%s)' % got if got else 'accepted',
            ('the act was committed as revision %d%s' % (committed[0], ' and then reversed' if now != EXPECT[stage] else '')) if committed else 'nothing was committed', now))
        return
    order = ''
    log = getattr(store, '_commits', None)
    if committed and log is not None:
        t = w.s.ctx.tenant_id
        order = '; store commit order: the act %s the finding' % ('before' if log.index((t, L.KIND, rid, committed[0])) < log.index((t, FD.KIND, made[0], 1)) else 'AFTER')
    nxt = ''
    if now == EXPECT[stage]:
        if stage == 'submit':
            nxt = '; the next checked act (approval): %s' % (act(w, rid, 'approve') or 'accepted')
        elif stage == 'approve':
            nxt = '; the next checked act (start of work): %s' % (act(w, rid, 'start') or 'accepted')
        else:
            w.run(as_of='2026-10-01')
            nxt = '; the next run: the approval is %s' % L.get(w.s, rid)['approval']['state']
    print('later change    %-7s point %-2s: %s; the recommendation is %s%s%s' % (stage, point, 'refused (%s)' % got if got else 'accepted', now, order, nxt))


for stage in ('submit', 'approve', 'start'):
    for point in ('1A', '1B', '2', '3'):
        run_case(stage, point)

print('DEFECT PRESENT' if any(present) else 'THE INSERT RACE IS CLOSED', '(%d of %d present)' % (sum(present), len(present)))
sys.exit(1 if any(present) else 0)
