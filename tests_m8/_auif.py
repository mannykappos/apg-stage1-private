"""Shared set-up for the M8 tests.  Importing it makes APG importable, VERIFIES the AUIF rev13 dependency by hash (ZIP, manifest, core tree) and makes AUIF importable from a
fresh verified extraction (apg_auif.dependency.ensure).  Nothing here changes AUIF or any APG release file.  Everything is synthetic.
APG-M11-S1 (P7-B2, P1-F6): APG_ROOT is no longer read.  The package root is this file's own tree, inserted only if absent; an apg package
resolving anywhere else is refused here (the early guard), and the runner's import-identity check is the second line of defence."""
import os, shutil, sys, tempfile
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
HERE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import apg as _apg                                                       # noqa: E402
if not os.path.realpath(_apg.__file__).startswith(os.path.realpath(HERE_ROOT) + os.sep):
    raise ImportError('apg resolves outside this package root: %s (expected under %s)' % (_apg.__file__, HERE_ROOT))

from apg_auif import dependency                                          # noqa: E402
DEP = dependency.ensure()

from apg.ingest import golden_m3 as GM, demo_setup as D, reconcile as R3      # noqa: E402
from apg.fin import demo_fin as DF                                       # noqa: E402
from apg.det import demo_det as DD                                       # noqa: E402
from apg_auif import client, gate, intake, layout, pack as PK            # noqa: E402

AS_OF = '2026-09-30'


def world():
    """(clock, provider, store, audit, who) exactly as the APG golden runs build it."""
    return GM._world()


def load_full(tenant='zero_one', families=('m3', 'fin', 'det'), config=None):
    """Builder Zero through AUIF into a fresh APG world, reconciled, with the demonstration policies proposed and approved in person (as the golden runs do).
    -> dict(env, s=scoped importer, clock, store, audit, who, owner, fv, dv, expected, summaries)."""
    clock, prov, store, audit, who = world()
    s = who('t-' + tenant, tenant, 'ann')
    owner = who('o-' + tenant, tenant, DD.DEMO_OWNER, DD.OWNER_ROLES)
    env, plan = client.builder_zero(HERE_ROOT, tenant, s, clock, families, config)
    sums = {}
    for iid, ent, f in plan:
        sums[f] = env.import_entity(tenant, iid, ent)
    R3.reconcile(s, D.demo_register(), AS_OF)
    fv = DF.install(s, clock, owner)['version'] if 'fin' in families else None
    dv = DD.install_det(s, clock, owner)['version'] if 'det' in families else None
    return dict(env=env, s=s, clock=clock, store=store, audit=audit, who=who, owner=owner, fv=fv, dv=dv, expected=env.bindings[tenant].expected(), summaries=sums, plan=plan)


def copy_folder(tenant, folder):
    """A private copy of one Builder Zero folder (for tests that alter a file).  -> path; the caller removes it."""
    d = tempfile.mkdtemp(prefix='apg_m8_bz_')
    src = os.path.join(HERE_ROOT, 'builder_zero', tenant, folder)
    for f in os.listdir(src):
        shutil.copy(os.path.join(src, f), d)
    return d


def single(iid, base_dir=None, tenant='zero_one', config=None, entities=None):
    """One integration (all files of its folder) in a fresh world and AUIF environment, ACTIVE.  -> dict(env, s, clock, audit, who, binding)."""
    clock, prov, store, audit, who = world()
    s = who('t-' + tenant, tenant, 'ann')
    env = client.AuifEnvironment(HERE_ROOT, config)
    env.bind(tenant, s, clock)
    env.add_file_integration(tenant, iid, entities, base_dir)
    env.start()
    env.activate(tenant, iid)
    return dict(env=env, s=s, clock=clock, store=store, audit=audit, who=who, binding=env.bindings[tenant], tenant=tenant, iid=iid)


def status(s, env, tenant='zero_one', expected=None):
    return gate.assessment_status(s, expected if expected is not None else env.bindings[tenant].expected(), env.module)


def codes(st):
    return sorted({r['code'] for r in st['reasons']})


def records(s, kind):
    return {r.key: r.payload for r in s.query(kind)}


def comparable(payload):
    """A stored record without its provenance (the one declared difference between the paths; see auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json)."""
    import copy
    p = copy.deepcopy(payload)
    p.pop('provenance', None)
    if p.get('conflict'):
        for c in p['conflict']['contenders']:
            c.pop('provenance', None)
    return p


def m3_ingest(s, clock, entity_template, data, source, name, family, revision_field):
    """The M3/M4/M5 file path for one file, exactly as the demonstration loaders call it."""
    from apg.ingest import pipeline as P
    from apg.fin import intake as FI
    from apg.det import intake as DI
    if family == 'm3':
        return P.ingest_file(s, clock, entity_template, data, source, name, D.DEMO_POLICY, revision_field)
    if family == 'fin':
        return FI.ingest_fin_file(s, clock, entity_template, data, source, name, DF.FIN_INTAKE_POLICY, revision_field)
    return DI.ingest_det_file(s, clock, entity_template, data, source, name, None, revision_field)


def rewrite_csv(path, fn):
    """Read a CSV, let fn(header, rows) change it, write it back."""
    import csv, io
    with open(path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header, body = fn(rows[0], rows[1:])
    b = io.StringIO()
    w = csv.writer(b, lineterminator='\n')
    w.writerow(header)
    w.writerows(body)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(b.getvalue())
