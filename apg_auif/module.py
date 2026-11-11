"""APG as an AUIF module client: a BaseModule (AUIF's ready-made ModulePort, unchanged) that RECEIVES entities, observations, events, integration states and errors.

It never acts outward: it has no action handler, never calls request_action or build_action, and declares no outbound capability (tests check all three).

What it does with a delivery:
  * a delivery for an AUIF tenant that has no APG binding is refused and never stored anywhere (it is listed in `unbound_refusals`);
  * an integration state or error for a bound tenant is written to that tenant's APG store at once (`auif_integration_state`, `auif_alert`) - the assessment gate reads
    them from there, so they survive a restart of this process;
  * an entity and its observation are paired (the object's provenance chain names its observation) and added to the import batch that the APG client opened for that
    tenant (apg_auif.client).  A delivery that arrives with no batch open is unsolicited: it is refused, not stored, and recorded as an alert that blocks the assessment
    until the integration has been imported again in full.
Nothing is turned into an APG record here; apg_auif.intake does that when the client closes the batch, so a batch is applied whole or not at all.
Every handler catches its own failures and records them (ADAPTER_ERROR). (AUIF rev13's BaseModule swallowed a handler exception silently; rev14 reports it to the fabric,
finding M8-F4 corrected. APG still catches its own, so that the gate reads them.)"""
MODULE_ID = 'apg'


def _base():
    from auif_ext.module_client.client import BaseModule
    return BaseModule


class Batch:
    """One import run of one record type of one integration (a sync), or one call that ingests events."""
    def __init__(self, tenant, integration_id, entity, mode, expect):
        self.tenant, self.integration_id, self.entity, self.mode, self.expect = tenant, integration_id, entity, mode, dict(expect)
        self.waiting = {}            # observation_id -> canonical object whose observation has not arrived yet
        self.deliveries = []         # [(kind, object, observation)] in arrival order
        self.errors = []             # AUIF error notifications for this integration while the batch was open
        self.states = []             # AUIF state notifications for this integration while the batch was open
        self.refusals = []           # [(code, detail)] found while receiving
        self.closed = False


def make_module(bindings):
    """bindings: {auif tenant id: apg_auif.intake.Binding}.  -> an APGModule instance."""
    BaseModule = _base()

    class APGModule(BaseModule):
        def __init__(self):
            reqs, seen = [], set()
            for b in bindings.values():
                for iid, integ in sorted(b.integrations.items()):
                    for ent, e in integ['entities'].items():
                        if e['concept'] not in seen:
                            seen.add(e['concept'])
                            reqs.append({'concept': e['concept'], 'attributes': [a['name'] for a in e['definition']['attributes']]})
            super().__init__(MODULE_ID, reqs, {'consumes': [r['concept'] for r in reqs], 'outbound_actions': []})
            self.bindings, self.current, self.unbound_refusals = dict(bindings), {}, []
            for kind in ('entity', 'observation', 'event', 'state', 'error'):
                self.on(kind, self._guarded(kind))

        # ---- batches (opened and closed by the APG client)
        def open_batch(self, tenant, integration_id, entity, mode, expect):
            if tenant in self.current and not self.current[tenant].closed:
                raise RuntimeError('a batch is already open for %s' % tenant)
            b = Batch(tenant, integration_id, entity, mode, expect)
            self.current[tenant] = b
            return b

        def close_batch(self, tenant):
            b = self.current.pop(tenant, None)
            if b is None:
                raise RuntimeError('no batch is open for %s' % tenant)
            b.closed = True
            for oid in sorted(b.waiting):
                b.refusals.append(('LINEAGE_INCOMPLETE', 'canonical object %s arrived without its observation' % b.waiting[oid].get('canonical_id')))
            return b

        # ---- handlers
        def _guarded(self, kind):
            fn = getattr(self, '_on_' + kind)

            def h(ctx, payload):
                try:
                    fn(ctx, payload)
                except Exception as e:                                       # never silent: the failure blocks the assessment
                    t = getattr(ctx, 'tenant_id', None)
                    b = self.current.get(t)
                    if b is not None:
                        b.refusals.append(('ADAPTER_ERROR', '%s handler: %s' % (kind, type(e).__name__)))
                    elif t in self.bindings:
                        self._alert(t, None, 'ADAPTER_ERROR', '%s handler: %s' % (kind, type(e).__name__))
                    else:
                        self.unbound_refusals.append(('ADAPTER_ERROR', kind, str(t)))
            return h

        def _binding(self, ctx, kind):
            t = getattr(ctx, 'tenant_id', None)
            if t not in self.bindings:
                self.unbound_refusals.append(('UNBOUND_TENANT', kind, str(t)[:64]))
                return None
            return self.bindings[t]

        def _alert(self, tenant, integration_id, code, detail):
            self.bindings[tenant].alert(integration_id, code, detail)

        def _on_entity(self, ctx, obj):
            if self._binding(ctx, 'entity') is None:
                return
            b = self.current.get(ctx.tenant_id)
            if b is None:
                return self._alert(ctx.tenant_id, None, 'UNSOLICITED_DELIVERY', 'canonical object %s arrived with no import open' % str(obj.get('canonical_id'))[:80])
            oid = next((s.get('ref') for s in obj.get('provenance_chain', []) if s.get('step_kind') == 'OBSERVATION'), None)
            if not oid or oid in b.waiting:
                b.refusals.append(('LINEAGE_INCOMPLETE', 'canonical object %s names no single observation' % str(obj.get('canonical_id'))[:80]))
                return
            b.waiting[oid] = obj

        def _pair(self, ctx, ob, kind):
            if self._binding(ctx, kind) is None:
                return
            b = self.current.get(ctx.tenant_id)
            if b is None:
                return self._alert(ctx.tenant_id, None, 'UNSOLICITED_DELIVERY', 'observation %s arrived with no import open' % str(ob.get('observation_id'))[:80])
            obj = b.waiting.pop(ob.get('observation_id'), None)
            if obj is None:
                b.refusals.append(('LINEAGE_INCOMPLETE', 'observation %s arrived without its canonical object' % str(ob.get('observation_id'))[:80]))
                return
            b.deliveries.append((kind, obj, ob))

        def _on_observation(self, ctx, ob):
            self._pair(ctx, ob, 'entity')

        def _on_event(self, ctx, ob):
            self._pair(ctx, ob, 'event')

        def _on_state(self, ctx, state):
            bnd = self._binding(ctx, 'state')
            if bnd is None:
                return
            b = self.current.get(ctx.tenant_id)
            if b is not None and state.get('integration_id') == b.integration_id:
                b.states.append(state)
            bnd.record_state(state)

        def _on_error(self, ctx, error):
            bnd = self._binding(ctx, 'error')
            if bnd is None:
                return
            b = self.current.get(ctx.tenant_id)
            iid = error.get('integration')
            if b is not None and iid == b.integration_id:
                b.errors.append(dict(error))
                return
            self._alert(ctx.tenant_id, iid if isinstance(iid, str) else None, 'AUIF_ERROR_OUTSIDE_IMPORT', str(error.get('kind'))[:60])

    return APGModule()

