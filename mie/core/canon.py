"""Canonical form (MIE1_SPEC section 7.2, MIE-R-29).  UTF-8 JSON; object keys sorted by the UTF-8 bytes of the key; no insignificant whitespace; arrays keep order;
integers in plain decimal; no floats; strings in NFC with only the mandatory escapes; duplicate keys refused at parse.  The same form identifies packs, observations (OB-) and
results (RS-).  RFC 8785 is not adopted (open question MIE-OQ-04)."""
import hashlib, json, unicodedata

MAX_DEPTH = 64


class CanonError(ValueError):
    def __init__(self, what, path='$'):
        super().__init__('%s at %s' % (what, path))
        self.what, self.path = what, path


class FloatSeen:
    """Stands in for a float found while parsing, so that a caller can refuse it with its own code (a float in a pack is an attempt to override a core invariant)."""
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return 'FloatSeen(%s)' % self.text


def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise CanonError('duplicate key %r' % k)
        out[k] = v
    return out


def _refuse_constant(name):
    raise CanonError('non-finite number %s' % name)


def loads(data):
    """bytes -> value.  Refuses invalid UTF-8, duplicate keys and NaN or infinities.  Floats come back as FloatSeen, never as float."""
    if not isinstance(data, (bytes, bytearray)):
        raise CanonError('bytes required')
    try:
        text = bytes(data).decode('utf-8', 'strict')
    except UnicodeDecodeError:
        raise CanonError('not UTF-8')
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_float=FloatSeen, parse_constant=_refuse_constant)
    except CanonError:
        raise
    except (ValueError, RecursionError) as e:
        raise CanonError('not JSON (%s)' % type(e).__name__)


def find_floats(obj, path='$', depth=0):
    """-> the paths of every FloatSeen or float inside obj."""
    if depth > MAX_DEPTH:
        raise CanonError('nesting too deep', path)
    if isinstance(obj, (FloatSeen, float)):
        return [path]
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += find_floats(v, '%s.%s' % (path, k), depth + 1)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out += find_floats(v, '%s[%d]' % (path, i), depth + 1)
    return out


def _str(s, path):
    if unicodedata.normalize('NFC', s) != s:
        raise CanonError('string not in NFC', path)
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif o < 0x20:
            out.append('\\u%04x' % o)
        elif 0xD800 <= o <= 0xDFFF:
            raise CanonError('lone surrogate', path)
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


def _enc(v, path, depth, parts):
    if depth > MAX_DEPTH:
        raise CanonError('nesting too deep', path)
    if v is None:
        parts.append('null')
    elif v is True:
        parts.append('true')
    elif v is False:
        parts.append('false')
    elif isinstance(v, int):
        parts.append(str(v))
    elif isinstance(v, (float, FloatSeen)):
        raise CanonError('float', path)
    elif isinstance(v, str):
        parts.append(_str(v, path))
    elif isinstance(v, (list, tuple)):
        parts.append('[')
        for i, x in enumerate(v):
            if i:
                parts.append(',')
            _enc(x, '%s[%d]' % (path, i), depth + 1, parts)
        parts.append(']')
    elif isinstance(v, dict):
        for k in v:
            if not isinstance(k, str):
                raise CanonError('non-string key', path)
        parts.append('{')
        for i, k in enumerate(sorted(v, key=lambda k: k.encode('utf-8'))):
            if i:
                parts.append(',')
            parts.append(_str(k, path))
            parts.append(':')
            _enc(v[k], '%s.%s' % (path, k), depth + 1, parts)
        parts.append('}')
    else:
        raise CanonError('unsupported type %s' % type(v).__name__, path)


def dumps(obj):
    """value -> canonical bytes."""
    parts = []
    _enc(obj, '$', 0, parts)
    return ''.join(parts).encode('utf-8')


def digest(obj):
    """Lower-case hex SHA-256 over the canonical bytes."""
    return hashlib.sha256(dumps(obj)).hexdigest()


def copy(obj):
    """An independent copy (through the canonical form, so nothing shared survives)."""
    return json.loads(dumps(obj).decode('utf-8'))
