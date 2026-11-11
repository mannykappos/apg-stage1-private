"""In-memory reference ProjectActionPort (a TEST DOUBLE that passes the EDR-31 contract; it is not a permission model) and the factory that builds the contract environment around it."""
from ..reference_impl import FakeClock, StaticContextProvider
from .approval_boundary import ProjectActionPort, ACTIONS
from .contracts_m9 import ActionEnv, TENANT


def where_of(scope):
    """-> the project id, or TENANT for a tenant-level scope, or None if the scope is not exactly one of the two."""
    if not isinstance(scope, dict):
        return None
    if set(scope) == {'level', 'project'} and scope['level'] == 'project' and isinstance(scope['project'], str) and scope['project']:
        return scope['project']
    if set(scope) == {'level'} and scope['level'] == 'tenant':
        return TENANT
    return None


class InMemoryActionPort(ProjectActionPort):
    def __init__(self, provider):
        self.provider = provider
        self._grants = set()

    def allows(self, ctx, scope, action):
        try:
            if self.provider.verify(ctx) is not True:
                return False
        except Exception:
            return False
        where = where_of(scope)
        if where is None or not (isinstance(action, str) and action in ACTIONS):
            return False
        return (ctx.tenant_id, ctx.user_id, where, action) in self._grants

    def _contract_grant(self, tenant_id, user_id, where, action):
        self._grants.add((tenant_id, user_id, where, action))

    def _contract_revoke_grant(self, tenant_id, user_id, where, action):
        self._grants.discard((tenant_id, user_id, where, action))


def action_env(port_cls=InMemoryActionPort, provider_cls=StaticContextProvider):
    def factory():
        c = FakeClock()
        p = provider_cls(c)
        return ActionEnv(p, port_cls(p), c.advance)
    return factory
