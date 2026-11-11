"""Canonical JSON and hashing used by every record in APG.  Floats and NaN are refused: money is integer cents."""
import hashlib, json, unicodedata


class CanonError(ValueError):
    pass


def _check(obj, path='$'):
    if obj is None or isinstance(obj, (str, bool)):
        return
    if isinstance(obj, int):
        return
    if isinstance(obj, float):
        raise CanonError(f'float not allowed at {path} (money and quantities are integers)')
    if isinstance(obj, (list, tuple)):
        for i, x in enumerate(obj):
            _check(x, f'{path}[{i}]')
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise CanonError(f'non-string key at {path}')
            _check(v, f'{path}.{k}')
        return
    raise CanonError(f'unsupported type {type(obj).__name__} at {path}')


def canonical(obj):
    """Deterministic JSON text.  Raises CanonError for floats, NaN, non-string keys or unsupported types."""
    _check(obj)
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def digest(obj):
    return hashlib.sha256(canonical(obj).encode('ascii')).hexdigest()


def deep_copy(obj):
    """Independent copy of a JSON-able object (so callers can never alias stored state)."""
    return json.loads(canonical(obj))


def norm_key(k):
    """Normalise a key for claim detection: NFKC, remove invisible format/control characters, lower-case, unify separators."""
    s = unicodedata.normalize('NFKC', k)
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat in ('Cf', 'Cc'):
            continue                    # zero-width and control characters are dropped
        out.append('_' if cat in ('Zs', 'Zl', 'Zp') or ch in '-.' else ch)
    return ''.join(out).lower()
