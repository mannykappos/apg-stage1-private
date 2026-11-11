"""APG's side of an AUIF runtime, for SYNTHETIC data only.  It builds an AUIF Fabric from AUIF's own unchanged parts and reference implementations (memory persistence,
reference tenant authority, in-memory secret store, fake clock), registers APG as a module (apg_auif.module), adds read-only integrations, activates them, and runs imports.

Boundaries, enforced here:
  * no real system: every connector is AUIF's own file importer over a local folder, or a synthetic test double;
  * no credentials: every connector declares authentication NONE; the secret store stays empty;
  * no Governor: the Fabric is given NoGovernor, which never grants anything and acknowledges nothing (AUIF then holds governed work, fail-closed), and every integration is
    declared with NO governed operations; nothing here calls the Governor adapter (auif_ext.governor_adapter);
  * no outbound action: this client has no method that requests one, and the APG module declares none;
  * no Engine port: the persistence, tenancy and secret ports are AUIF's reference implementations, not Anchor Engine bindings.
An import is one batch per record type: the client opens the batch in the module, lets AUIF read and deliver, closes the batch and hands it to apg_auif.intake."""
import json, math, os
from . import dependency, definitions as DEF, layout, pack as PK
from .intake import Binding, apply_batch

ENVIRONMENT_ID = 'synthetic-builder-zero'
PRINCIPAL = 'apg-m8-import'
CONFIG_DIR = 'auif_m8'
MAX_KEYS = 2000                       # auif.security.InputGuard's default limit on the keys of one page
MAX_ROWS = 100000                     # auif_ext FileSpec default row limit (the same as APG's mapping Limits)


def load_config(root):
    """The stored PROPOSED definitions, AUIF model and CANDIDATE packs (written by tools/make_m8_config.py)."""
    d = os.path.join(root, CONFIG_DIR)
    defs = json.load(open(os.path.join(d, 'definitions', 'construction_definitions.json'), encoding='utf-8'))
    model = json.load(open(os.path.join(d, 'definitions', 'apg_canonical_model.json'), encoding='utf-8'))
    packs = {}
    for f in sorted(os.listdir(os.path.join(d, 'packs'))):
        if f.endswith('.json'):
            p = json.load(open(os.path.join(d, 'packs', f), encoding='utf-8'))
            packs[p['pack_id']] = p
    return {'definitions': defs, 'model': model, 'packs': packs}


def _ports():
    from auif.ports import GovernorPort, PolicyPort

    class NoGovernor(GovernorPort):
        """APG-M8 wires no Governor.  Every request is answered UNAVAILABLE and no report is acknowledged."""
        def request_decision(self, ctx, request):
            return {'status': 'UNAVAILABLE', 'decision_ref': None, 'decision_hash': None, 'reason': 'APG-M8: no Governor is wired'}

        def report_condition(self, ctx, condition):
            return {'acknowledged': False}

    class NoPolicy(PolicyPort):
        def decide(self, ctx, classification, destination, context):
            return None                                                   # undeterminable: AUIF refuses anything that needs a policy decision
    return NoGovernor, NoPolicy


