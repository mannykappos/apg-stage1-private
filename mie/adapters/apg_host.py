"""Host-side adapters that let the core run inside APG's reference environment (EDR-37).  The core's TenantContextPort reuses APG's existing definition (EDR-01): an APG
AuthenticatedContext, verified by APG's TenantContextPort, gives the tenant.  This module is outside the core; the core imports nothing from APG."""
from mie.core.ports import ContextInvalid, ContextMissing, TenantContextPort


class ApgContext(TenantContextPort):
    def __init__(self, apg_provider):
        self.provider = apg_provider

    def resolve(self, ctx):
        if ctx is None:
            raise ContextMissing()
        try:
            ok = self.provider.verify(ctx)
        except Exception:
            raise ContextInvalid()
        if not ok:
            raise ContextInvalid()
        return ctx.tenant_id
