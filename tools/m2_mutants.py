#!/usr/bin/env python3
"""Mutation run over the M2 control modules.  Each mutant is a one-place textual change to a COPY of the package; the unit/adversarial tests and the
port contract suites are run against it; a mutant is KILLED when either fails.  Usage: python3 -I tools/m2_mutants.py [--list] [--jobs N]
Exit 0 only if every mutant is killed or is a documented equivalent.  apg/materiality.py is covered by the CR-02 mutation run (79 mutants), not here."""
import os, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True

# (id, file, old, new)  -- old must occur in the file
MUT = [
 # ---- canon
 ('CA01-float-allowed', 'canon.py', "    if isinstance(obj, float):\n        raise CanonError(f'float not allowed", "    if False:\n        raise CanonError(f'float not allowed"),
 ('CA02-nonstring-key-allowed', 'canon.py', "if not isinstance(k, str):\n                raise CanonError", "if False:\n                raise CanonError"),
 ('CA03-keys-not-sorted', 'canon.py', "json.dumps(obj, sort_keys=True,", "json.dumps(obj, sort_keys=False,"),
 ('CA04-no-nfkc', 'canon.py', "s = unicodedata.normalize('NFKC', k)", "s = k"),
 ('CA05-invisible-kept', 'canon.py', "if cat in ('Cf', 'Cc'):", "if False:"),
 ('CA06-separators-not-unified', 'canon.py', "'_' if cat in ('Zs', 'Zl', 'Zp') or ch in '-.' else ch", "ch"),
 ('CA07-case-kept', 'canon.py', "return ''.join(out).lower()", "return ''.join(out)"),
 ('CA08-unsupported-type-allowed', 'canon.py', "    raise CanonError(f'unsupported type", "    return\n    raise CanonError(f'unsupported type"),
 # ---- values
 ('VA01-known-accepts-bool', 'values.py', "if not isinstance(self.cents, int) or isinstance(self.cents, bool):", "if not isinstance(self.cents, int):"),
 ('VA02-known-truthy', 'values.py', "raise UnknownValueError('use .cents explicitly; truthiness of money is ambiguous')", "return True"),
 ('VA03-unknown-falsy', 'values.py', "raise UnknownValueError('an unknown value has no truth value')", "return False"),
 ('VA04-unknown-cents-zero', 'values.py', "raise UnknownValueError(f'value is unknown ({self.reason}): {self.detail}')", "return 0"),
 ('VA05-unknown-arith-zero', 'values.py', "raise UnknownValueError(f'arithmetic on an unknown value ({self.reason}) is refused')", "return 0"),
 ('VA06-bool-is-money', 'values.py', "if isinstance(x, bool):\n        return Unknown(INVALID, 'boolean is not money')", "if False:\n        return Unknown(INVALID, 'boolean is not money')"),
 ('VA07-unicode-digits', 'values.py', "s.isascii() and (", "("),
 ('VA08-total-counts-unknown', 'values.py', "        else:\n            out.append((iid, v.reason, v.detail))", "        else:\n            inc.append(iid)"),
 ('VA09-total-always-complete', 'values.py', "return Total(s, not out,", "return Total(s, True,"),
 ('VA10-require-complete-silent', 'values.py', "if not self.complete:\n            raise", "if False:\n            raise"),
 ('VA11-zero-denominator-allowed', 'values.py', "if d.cents <= 0:", "if d.cents < 0:"),
 ('VA12-round-half-down', 'values.py', "if 2 * r >= d.cents:", "if 2 * r > d.cents:"),
 ('VA13-sign-lost', 'values.py', "return Known(q if n.cents >= 0 else -q)", "return Known(q)"),
 ('VA14-unknown-numerator-used', 'values.py', "    if isinstance(n, Unknown):\n        return n", "    if False:\n        return n"),
 ('VA15-unknown-denominator-used', 'values.py', "    if isinstance(d, Unknown):\n        return d", "    if False:\n        return d"),
 # ---- tenancy
 ('TE01-org-names-ignored', 'tenancy.py', "return 'tenant' in n or n in _ORG_NAMES", "return 'tenant' in n"),
 ('TE02-tenant-word-ignored', 'tenancy.py', "return 'tenant' in n or n in _ORG_NAMES", "return n in _ORG_NAMES"),
 ('TE03-underscores-kept', 'tenancy.py', "n = canon.norm_key(key).replace('_', '')", "n = canon.norm_key(key)"),
 ('TE04-depth-cap-removed', 'tenancy.py', "    if depth > MAX_DEPTH:\n        raise TenantMismatch('payload nesting too deep to inspect safely')\n    out = []", "    out = []"),
 ('TE05-embedded-json-ignored', 'tenancy.py', "if t[:1] in ('{', '[') and len(t) < 1_000_000:", "if False:"),
 ('TE06-lookalike-matches', 'tenancy.py', " and value == tenant_id", ""),
 ('TE07-foreign-claims-allowed', 'tenancy.py', "bad = [c for c in claims if not _same(c[2], ctx.tenant_id)]", "bad = []"),
 ('TE08-refusal-not-audited', 'tenancy.py', "        if audit is not None:\n            audit.append(ctx, 'tenant_claim.refused', bad[0][0]", "        if False:\n            audit.append(ctx, 'tenant_claim.refused', bad[0][0]"),
 ('TE09-claims-not-stripped', 'tenancy.py', "if not (isinstance(k, str) and is_claim_key(k))}", "if True}"),
 ('TE10-embedded-claims-not-stripped', 'tenancy.py', "if isinstance(obj, str) and find_claims(obj, depth=depth + 1):", "if False:"),
 ('TE11-put-unscreened', 'tenancy.py', "clean, _ = screen_payload(self.ctx, payload, self._audit)\n        return self._store.put(self.ctx, kind, key, clean, expected_revision)", "return self._store.put(self.ctx, kind, key, payload, expected_revision)"),
 ('TE12-atomic-unscreened', 'tenancy.py', "clean, _ = screen_payload(self.ctx, payload, self._audit)\n            cleaned.append", "clean = payload\n            cleaned.append"),
 ('TE13-query-filter-unscreened', 'tenancy.py', "screen_payload(self.ctx, where, self._audit)         # a tenant-like filter field is refused or ignored, never honoured\n            where, _ = screen_payload(self.ctx, where)", "pass"),
 ('TE14-job-claim-unchecked', 'tenancy.py', "if claimed is not None and not _same(claimed, ctx.tenant_id):", "if False:"),
 ('TE15-job-payload-unscreened', 'tenancy.py', "clean, _ = screen_payload(ctx, job.get('payload', {}), audit)\n    return scoped, clean", "return scoped, job.get('payload', {})"),
 ('TE16-scoped-ctx-unchecked', 'tenancy.py', "if not isinstance(ctx, AuthenticatedContext):\n            raise NoContext('a verified context is required')\n        self._store", "if False:\n            raise NoContext('a verified context is required')\n        self._store"),
 ('TE17-job-credentials-unchecked', 'tenancy.py', "if not isinstance(job, dict) or 'credentials' not in job:", "if False:"),
 ('TE18-screen-ctx-unchecked', 'tenancy.py', "    if not isinstance(ctx, AuthenticatedContext):\n        raise NoContext('a verified context is required')\n    claims", "    claims"),
 # ---- reference implementations (the contract suites must notice)
 ('RI01-seal-unchecked', 'reference_impl.py', "if not hmac.compare_digest(self._seal(ctx.fields()), ctx.seal):\n            return False", "if False:\n            return False"),
 ('RI02-expiry-unchecked-in-verify', 'reference_impl.py', "if ctx.expires_at <= self.clock.now():\n            return False", "if False:\n            return False"),
 ('RI03-revocation-unchecked-in-verify', 'reference_impl.py', "for tok in self._revoked:", "for tok in ():"),
 ('RI04-revoked-credentials-resolve', 'reference_impl.py', " or credentials in self._revoked:", ":"),
 ('RI05-expired-credentials-resolve', 'reference_impl.py', "if exp <= self.clock.now():\n            raise Unauthenticated('session expired')", "if False:\n            raise Unauthenticated('session expired')"),
 ('RI06-context-type-unchecked', 'reference_impl.py', "if not isinstance(ctx, AuthenticatedContext):\n            return False", "if False:\n            return False"),
 ('RI07-missing-context-allowed', 'reference_impl.py', "if ctx is None:\n        raise NoContext('no context supplied')", "if False:\n        raise NoContext('no context supplied')"),
 ('RI08-expected-revision-ignored', 'reference_impl.py', "if exp is not None and (not isinstance(exp, int) or isinstance(exp, bool) or exp != cur_rev):", "if False:"),
 ('RI09-identical-put-appends', 'reference_impl.py', "if cur is not None and cur.payload_hash == h:", "if False:"),
 ('RI10-query-crosses-tenants', 'reference_impl.py', "if t == ctx.tenant_id and k == kind:", "if k == kind:"),
 ('RI11-revision-zero-reads-latest', 'reference_impl.py', "1 <= revision <= len(h)", "0 <= revision <= len(h)"),
 ('RI12-output-aliased', 'reference_impl.py', "return Record(t, kind, key, rev, canon.deep_copy(payload), h)", "return Record(t, kind, key, rev, payload, h)"),
 ('RI13-input-aliased', 'reference_impl.py', "return canon.deep_copy(payload), canon.digest(payload)", "return payload, canon.digest(payload)"),
 ('RI14-batch-ops-not-staged', 'reference_impl.py', "            staged[(kind, key)] = rec\n", "            pass\n"),
 ('RI15-audit-chain-not-linked', 'reference_impl.py', "prev = chain[-1].hash if chain else ZERO_HASH", "prev = ZERO_HASH"),
 ('RI16-verify-ignores-links', 'reference_impl.py', " or e.prev_hash != prev", ""),
 ('RI17-verify-ignores-hash', 'reference_impl.py', " or _event_hash(e) != e.hash", ""),
 ('RI18-secrets-not-redacted', 'reference_impl.py', "'[REDACTED]' if _SECRET_KEY.search(k)", "'[REDACTED]' if False"),
 ('RI19-audit-read-aliased', 'reference_impl.py', "'detail': canon.deep_copy(e.detail)", "'detail': e.detail"),
 ('RI20-audit-chain-shared', 'reference_impl.py', "chain = self._d.setdefault(ctx.tenant_id, [])", "chain = self._d.setdefault('shared', [])"),
 ('RI21-audit-seq-off-by-one', 'reference_impl.py', "proto = AuditEvent(ctx.tenant_id, len(chain) + 1,", "proto = AuditEvent(ctx.tenant_id, len(chain),"),
 ('RI22-ids-unchecked', 'reference_impl.py', " or _ID_BAD.search(v)", ""),
 ('RI23-reason-type-unchecked', 'reference_impl.py', "if not isinstance(v, str):\n                raise PayloadInvalid(n + ' must be a string')", "if False:\n                raise PayloadInvalid(n + ' must be a string')"),
 ('RI24-audit-verify-skips-tenant', 'reference_impl.py', " or e.tenant_id != ctx.tenant_id", ""),
 ('RI25-seal-not-over-fields', 'reference_impl.py', "return hmac.new(self._secret, canon.canonical(fields).encode('ascii'), hashlib.sha256).hexdigest()", "return hmac.new(self._secret, canon.canonical({'tenant_id': fields['tenant_id']}).encode('ascii'), hashlib.sha256).hexdigest()"),
 # ---- source authority
 ('SA01-proposer-may-approve', 'source_authority.py', " and a.approver != self.proposer", ""),
 ('SA02-ai-may-approve', 'source_authority.py', "a.kind == 'human' and a.role", "a.role"),
 ('SA03-any-role-approves', 'source_authority.py', "a.role == 'authority_owner'", "True"),
 ('SA04-overlap-allowed', 'source_authority.py', "                if lo <= hi:\n                    raise", "                if False:\n                    raise"),
 ('SA05-asof-unchecked', 'source_authority.py', "if not (isinstance(as_of, str) and _DATE.fullmatch(as_of)):", "if not isinstance(as_of, str):"),
 ('SA06-unapproved-register-used', 'source_authority.py', "if register is None or not register.approved():", "if register is None:"),
 ('SA07-unpermitted-source-used', 'source_authority.py', "live = [o for o in live if o.source in allowed]", "live = [o for o in live if True]"),
 ('SA08-cancelled-used', 'source_authority.py', "live = [o for o in observations if not o.cancelled]", "live = [o for o in observations]"),
 ('SA09-lowest-revision-wins', 'source_authority.py', "top = max(revs)", "top = min(revs)"),
 ('SA10-same-revision-conflict-ignored', 'source_authority.py', "if len({_txt(o.value) for o in at_top}) > 1:", "if False:"),
 ('SA11-unknown-revision-order-ignored', 'source_authority.py', "if any(r is None for r in revs):", "if False:"),
 ('SA12-invalid-revision-ignored', 'source_authority.py', "if any(r is not None and (not isinstance(r, int) or isinstance(r, bool)) for r in revs):", "if False:"),
 ('SA13-ocr-trusted', 'source_authority.py', "if chosen.origin != 'system' and not chosen.human_verified:", "if False:"),
 ('SA14-human-approval-skipped', 'source_authority.py', "if rule.nature == 'human_approved' and chosen.approved_by_role is None:", "if False:"),
 ('SA15-only-higher-secondary-flagged', 'source_authority.py', "as_value(o.value).cents != val.cents]", "as_value(o.value).cents > val.cents]"),
 ('SA16-quarantine-mode-ignored', 'source_authority.py', "if rule.on_secondary_disagreement == 'quarantine':", "if False:"),
 ('SA17-warnings-dropped', 'source_authority.py', "    if warnings:\n        return out(ACCEPTED_W", "    if False:\n        return out(ACCEPTED_W"),
 ('SA18-pending-not-worst', 'source_authority.py', "for bad in (REJECTED, QUARANTINED, PENDING):", "for bad in (REJECTED, QUARANTINED):"),
 ('SA19-provisional-nature-ignored', 'source_authority.py', "if any(r.rule_nature == 'provisional' for r in resolutions):", "if False:"),
 ('SA20-total-counts-unaccepted', 'source_authority.py', "if status in AUTHORITATIVE_OUTCOMES and isinstance(v, Known):", "if isinstance(v, Known):"),
 ('SA21-total-always-complete', 'source_authority.py', "return AuthoritativeTotal(s, not exc,", "return AuthoritativeTotal(s, True,"),
 ('SA22-auth-total-addable', 'source_authority.py', "raise TypeError('an authoritative total cannot be added to anything else; combine inside a recorded calculation')", "return 0"),
 ('SA23-provisional-counts-accepted', 'source_authority.py', "if status not in AUTHORITATIVE_OUTCOMES and isinstance(v, Known):\n            s += v.cents; un.append", "if isinstance(v, Known):\n            s += v.cents; un.append"),
 ('SA24-provisional-addable', 'source_authority.py', "raise TypeError('a provisional total cannot be added to an authoritative total')", "return 0"),
 ('SA25-resolver-role-unchecked', 'source_authority.py', " or p['resolver_role'] not in approver_ctx.roles", ""),
 ('SA26-ai-may-resolve', 'source_authority.py', "approver_ctx.actor_kind != 'human' or ", ""),
 ('SA27-note-optional', 'source_authority.py', "if not isinstance(note, str) or not note.strip():", "if False:"),
 ('SA28-same-person-twice', 'source_authority.py', "if any(a['by'] == approver_ctx.user_id for a in p['approvals']):", "if False:"),
 ('SA29-one-approval-promotes', 'source_authority.py', "if len(p['approvals']) >= p['required_approvals']:", "if len(p['approvals']) >= 1:"),
 ('SA30-disagreeing-approvers', 'source_authority.py', "if len({a['action'] for a in p['approvals']}) > 1 or", "if False or"),
 ('SA31-final-state-rewritten', 'source_authority.py', "if p['status'] in ('promoted', 'rejected', 'merged'):\n            return item", "if False:\n            return item"),
 ('SA32-correction-unchecked', 'source_authority.py', "if action == 'correct' and (not isinstance(corrected_cents, int) or isinstance(corrected_cents, bool)):", "if False:"),
 ('SA33-retained-not-open', 'source_authority.py', "if r.payload['status'] in ('held', 'retained'))", "if r.payload['status'] in ('held',))"),
 ('SA34-register-replaced', 'source_authority.py', "if register.version in self._v:", "if False:"),
 ('SA35-supersedes-unchecked', 'source_authority.py', "if self._order and register.supersedes != self._order[-1]:", "if False:"),
 ('SA36-rule-end-exclusive', 'source_authority.py', "or as_of <= self.effective_to)", "or as_of < self.effective_to)"),
 ('SA37-rule-start-exclusive', 'source_authority.py', "return self.effective_from <= as_of and", "return self.effective_from < as_of and"),
 ('SA38-batch-conflict-ignored', 'source_authority.py', "elif d not in seen[k]:", "elif False:"),
 ('SA39-batch-no-identifier-ok', 'source_authority.py', "if not isinstance(k, str) or not k.strip():\n            bad.setdefault", "if False:\n            bad.setdefault"),
 ('SA40-conflict-rows-still-clean', 'source_authority.py', "clean = [r for k, r in first.items() if k not in bad]", "clean = list(first.values())"),
 ('SA41-approvals-zero', 'source_authority.py', "or self.required_approvals < 1:", "or self.required_approvals < 0:"),
 ('SA42-action-unchecked', 'source_authority.py', "if action not in ('accept', 'correct', 'reject', 'merge', 'retain'):", "if False:"),
 ('SA43-conflict-not-logged', 'source_authority.py', "scoped.log('ingest.conflict'", "pass; (lambda *a, **k: None)('ingest.conflict'"),
 # ---- status model
 ('SM01-result-must-be-exactly-pass', 'status_model.py', "if ev.result in NON_PASS or ev.result != 'pass':", "if ev.result in NON_PASS:"),
 ('SM02-evidence-for-any-requirement', 'status_model.py', "    if st.requirement_id not in ev.requirement_ids:", "    if False:"),
 ('SM03-build-unchecked', 'status_model.py', "if not st.build or ev.build != st.build:", "if False:"),
 ('SM04-hash-unchecked', 'status_model.py', "if not _SHA.fullmatch(ev.integrity_hash or ''):\n        raise StatusError('NO_INTEGRITY_HASH'", "if False:\n        raise StatusError('NO_INTEGRITY_HASH'"),
 ('SM05-tests-unnamed', 'status_model.py', "if not ev.tests:", "if False:"),
 ('SM06-mock-always-ok', 'status_model.py', "if ev.mock_only and not allow_mock:", "if False:"),
 ('SM07-environment-unchecked', 'status_model.py', "if ev.environment not in envs:", "if False:"),
 ('SM08-kind-unchecked', 'status_model.py', "if ev.kind != kinds:", "if False:"),
 ('SM09-rungs-skippable', 'status_model.py', "if target != nxt:", "if False:"),
 ('SM10-failed-advances', 'status_model.py', "if st.status in (BLOCKED, FAILED):\n        raise StatusError('NOT_ADVANCEABLE'", "if False:\n        raise StatusError('NOT_ADVANCEABLE'"),
 ('SM11-any-approver-specifies', 'status_model.py', "if ev.kind != 'approval' or ev.actor_kind != 'human' or ev.role not in ('product_owner', 'spec_approver'):", "if ev.kind != 'approval':"),
 ('SM12-self-acceptance', 'status_model.py', "if ev.actor == st.builder:", "if False:"),
 ('SM13-acceptance-below-level', 'status_model.py', "        if rank(st.status) < rank(st.required_level):\n            raise StatusError('BELOW_REQUIRED_LEVEL'", "        if False:\n            raise StatusError('BELOW_REQUIRED_LEVEL'"),
 ('SM14-any-reviewer-accepts', 'status_model.py', "if ev.kind != 'review' or ev.actor_kind != 'human' or ev.role != 'authorised_reviewer':", "if ev.kind != 'review':"),
 ('SM15-any-actor-closes', 'status_model.py', "if ev.kind != 'closure' or ev.actor_kind != 'human' or ev.role != 'closure_authority' or not ev.reason:", "if ev.kind != 'closure':"),
 ('SM16-mandatory-tests-ignored', 'status_model.py', "missing = [t for t in st.mandatory_tests if t not in seen]", "missing = []"),
 ('SM17-gates-ignored', 'status_model.py', "if rank(st.required_level) >= r and k not in kinds:", "if False:"),
 ('SM18-build-change-keeps-status', 'status_model.py', "return replace(st, status='Implemented', build=new_build", "return replace(st, status=st.status, build=new_build"),
 ('SM19-recovery-evidence-stale-ok', 'status_model.py', "if ev.build != st.build or not _SHA.fullmatch(ev.integrity_hash or ''):\n        raise StatusError('STALE_OR_DIFFERENT_BUILD', 'recovery", "if False:\n        raise StatusError('STALE_OR_DIFFERENT_BUILD', 'recovery"),
 ('SM20-recovery-jumps-to-top', 'status_model.py', "return replace(st, status=st.last_good, blocked_reason=''", "return replace(st, status='Closed', blocked_reason=''"),
 ('SM21-failure-needs-no-fail', 'status_model.py', "if st.requirement_id not in ev.requirement_ids or ev.result != 'fail':", "if False:"),
 ('SM22-block-without-reason', 'status_model.py', "if not reason or not next_action:", "if False:"),
 ('SM23-integration-without-components', 'status_model.py', "if not ev.components:", "if False:"),
 ('SM24-implemented-without-record', 'status_model.py', "if ev.kind != 'implementation' or not ev.build:", "if False:"),
 ('SM25-mock-local-refused', 'status_model.py', "_run_checks(ev, st, 'test_run', LOCAL_ENVS, True)", "_run_checks(ev, st, 'test_run', LOCAL_ENVS, False)"),
 ('SM26-required-level-unchecked', 'status_model.py', "if required_level not in LADDER[2:6]:", "if False:"),
 ('SM27-closure-counts-other-builds', 'status_model.py', "if e.build == st.build and e.result == 'pass' and e.kind in", "if e.kind in"),
 ('SM28-actor-kind-unchecked', 'status_model.py', "if ev.actor_kind not in ('human', 'ai', 'service'):", "if False:"),
 ('SM29-ref-and-actor-optional', 'status_model.py', "if not ev.ref or not ev.actor:", "if False:"),
 ('SM30-same-build-demotes', 'status_model.py', "if new_build == st.build:\n        return st", "if False:\n        return st"),
 ('SM31-recover-from-good-state', 'status_model.py', "if st.status not in (BLOCKED, FAILED):\n        raise StatusError('NOT_BLOCKED_OR_FAILED')", "if False:\n        raise StatusError('NOT_BLOCKED_OR_FAILED')"),
 ('SM32-last-good-lost', 'status_model.py', "return replace(st, status=FAILED, last_good=st.last_good or st.status", "return replace(st, status=FAILED, last_good=''"),
 ('SM33-closure-build-unchecked', 'status_model.py', "        if ev.build != st.build:\n            raise StatusError('STALE_OR_DIFFERENT_BUILD', 'closure", "        if False:\n            raise StatusError('STALE_OR_DIFFERENT_BUILD', 'closure"),
 ('SM34-acceptance-build-unchecked', 'status_model.py', "        if ev.build != st.build:\n            raise StatusError('STALE_OR_DIFFERENT_BUILD', 'review", "        if False:\n            raise StatusError('STALE_OR_DIFFERENT_BUILD', 'review"),
 ('SM35-unknown-status-passes', 'status_model.py', "if target not in LADDER:", "if False:"),
 ('SM36-history-not-kept', 'status_model.py', "history=st.history + ((st.status, target, ev.ref),), last_good=target", "history=st.history, last_good=target"),
 # ---- reproducibility
 ('RP01-input-hash-unchecked', 'repro.py', "if rec.payload_hash != r.payload_hash or digest(rec.payload) != r.payload_hash:", "if False:"),
 ('RP02-store-hash-trusted', 'repro.py', " or digest(rec.payload) != r.payload_hash", ""),
 ('RP03-formula-version-reuse', 'repro.py', "if old is not None and old[1] != h:", "if False:"),
 ('RP04-nondeterminism-ignored', 'repro.py', "if ca != cb:", "if False:"),
 ('RP05-rerun-overwrites', 'repro.py', "    if existing is not None:", "    if False:"),
 ('RP06-stored-result-unchecked', 'repro.py', "if digest(p['result']) != p['result_hash']:", "if False:"),
 ('RP07-stored-params-unchecked', 'repro.py', "if digest(p['params']) != p['params_hash']:", "if False:"),
 ('RP08-run-key-unchecked', 'repro.py', "if digest(body)[:32] != p['run_key'] or p['run_key'] != run_key:", "if False:"),
 ('RP09-formula-drift-ignored', 'repro.py', "if code_hash != p['formula_code_hash']:", "if False:"),
 ('RP10-result-difference-ignored', 'repro.py', "if digest(again) != p['result_hash']:", "if False:"),
 ('RP11-duplicate-inputs-ok', 'repro.py', "if len({(r.kind, r.key) for r in refs}) != len(refs):", "if False:"),
 ('RP12-no-inputs-ok', 'repro.py', "    if not refs:", "    if False:"),
 ('RP13-formula-sees-live-inputs', 'repro.py', "a = fn(deep_copy(inputs), deep_copy(params))", "a = fn(inputs, deep_copy(params))"),
 ('RP14-drift-includes-equal', 'repro.py', "latest.revision > i['revision']", "latest.revision >= i['revision']"),
 ('RP15-version-zero-ok', 'repro.py', "or version < 1:", "or version < 0:"),
 ('RP16-float-result-ok', 'repro.py', "    except CanonError as e:\n        raise ReproError('RESULT_NOT_CANONICAL', str(e))", "    except CanonError as e:\n        return deep_copy({})"),
 ('RP17-latest-pinned-wrongly', 'repro.py', "return InputRef(kind, key, rec.revision, rec.payload_hash)", "return InputRef(kind, key, rec.revision + 1, rec.payload_hash)"),
 ('RP18-created-by-dropped', 'repro.py', "created_by=scoped.ctx.user_id", "created_by=''"),
 # ---- materiality engine
 ('ME01-ai-records-decisions', 'materiality_engine.py', "    if ctx.actor_kind != 'human':\n        raise PolicyError('HUMAN_REQUIRED'", "    if False:\n        raise PolicyError('HUMAN_REQUIRED'"),
 ('ME02-anyone-records-decisions', 'materiality_engine.py', "if not _has(ctx, 'product_owner'):", "if False:"),
 ('ME03-self-approval', 'materiality_engine.py', "if ctx.user_id == p['proposer']:", "if False:"),
 ('ME04-roleless-approval', 'materiality_engine.py', "    if role is None:", "    if False:"),
 ('ME05-approval-not-bound-to-content', 'materiality_engine.py', "if a['policy_digest'] != p['policy_digest'] or", "if False or"),
 ('ME06-approval-key-unchecked', 'materiality_engine.py', " or key_rec.key != f\"{version}|{a['approver']}\"", ""),
 ('ME07-approval-not-bound-to-change', 'materiality_engine.py', " or a.get('against') != (old_version or '')", ""),
 ('ME08-first-policy-compared-to-itself', 'materiality_engine.py', "old_policy = old if old is not None else baseline_policy()", "old_policy = old if old is not None else p['policy']"),
 ('ME09-activation-not-compare-and-set', 'materiality_engine.py', "                   expected_revision=rev)", "                   expected_revision=None)"),
 ('ME10-stored-policy-unchecked', 'materiality_engine.py', "if digest(p['policy']) != p['policy_digest'] or p['policy'].get('version') != version:", "if False:"),
 ('ME11-active-pointer-unchecked', 'materiality_engine.py', "if cur.payload['policy_digest'] != p['policy_digest']:", "if False:"),
 ('ME12-versions-overwritable', 'materiality_engine.py', "scoped.put(POLICY_KIND, policy['version'], payload, expected_revision=0)", "scoped.put(POLICY_KIND, policy['version'], payload)"),
 ('ME13-different-content-same-version', 'materiality_engine.py', "if existing.payload['policy_digest'] == payload['policy_digest']:", "if True:"),
 ('ME14-invalid-rule-proposed', 'materiality_engine.py', "if M._rule_state(rule)[0] == 'invalid':", "if False:"),
 ('ME15-no-policy-not-material', 'materiality_engine.py', "result = {'material': True, 'reasons': [NO_ACTIVE]", "result = {'material': False, 'reasons': [NO_ACTIVE]"),
 ('ME16-open-decisions-hidden', 'materiality_engine.py', "open_d = [d for d in decisions_relied_on(policy) if status[d] == 'open']", "open_d = []"),
 ('ME17-unset-rule-no-dependency', 'materiality_engine.py', "        if st == 'unset':\n            deps.add('DEC-A1-1')", "        if st == 'unset':\n            pass"),
 ('ME18-all-records-no-dependency', 'materiality_engine.py', "        if st == 'all':\n            deps.add('DEC-A1-3')", "        if st == 'all':\n            pass"),
 ('ME19-two-measures-no-dependency', 'materiality_engine.py', ">= 2:\n            deps.add('DEC-A1-4')", ">= 3:\n            deps.add('DEC-A1-4')"),
 ('ME20-always-list-no-dependency', 'materiality_engine.py', "    if policy.get('always_material'):\n        deps.add('DEC-A1-2')", "    if False:\n        deps.add('DEC-A1-2')"),
 ('ME21-aggregation-no-dependency', 'materiality_engine.py', "    if 'aggregation' in policy or not policy.get('aggregate', True):\n        deps.add('DEC-A1-8')", "    if False:\n        deps.add('DEC-A1-8')"),
 ('ME22-unknown-becomes-zero', 'materiality_engine.py', "    if isinstance(v, Unknown):\n        return None", "    if isinstance(v, Unknown):\n        return 0"),
 ('ME23-bases-not-normalised', 'materiality_engine.py', "r['bases'] = {k: _num(v) for k, v in r['bases'].items()}", "pass"),
 ('ME24-record-unscreened', 'materiality_engine.py', "rec, _ = screen_payload(ctx, normalise(record), scoped._audit)", "rec = normalise(record)"),
 ('ME25-candidates-unscreened', 'materiality_engine.py', "cc, _ = screen_payload(ctx, normalise(c), scoped._audit)", "cc = normalise(c)"),
 ('ME26-verify-inputs-unchecked', 'materiality_engine.py', "if digest({'policy': s['policy_digest'], 'record': s['record'], 'candidates': s['candidates']})[:32] != key:", "if False:"),
 ('ME27-verify-result-unchecked', 'materiality_engine.py', "return (True, '') if digest(again) == digest(s['result']) else (False, 'RESULT_DIFFERS')", "return (True, '')"),
 ('ME28-verify-policy-unchecked', 'materiality_engine.py', "        if p['policy_digest'] != s['policy_digest']:", "        if False:"),
 ('ME29-key-ignores-policy', 'materiality_engine.py', "key = digest({'policy': pol_digest, 'record': rec, 'candidates': cands})[:32]", "key = digest({'record': rec, 'candidates': cands})[:32]"),
 ('ME30-ai-approves', 'materiality_engine.py', "_need_human(ctx, 'approval')", "pass"),
 ('ME31-decision-incomplete-ok', 'materiality_engine.py', "if not isinstance(outcome, str) or not outcome.strip() or not isinstance(rationale, str) or not rationale.strip():", "if False:"),
 ('ME32-unknown-decision-ok', 'materiality_engine.py', "if decision_id not in DECISIONS:", "if False:"),
 ('ME33-activation-unchecked', 'materiality_engine.py', "    if not ok:\n        scoped.log('policy.activation_refused'", "    if False:\n        scoped.log('policy.activation_refused'"),
 ('ME34-unstorable-input-trusted', 'materiality_engine.py', "        replayable = False\n", "        replayable = True\n"),
 ('ME35-decision-ledger-by-presence', 'materiality_engine.py', "'decided' if (r is not None and r.payload.get('decided_by')) else 'open'", "'decided' if r is not None else 'open'"),
 ('ME36-invalid-policy-proposed', 'materiality_engine.py', "    if not M.policy_valid(policy):\n        raise PolicyError('POLICY_INVALID'", "    if False:\n        raise PolicyError('POLICY_INVALID'"),
]