class AuifEnvironment:
    def __init__(self, root, config=None, sequencer_policy=None):
        self.dep = dependency.ensure()
        from auif.canonical import CanonicalModel
        from auif.clock import FakeClock
        from auif.fabric import Fabric
        from auif.observability import Telemetry
        from auif.tenancy import TenantAuthority, TenantScopedPersistence
        from auif.throttle import Throttle
        from auif.translation import PackRegistry
        from auif.util import Ids
        from auif_ref.persistence import MemoryPersistence
        from auif_ref.secrets import InMemorySecretStore
        NoGovernor, NoPolicy = _ports()
        self.root, self.cfg = root, config or load_config(root)
        self.templates = DEF.load_templates(root)
        self.defs = DEF.by_entity(self.cfg['definitions'])
        self.clock, self.ids, self.tel, self.auth = FakeClock(), Ids(), Telemetry(), TenantAuthority()
        self.store = TenantScopedPersistence(MemoryPersistence(), self.auth)
        self.packs = PackRegistry()
        for p in self.cfg['packs'].values():
            self.packs.register(p)
        self.governor = NoGovernor()
        self.fabric = Fabric(store=self.store, authority=self.auth, secrets=InMemorySecretStore(), governor=self.governor, policy=NoPolicy(), clock=self.clock,
                             telemetry=self.tel, ids=self.ids, model=CanonicalModel(self.cfg['model']), packs=self.packs, throttle=Throttle(self.clock, default_rate=1000, default_burst=1000),
                             sequencer_policy=sequencer_policy)
        self.bindings, self.ctx, self.module = {}, {}, None

    # ---- configuration
    def entity_config(self, entity, family=None, policy=None, revision_field=None, file_name=None):
        from apg.det.intake import DET_INTAKE_POLICY
        from apg.fin.demo_fin import FIN_INTAKE_POLICY
        from apg.ingest.demo_setup import DEMO_POLICY
        d = self.defs[entity]
        fam = family or d['intake_family']
        info = layout.by_template().get(d['template_id'], {})
        return {'family': fam, 'template': self.templates[d['template_id']], 'policy': policy or {'m3': DEMO_POLICY, 'fin': FIN_INTAKE_POLICY, 'det': DET_INTAKE_POLICY}[fam],
                'revision_field': revision_field if revision_field is not None else d['revision_field'], 'concept': d['concept'], 'definition': d,
                'file': file_name or info.get('file'), 'model_version': self.cfg['model']['model_version']}

    def bind(self, tenant, scoped, apg_clock):
        if self.module is not None:
            raise RuntimeError('bind every tenant before start()')
        if scoped.ctx.tenant_id != tenant:
            raise ValueError('the APG store is for tenant %s, not %s' % (scoped.ctx.tenant_id, tenant))
        self.ctx[tenant] = self.auth.issue(tenant, PRINCIPAL)
        self.bindings[tenant] = Binding(scoped, apg_clock, {})
        return self.bindings[tenant]

    def add_file_integration(self, tenant, iid, entities=None, base_dir=None, pack_id=None):
        """A Builder Zero folder as one read-only integration.  entities: the record types to declare (default: every file of the integration that exists)."""
        specs = PK.file_specs(self.root, tenant, iid, self.templates)
        if entities is not None:
            specs = type(specs)((e, s) for e, s in specs.items() if e in entities)
        conn = PK.connector(self.root, tenant, iid, self.templates, specs, base_dir)
        p = self.cfg['packs'][pack_id or PK.pack_id(iid)]
        src = layout.integrations()[iid]['source']
        return self._add(tenant, iid, conn, p, src, list(specs), {e: self.entity_config(e, file_name=s.filename) for e, s in specs.items()})

    def add_integration(self, tenant, iid, connector, pack, source, entities, entity_configs, event_entities=None, identity_fields=None):
        return self._add(tenant, iid, connector, pack, source, entities, entity_configs, event_entities, identity_fields)

    def _add(self, tenant, iid, conn, p, source, entities, econf, event_entities=None, identity_fields=None):
        bad = PK.form_problems(p)
        if bad:
            raise ValueError('pack %s is not in the contract reference form: %s' % (p.get('pack_id'), bad[:3]))
        ref = PK.ref(p)
        ident = dict(identity_fields or {})
        for e in entities:                                              # APG-M8.1: every record type's AUIF source identity is its natural key, composite keys included
            nk = econf[e]['template']['natural_key']                    # (AUIF rev14; on rev13 a composite key fell back to a content hash: finding M8-F2)
            ident.setdefault(e, nk[0] if len(nk) == 1 else list(nk))
        c = self.fabric.add_integration(self.ctx[tenant], integration_id=iid, anchor_module=DEF.MODULE_ID, connector=conn, pack_ref=ref, target_system_id=iid,
                                        environment_id=ENVIRONMENT_ID, governed_operations=(), entities=list(entities), identity_fields=ident, event_entities=event_entities)
        self.bindings[tenant].integrations[iid] = {'source': source, 'pack_ref': ref, 'fingerprints': list(p['schema_expectations']['compatible_fingerprints']),
                                                   'target_system_id': iid, 'environment_id': ENVIRONMENT_ID, 'connector_id': c.runtime.desc['connector_id'],
                                                   'entities': {e: econf[e] for e in entities}}
        return c

    def start(self):
        from auif_ext.module_client.client import ModuleClient
        from .module import make_module
        self.module = make_module(self.bindings)
        self.client = ModuleClient(self.fabric, self.module)
        return self.module

    # ---- running
    def activate(self, tenant, iid):
        return self.client.activate(self.ctx[tenant], iid)

    def _expect(self, tenant, iid, entity):
        integ = self.bindings[tenant].integrations[iid]
        ncols = len(integ['entities'][entity]['template']['columns'])
        page = max(1, min(200, (MAX_KEYS - 3) // max(1, ncols)))
        st = self.bindings[tenant].state(iid) or {}
        return {'manifest_ref': dict(st.get('manifest_ref') or {'id': None, 'version': None, 'hash': None}), 'page_size': page, 'max_pages': math.ceil(MAX_ROWS / page) + 2}

    def import_entity(self, tenant, iid, entity):
        """Read one record type through AUIF and apply it to APG as one batch.  -> intake summary."""
        ex = self._expect(tenant, iid, entity)
        self.module.open_batch(tenant, iid, entity, 'sync', ex)
        rep = None
        raised = None
        try:
            rep = self.fabric.sync(self.ctx[tenant], iid, entity, max_pages=ex['max_pages'], page_size=ex['page_size'])
        except Exception as e:                                          # AUIF itself raised: fail closed, never retry around it (rev13 did, finding M8-F6; kept as a guard)
            raised = e
        finally:
            b = self.module.close_batch(tenant)
        if raised is not None:
            b.refusals.append(('AUIF_RAISED', 'AUIF raised %s: %s' % (type(raised).__name__, str(raised)[:120])))
            rep = None
        return apply_batch(self.bindings[tenant], b, rep)

    def ingest_events(self, tenant, iid, entity, events):
        """Hand AUIF a list of source events for one integration (synthetic) and apply what it delivers.  -> intake summary (with the AUIF ordering results)."""
        ex = self._expect(tenant, iid, entity)
        self.module.open_batch(tenant, iid, entity, 'events', ex)
        res = []
        raised = None
        try:
            res = self.fabric.ingest_events(self.ctx[tenant], iid, events)
        except Exception as e:                                          # AUIF itself raised: fail closed, never retry around it (rev13 did, finding M8-F6; kept as a guard)
            raised = e
        finally:
            b = self.module.close_batch(tenant)
        if raised is not None:
            b.refusals.append(('AUIF_RAISED', 'AUIF raised %s: %s' % (type(raised).__name__, str(raised)[:120])))
            res = []
        out = apply_batch(self.bindings[tenant], b, res, self.fabric.sequencer.pending(self.ctx[tenant], iid))
        out['ordering'] = res
        return out

    def tick(self, tenant, iid, entity):
        """Let AUIF's sequencer time out queued events (it moves them to reconciliation, never invents state) and apply what that changes."""
        ex = self._expect(tenant, iid, entity)
        self.module.open_batch(tenant, iid, entity, 'events', ex)
        res = []
        raised = None
        try:
            res = self.fabric.tick(self.ctx[tenant], iid)
        except Exception as e:                                          # AUIF itself raised: fail closed, never retry around it (rev13 did, finding M8-F6; kept as a guard)
            raised = e
        finally:
            b = self.module.close_batch(tenant)
        if raised is not None:
            b.refusals.append(('AUIF_RAISED', 'AUIF raised %s: %s' % (type(raised).__name__, str(raised)[:120])))
            res = []
        out = apply_batch(self.bindings[tenant], b, res, self.fabric.sequencer.pending(self.ctx[tenant], iid))
        out['ordering'] = res
        return out


def builder_zero(root, tenant, scoped, apg_clock, families=('m3', 'fin', 'det'), config=None):
    """A started AUIF environment with the Builder Zero integrations of `tenant` that hold the requested record families (a file that does not exist for the tenant is not
    declared and not read, exactly as M3 skips it).  -> (env, [(integration id, entity, file name)] in M3 load order)."""
    env = AuifEnvironment(root, config)
    env.bind(tenant, scoped, apg_clock)
    plan, per = [], {}
    for fam, tid, folder, fname, src, rev in layout.ENTITIES:
        if fam not in families or not os.path.exists(os.path.join(root, 'builder_zero', tenant, folder, fname)):
            continue
        iid = layout.integration_id(src, folder)
        ent = env.templates[tid]['target_entity']
        per.setdefault(iid, []).append(ent)
        plan.append((iid, ent, fname))
    for iid in per:
        env.add_file_integration(tenant, iid)                  # every file of the folder is declared (the pack's schema fingerprint covers them all); only `plan` is read
    env.start()
    for iid in per:
        env.activate(tenant, iid)
    return env, plan
