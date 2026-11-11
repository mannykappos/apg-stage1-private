"""Builder Zero through AUIF, with the SAME signatures and return values as the M3-path loaders, so the existing golden runs can be repeated on the AUIF path unchanged
(tests_m8/test_m8_path_equivalence.py swaps these in for the duration of one run):
    load_m3(root, scoped, clock, tenant)                       <- apg.ingest.golden_m3._load
    load_zero(root, scoped, clock, tenant, register, as_of)    <- apg.fin.demo_fin.load_zero   (M3 + M4 files, then reconciliation with the SYNTHETIC register)
    load_det(root, scoped, clock, tenant)                      <- apg.det.demo_det.load_det    (M5 files)
Each returns {file name: receipt}, like the M3 loaders.  A batch that AUIF or the adapter blocked appears as {'status': 'blocked', 'reasons': [...]} so a comparison cannot
mistake it for data.  The environments are kept in RUNS (tenant -> list) so a test can inspect what AUIF and the adapter did."""
from . import client

RUNS = {}


def _load(root, scoped, clock, tenant, families):
    env, plan = client.builder_zero(root, tenant, scoped, clock, families)
    RUNS.setdefault(tenant, []).append(env)
    out = {}
    for iid, entity, fname in plan:
        s = env.import_entity(tenant, iid, entity)
        out[fname] = s['receipt'] if s['status'] in ('applied', 'replay') else {'status': 'blocked', 'reasons': s['reasons'], 'counts': {}}
    return out


def load_m3(root, scoped, clock, tenant):
    return _load(root, scoped, clock, tenant, ('m3',))


def load_zero(root, scoped, clock, tenant='zero_one', register=None, as_of='2026-09-30'):
    from apg.ingest import demo_setup as D, reconcile as R3
    out = _load(root, scoped, clock, tenant, ('m3', 'fin'))
    R3.reconcile(scoped, register or D.demo_register(), as_of)
    return out


def load_det(root, scoped, clock, tenant='zero_one'):
    return _load(root, scoped, clock, tenant, ('det',))