# Mutants that cannot change observable behaviour, with the reason.  Anything else that survives is a test gap.
EQUIV = {
 'ME35-decision-ledger-by-presence': "the only writer of the ledger kind in this package is record_decision, which always stores decided_by; a direct store write is outside the engine and is recorded as handoff item EDR-20 (write authorisation by record kind).",
 'CA01-float-allowed': "a float then reaches the final 'unsupported type' branch of _check and is still refused with CanonError; only the message differs.",
 'RI13-input-aliased': "_mk deep-copies the payload again before it is stored, so a caller's object is never held; the first copy is redundant defence.",
}


def run_one(item, tmp):
    mid, fname, old, new = item
    path = os.path.join(ROOT, 'apg', fname)
    src = open(path, encoding='utf-8').read()
    if src.count(old) < 1:
        return mid, 'ERROR', f'pattern not found in {fname}'
    work = os.path.join(tmp, mid)
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns('logs', '__pycache__', '.git', 'dist'))
    open(os.path.join(work, 'apg', fname), 'w', encoding='utf-8').write(src.replace(old, new, 1))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for cmd in ([sys.executable, '-I', 'tools/run_m2_tests.py', '-q', '--failfast'], [sys.executable, '-I', 'tools/run_contracts.py']):
        try:
            r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return mid, 'KILLED', 'timeout'
        if r.returncode != 0:
            return mid, 'KILLED', 'tests' if 'run_m2_tests' in cmd[2] else 'contracts'
    return mid, 'SURVIVED', ''


