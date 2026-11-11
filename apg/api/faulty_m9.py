"""DELIBERATELY BROKEN ProjectActionPort implementations (EDR-31, Blueprint Section 15).  They exist only to prove the M9.1 contract suite has teeth: each fault must make at least the listed cases fail.  Never use
these for anything else.   FAULTS maps id -> (description, factory, expected failing case ids)."""
from .reference_m9 import InMemoryActionPort, action_env, where_of
from .approval_boundary import ACTIONS


class AlwaysYes(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        return True


class TruthyNotTrue(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        return 1 if super().allows(ctx, scope, action) else False


class NoneForNo(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        return True if super().allows(ctx, scope, action) else None


class ViewImpliesApprove(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        r = super().allows(ctx, scope, action)
        if not r and action == 'approve':
            return super().allows(ctx, scope, 'view')
        return r


class AnyProjectWillDo(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        if not self.provider.verify(ctx) or where_of(scope) is None or action not in ACTIONS:
            return False
        return any(t == ctx.tenant_id and u == ctx.user_id and a == action for (t, u, w, a) in self._grants)


class ProjectGrantGivesTenantLevel(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        if isinstance(scope, dict) and scope.get('level') == 'tenant' and action in ACTIONS and self.provider.verify(ctx):
            return any(t == ctx.tenant_id and u == ctx.user_id and a == action for (t, u, w, a) in self._grants)
        return super().allows(ctx, scope, action)


class IgnoresTenant(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        w = where_of(scope)
        if not self.provider.verify(ctx) or w is None or action not in ACTIONS:
            return False
        return any(u == ctx.user_id and ww == w and a == action for (t, u, ww, a) in self._grants)


class IgnoresUser(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        w = where_of(scope)
        if not self.provider.verify(ctx) or w is None or action not in ACTIONS:
            return False
        return any(t == ctx.tenant_id and ww == w and a == action for (t, u, ww, a) in self._grants)


class RemembersAnswers(InMemoryActionPort):
    def __init__(self, provider):
        super().__init__(provider)
        self._seen = {}

    def allows(self, ctx, scope, action):
        k = (ctx.tenant_id, ctx.user_id, repr(scope), repr(action))
        if k not in self._seen:
            self._seen[k] = super().allows(ctx, scope, action)
        return self._seen[k]


class NearMatchActions(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        if isinstance(action, str):
            action = action.strip().lower()
        return super().allows(ctx, scope, action)


class RaisesOnOddActions(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        if action not in ACTIONS:
            raise ValueError('unknown action')
        return super().allows(ctx, scope, action)


class RaisesOnOddScopes(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        return super().allows(ctx, {'level': scope['level'], **({'project': scope['project']} if scope['level'] == 'project' else {})}, action)


class ProjectIdsLoose(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        if isinstance(scope, dict) and scope.get('level') == 'project' and isinstance(scope.get('project'), str):
            scope = {'level': 'project', 'project': scope['project'].strip().upper()}
        return super().allows(ctx, scope, action)


class IgnoresTheSession(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        w = where_of(scope)
        if w is None or not (isinstance(action, str) and action in ACTIONS):
            return False
        return (ctx.tenant_id, ctx.user_id, w, action) in self._grants


class MarksWhatItWasGiven(InMemoryActionPort):
    def allows(self, ctx, scope, action):
        r = super().allows(ctx, scope, action)
        if isinstance(scope, dict):
            scope['checked'] = True
        return r


class TrustsTheContextFields(InMemoryActionPort):
    """Checks the session's expiry from the context's own fields, but never asks the context port whether the context is genuine or still valid."""
    def allows(self, ctx, scope, action):
        w = where_of(scope)
        if w is None or not (isinstance(action, str) and action in ACTIONS) or ctx.expires_at <= self.provider.clock.now():
            return False
        return (ctx.tenant_id, ctx.user_id, w, action) in self._grants


FAULTS = {
    'AP-F01': ('answers yes to everything', action_env(AlwaysYes), ['AP-02', 'AP-03', 'AP-04', 'AP-06', 'AP-08', 'AP-09', 'AP-14']),
    'AP-F02': ('answers a truthy 1 instead of True', action_env(TruthyNotTrue), ['AP-01']),
    'AP-F03': ('answers None instead of False', action_env(NoneForNo), ['AP-01', 'AP-02']),
    'AP-F04': ('the right to view carries the right to approve', action_env(ViewImpliesApprove), ['AP-03']),
    'AP-F05': ('any grant of the action in the tenant counts for every project', action_env(AnyProjectWillDo), ['AP-04']),
    'AP-F06': ('a project grant counts as a tenant-level grant', action_env(ProjectGrantGivesTenantLevel), ['AP-05']),
    'AP-F07': ('grants are not kept apart by tenant', action_env(IgnoresTenant), ['AP-06']),
    'AP-F08': ('grants are not kept apart by person', action_env(IgnoresUser), ['AP-14']),
    'AP-F09': ('the first answer is kept and given again after a grant changes', action_env(RemembersAnswers), ['AP-07']),
    'AP-F10': ('an action that nearly matches is accepted', action_env(NearMatchActions), ['AP-08']),
    'AP-F11': ('an unknown action raises instead of being refused', action_env(RaisesOnOddActions), ['AP-08']),
    'AP-F12': ('a scope of the wrong shape raises instead of being refused', action_env(RaisesOnOddScopes), ['AP-09']),
    'AP-F13': ('a project id is matched loosely (trimmed and upper-cased)', action_env(ProjectIdsLoose), ['AP-04']),
    'AP-F14': ('the session is never checked', action_env(IgnoresTheSession), ['AP-11', 'AP-12', 'AP-13']),
    'AP-F15': ('the scope it was given is changed', action_env(MarksWhatItWasGiven), ['AP-10']),
    'AP-F16': ('the context is trusted from its own fields (expiry checked, genuineness not)', action_env(TrustsTheContextFields), ['AP-12', 'AP-13']),
}
