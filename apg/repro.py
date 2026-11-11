"""Reproducibility records.  Blueprint: Section 05 section 13.

A calculation is reproducible only if three things are pinned and can be re-checked:
  1. the exact INPUT revisions it read (kind, key, revision number and payload hash) - never "the latest";
  2. the FORMULA that ran (id, version and a hash of its code) - the same id+version can never silently mean different code;
  3. the PARAMETERS (canonical, hashed) and the RESULT (canonical, hashed).
run() writes a record into the tenant's own store.  replay() rebuilds the inputs from their pinned revisions, re-checks every hash, re-runs the
formula and says exactly what drifted.  Later revisions of an input never change an old calculation; drift_report() lists them so a person can decide."""
import hashlib, inspect
from dataclasses import dataclass
from .canon import canonical, digest, deep_copy, CanonError

KIND = 'repro_record'


class ReproError(ValueError):
    def __init__(self, code, msg=''):
        super().__init__(f'{code}: {msg}')
        self.code = code


@dataclass(frozen=True)
class InputRef:
    kind: str
    key: str
    revision: int
    payload_hash: str

    def as_dict(self):
        return {'kind': self.kind, 'key': self.key, 'revision': self.revision, 'payload_hash': self.payload_hash}


def pin_latest(scoped, kind, key):
    """Pin the CURRENT latest revision of an input.  Raises if it does not exist."""
    rec = scoped.get(kind, key)
    if rec is None:
        raise ReproError('INPUT_MISSING', f'{kind}/{key}')
    return InputRef(kind, key, rec.revision, rec.payload_hash)


def _code_hash(fn):
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        src = repr(fn.__code__.co_code) + repr(fn.__code__.co_consts)
    return hashlib.sha256(src.encode('utf-8')).hexdigest()


class FormulaRegistry:
    """Maps (formula id, version) to one function.  A version is immutable: registering different code under an existing id+version is refused."""
    def __init__(self):
        self._f = {}

    def register(self, formula_id, version, fn, code_hash=None):
        if not formula_id or not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ReproError('BAD_FORMULA_ID', 'formula id and a positive integer version are required')
        h = code_hash or _code_hash(fn)
        old = self._f.get((formula_id, version))
        if old is not None and old[1] != h:
            raise ReproError('FORMULA_VERSION_REUSED', f'{formula_id} v{version} already registered with different code; bump the version')
        self._f[(formula_id, version)] = (fn, h)
        return h

    def get(self, formula_id, version):
        if (formula_id, version) not in self._f:
            raise ReproError('FORMULA_UNKNOWN', f'{formula_id} v{version}')
        return self._f[(formula_id, version)]


@dataclass(frozen=True)
class ReplayResult:
    ok: bool
    code: str            # '' when ok
    detail: str = ''


def _load(scoped, refs):
    out = {}
    for r in refs:
        rec = scoped.get(r.kind, r.key, r.revision)
        if rec is None:
            raise ReproError('INPUT_REVISION_MISSING', f'{r.kind}/{r.key} r{r.revision}')
        if rec.payload_hash != r.payload_hash or digest(rec.payload) != r.payload_hash:
            raise ReproError('INPUT_HASH_MISMATCH', f'{r.kind}/{r.key} r{r.revision} no longer matches the pinned hash')
        out[f'{r.kind}/{r.key}'] = deep_copy(rec.payload)
    return out


def _compute(fn, inputs, params):
    a = fn(deep_copy(inputs), deep_copy(params))
    b = fn(deep_copy(inputs), deep_copy(params))
    try:
        ca, cb = canonical(a), canonical(b)
    except CanonError as e:
        raise ReproError('RESULT_NOT_CANONICAL', str(e))
    if ca != cb:
        raise ReproError('NONDETERMINISTIC', 'the formula gave different results for identical inputs')
    return deep_copy(a)