def main():
    ids = [m[0] for m in MUT]
    if len(set(ids)) != len(ids):
        print('ERROR duplicate mutant ids'); return 2
    if '--list' in sys.argv:
        print('\n'.join(ids)); return 0
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 4
    tmp = tempfile.mkdtemp(prefix='m2_mut_')
    try:
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(lambda m: run_one(m, tmp), MUT))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    killed = equiv = 0; unexplained = []; by_tests = by_contracts = 0
    for mid, st, info in results:
        if st == 'ERROR':
            print(f'ERROR {mid}: {info}'); return 2
        if st == 'KILLED':
            killed += 1; by_tests += info == 'tests'; by_contracts += info == 'contracts'; print(f'KILLED     {mid}  (by {info})')
        elif mid in EQUIV and EQUIV[mid]:
            equiv += 1; print(f'EQUIVALENT {mid}  -- {EQUIV[mid]}')
        else:
            unexplained.append(mid); print(f'SURVIVED   {mid}')
    print(f'mutants {len(MUT)}  killed {killed} (tests {by_tests}, contracts {by_contracts})  documented-equivalent {equiv}  unexplained survivors {len(unexplained)}')
    if unexplained:
        print('UNEXPLAINED:', unexplained); return 1
    print('MUTATION RUN OK'); return 0


if __name__ == '__main__':
    sys.exit(main())