def run(scoped, registry, clock, formula_id, version, refs, params=None):
    """Execute a registered formula over pinned inputs and store a reproducibility record.  -> the stored record payload (dict)."""
    refs = tuple(refs)
    if not refs:
        raise ReproError('NO_INPUTS', 'a calculation must pin at least one input')
    if len({(r.kind, r.key) for r in refs}) != len(refs):
        raise ReproError('DUPLICATE_INPUT', 'the same input is pinned twice')
    for r in refs:
        if not isinstance(r, InputRef) or not isinstance(r.revision, int) or isinstance(r.revision, bool) or r.revision < 1:
            raise ReproError('BAD_INPUT_REF')
    params = {} if params is None else params
    fn, code_hash = registry.get(formula_id, version)
    inputs = _load(scoped, refs)
    result = _compute(fn, inputs, params)
    body = {'formula_id': formula_id, 'formula_version': version, 'formula_code_hash': code_hash,
            'inputs': [r.as_dict() for r in sorted(refs, key=lambda r: (r.kind, r.key))], 'params': deep_copy(params), 'params_hash': digest(params)}
    run_key = digest(body)[:32]
    existing = scoped.get(KIND, run_key)
    if existing is not None:                      # the same calculation over the same pinned inputs: the first record stands, nothing is overwritten
        return deep_copy(existing.payload)
    payload = dict(body, run_key=run_key, result=result, result_hash=digest(result), created_at=clock.now(), created_by=scoped.ctx.user_id)
    rec = scoped.put(KIND, run_key, payload)
    scoped.log('repro.run', f'{KIND}/{run_key}', 'ok', detail={'formula': f'{formula_id}@{version}', 'result_hash': payload['result_hash']})
    return deep_copy(rec.payload)


def replay(scoped, registry, run_key):
    """Re-run a stored calculation from its pinned inputs.  -> ReplayResult.  Never raises for a reproducibility failure; the code says what drifted."""
    rec = scoped.get(KIND, run_key)
    if rec is None:
        return ReplayResult(False, 'RECORD_MISSING', run_key)
    p = rec.payload
    try:
        if digest(p['result']) != p['result_hash']:
            return ReplayResult(False, 'STORED_RESULT_ALTERED', 'stored result does not match its hash')
        if digest(p['params']) != p['params_hash']:
            return ReplayResult(False, 'STORED_PARAMS_ALTERED', 'stored parameters do not match their hash')
        body = {k: p[k] for k in ('formula_id', 'formula_version', 'formula_code_hash', 'inputs', 'params', 'params_hash')}
        if digest(body)[:32] != p['run_key'] or p['run_key'] != run_key:
            return ReplayResult(False, 'RECORD_ALTERED', 'record body does not match its run key')
        try:
            fn, code_hash = registry.get(p['formula_id'], p['formula_version'])
        except ReproError as e:
            return ReplayResult(False, e.code, str(e))
        if code_hash != p['formula_code_hash']:
            return ReplayResult(False, 'FORMULA_DRIFT', f"{p['formula_id']} v{p['formula_version']} code is not the code that produced this result")
        refs = [InputRef(i['kind'], i['key'], i['revision'], i['payload_hash']) for i in p['inputs']]
        inputs = _load(scoped, refs)
        again = _compute(fn, inputs, p['params'])
    except ReproError as e:
        return ReplayResult(False, e.code, str(e))
    if digest(again) != p['result_hash']:
        return ReplayResult(False, 'RESULT_DIFFERS', 'replay produced a different result')
    return ReplayResult(True, '')


def drift_report(scoped, run_key):
    """-> list of {input, pinned_revision, latest_revision} for inputs that have newer revisions.  Informational: an old calculation stays valid for what it pinned."""
    rec = scoped.get(KIND, run_key)
    if rec is None:
        raise ReproError('RECORD_MISSING', run_key)
    out = []
    for i in rec.payload['inputs']:
        latest = scoped.get(i['kind'], i['key'])
        if latest is not None and latest.revision > i['revision']:
            out.append({'input': f"{i['kind']}/{i['key']}", 'pinned_revision': i['revision'], 'latest_revision': latest.revision})
    return out
