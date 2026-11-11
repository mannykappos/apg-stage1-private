"""Mapping templates applied to a file.  Blueprint: Section 04 sections 8 (structural and semantic validation), 10 (normalisation), 18 (spreadsheet imports).

A template (format apg-mapping-template-1.0, from M1) says which columns mean what.  `apply_template` turns the BYTES of a file into row results:
  * the original text of every cell is kept (`raw`) next to the normalised value (`mapped`);
  * a blank optional cell becomes an UNKNOWN field with a reason; it is never turned into zero, an empty string or a default;
  * a value that does not parse is a problem, never a guess: dollars with more than two decimals are refused rather than rounded, dates must be written
    exactly as the template's format says, hidden characters are refused, and an identifier that is not plain ASCII is refused (look-alike keys);
  * a whole file is refused (FileRejected) when it cannot be read safely: too big, wrong encoding, NUL bytes, malformed quoting, a missing or repeated header.
Problems carry a severity: 'reject' (the row cannot be stored as a record) or 'hold' (store it, but it cannot be used until someone looks).
Standard library only; no clock, no storage."""
import csv, datetime, io, hashlib, json, re, unicodedata
from dataclasses import dataclass, field
from .. import canon

MAPPER_VERSION = 'apg-mapper-1'
TYPES = {'string', 'integer', 'date', 'money_cents', 'decimal', 'enum', 'boolean'}
TRANSFORMS = {'none', 'trim', 'upper', 'parse_date', 'dollars_to_cents'}
TENANT_NAMES = {'tenant_id', 'tenant', 'tenant_ref', 'org_id', 'organisation_id'}
MAX_ABS_CENTS = 10 ** 13
DOLLARS = re.compile(r'\$?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]{1,2})?')
INTEGER = re.compile(r'-?[0-9]+')
DECIMAL = re.compile(r'-?[0-9]+(?:\.[0-9]{1,6})?')


class FileRejected(Exception):
    def __init__(self, code, detail=''):
        super().__init__(f'{code}: {detail}')
        self.code, self.detail = code, detail


@dataclass(frozen=True)
class Limits:
    max_bytes: int = 5_000_000
    max_rows: int = 100_000
    max_cell_chars: int = 5_000
    min_date: str = '1990-01-01'
    max_date: str = '2100-12-31'
    ascii_identifiers: bool = True


@dataclass(frozen=True)
class RowResult:
    row_no: int                 # 1-based number of the data row (the row after the header is 1)
    raw: dict                   # column name -> text exactly as read
    mapped: dict                # target field -> normalised value (str | int | bool); only values that are KNOWN
    unknown: dict               # target field -> reason ('no_data' | 'invalid')
    problems: tuple             # ({'code','field','severity','detail'}, ...)
    warnings: tuple
    natural_key: str
    row_hash: str

    @property
    def rejected(self):
        return any(p['severity'] == 'reject' for p in self.problems)


@dataclass(frozen=True)
class FileParse:
    file_sha256: str
    size: int
    template_id: str
    mapping_version: str          # digest of the template + mapper version: the exact rules used
    header: tuple
    unmapped_columns: tuple
    rows: tuple
    blank_rows: int


def template_digest(t):
    return canon.digest({'template': t, 'mapper': MAPPER_VERSION})


def validate_template(t):
    """-> list of problems (empty = valid).  Same rules as the M1 checker, plus the checks the runtime needs."""
    p = []
    for k in ('format_version', 'template_id', 'status', 'tenant_binding', 'source_category', 'file', 'money', 'natural_key', 'target_entity', 'columns', 'unmapped_columns_policy', 'on_row_error'):
        if k not in t:
            p.append('missing ' + k)
    if p:
        return p
    if t['format_version'] != 'apg-mapping-template-1.0':
        p.append('format_version')
    if t['tenant_binding'] != 'authenticated_context':
        p.append('tenant must come from the authenticated context, never from the file')
    if not str(t['status']).startswith('draft'):
        p.append('status must be a draft until verified against a real export')
    if not re.fullmatch(r'SRC-(0[1-9]|1[0-4])', str(t['source_category'])):
        p.append('source_category')
    if t['money'].get('unit') not in ('cents', 'dollars'):
        p.append('money.unit')
    if not isinstance(t['file'], dict) or t['file'].get('type') != 'csv' or not t['file'].get('delimiter') or len(t['file']['delimiter']) != 1:
        p.append('file must be a csv with a one-character delimiter')
    try:
        'x'.encode(t['file'].get('encoding', ''))
    except (LookupError, TypeError):
        p.append('file.encoding unknown')
    hr = t['file'].get('header_row') if isinstance(t['file'], dict) else None
    if not isinstance(hr, int) or isinstance(hr, bool) or hr < 1:
        p.append('file.header_row must be a whole number of at least 1')
    cols = t['columns']
    if not isinstance(cols, list) or not cols:
        return p + ['columns']
    tf = [c.get('target_field') for c in cols]
    sc = [c.get('source_column') for c in cols]
    if len(set(tf)) != len(tf):
        p.append('duplicate target_field')
    if len(set(sc)) != len(sc):
        p.append('duplicate source_column')
    for c in cols:
        if c.get('type') not in TYPES:
            p.append('type ' + str(c.get('type')))
        if c.get('transform', 'none') not in TRANSFORMS:
            p.append('transform ' + str(c.get('transform')))
        if str(c.get('target_field', '')).lower() in TENANT_NAMES:
            p.append('a column may not set the tenant: ' + str(c.get('target_field')))
        if c.get('type') == 'date' and not c.get('date_format'):
            p.append('date column needs date_format: ' + str(c.get('source_column')))
        if c.get('type') == 'date' and c.get('transform') != 'parse_date':
            p.append('date column needs parse_date')
        if c.get('type') == 'enum' and not c.get('allowed'):
            p.append('enum needs allowed list')
        if c.get('type') == 'money_cents' and t['money']['unit'] == 'dollars' and c.get('transform') != 'dollars_to_cents':
            p.append('dollar file: money column needs dollars_to_cents: ' + str(c.get('source_column')))
        if c.get('type') == 'money_cents' and t['money']['unit'] == 'cents' and c.get('transform') == 'dollars_to_cents':
            p.append('cents file must not convert dollars')
        if c.get('transform') == 'dollars_to_cents' and c.get('type') != 'money_cents':
            p.append('dollars_to_cents only on money_cents')
        if c.get('missing_means', 'unknown_not_zero') != 'unknown_not_zero':
            p.append('missing_means may only be unknown_not_zero (a blank is never zero)')
        if not isinstance(c.get('required'), bool):
            p.append('required must be true or false: ' + str(c.get('source_column')))
    if not isinstance(t['natural_key'], list) or not t['natural_key'] or not set(t['natural_key']) <= set(sc):
        p.append('natural_key must name mapped source columns')
    elif not all(any(c['source_column'] == k and c['required'] for c in cols) for k in t['natural_key']):
        p.append('every natural_key column must be required')
    if not any(c.get('required') for c in cols):
        p.append('no required column')
    return p


def _bad_char(s):
    for ch in s:
        cat = unicodedata.category(ch)
        if cat == 'Cf' or (cat == 'Cc' and ch not in '\t\n\r'):
            return ch
    return None


def _cell(col, text, money_unit, limits):
    """-> (value, problem_code_or_None, detail, warning_or_None).  `text` is already stripped and non-empty."""
    t, tr = col['type'], col.get('transform', 'none')
    if t in ('string', 'enum'):
        v = text.upper() if tr == 'upper' else text
        if t == 'enum' and v not in col['allowed']:
            return None, 'INVALID_ENUM', f'{text!r} is not one of {col["allowed"]}', None
        warn = 'FORMULA_PREFIX' if v[:1] in ('=', '@') or (v[:1] in ('+', '-') and not INTEGER.fullmatch(v)) else None
        return v, None, '', warn
    if t == 'integer' or (t == 'money_cents' and tr != 'dollars_to_cents'):
        if not text.isascii() or not INTEGER.fullmatch(text):
            return None, 'INVALID_INTEGER' if t == 'integer' else 'INVALID_MONEY', f'{text!r} is not a whole number', None
        n = int(text)
        if abs(n) > MAX_ABS_CENTS:
            return None, 'OUT_OF_RANGE', f'{text!r} is outside the accepted range', None
        return n, None, '', None
    if t == 'money_cents':                                       # dollars_to_cents: exact, no rounding
        s = text
        neg = False
        if s.startswith('(') and s.endswith(')'):
            neg, s = True, s[1:-1].strip()
        elif s.startswith('-'):
            neg, s = True, s[1:].strip()
        if not s.isascii() or not DOLLARS.fullmatch(s):
            return None, 'INVALID_MONEY', f'{text!r} is not a dollar amount with at most two decimals', None
        s = s.lstrip('$').replace(',', '')
        whole, _, frac = s.partition('.')
        cents = int(whole) * 100 + int((frac + '00')[:2])
        if cents > MAX_ABS_CENTS:
            return None, 'OUT_OF_RANGE', f'{text!r} is outside the accepted range', None
        return -cents if neg else cents, None, '', None
    if t == 'date':
        fmt = col['date_format']
        try:
            d = datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            return None, 'INVALID_DATE', f'{text!r} does not match {fmt}', None
        if d.strftime(fmt) != text:
            return None, 'INVALID_DATE', f'{text!r} is not written exactly as {fmt}', None
        iso = d.isoformat()
        if not (limits.min_date <= iso <= limits.max_date):
            return None, 'DATE_OUT_OF_RANGE', f'{iso} is outside {limits.min_date}..{limits.max_date}', None
        return iso, None, '', None
    if t == 'decimal':
        if not text.isascii() or not DECIMAL.fullmatch(text):
            return None, 'INVALID_DECIMAL', f'{text!r} is not a decimal with at most six places', None
        return text, None, '', None                               # kept as exact text: floats never enter a record
    if t == 'boolean':
        v = text.lower()
        if v in ('true', 'yes', '1'):
            return True, None, '', None
        if v in ('false', 'no', '0'):
            return False, None, '', None
        return None, 'INVALID_BOOLEAN', f'{text!r} is not a yes/no value', None
    return None, 'INVALID_TYPE', t, None


def apply_template(template, data, limits=None):
    """-> FileParse.  Raises FileRejected for a file that cannot be read safely.  Never raises for a bad ROW: that is a RowResult with problems."""
    limits = limits or Limits()
    probs = validate_template(template)
    if probs:
        raise FileRejected('TEMPLATE_INVALID', '; '.join(probs[:5]))
    if not isinstance(data, (bytes, bytearray)):
        raise FileRejected('NOT_BYTES', 'a file is bytes')
    if len(data) > limits.max_bytes:
        raise FileRejected('FILE_TOO_LARGE', f'{len(data)} bytes')
    if len(data) == 0:
        raise FileRejected('EMPTY_FILE', 'no content')
    if b'\x00' in data:
        raise FileRejected('NUL_BYTE', 'binary content in a text import')
    try:
        text = bytes(data).decode(template['file']['encoding'], errors='strict')
    except UnicodeDecodeError as e:
        raise FileRejected('ENCODING', f'not valid {template["file"]["encoding"]}: {e.reason} at byte {e.start}')
    sha = hashlib.sha256(data).hexdigest()
    try:
        rows = list(csv.reader(io.StringIO(text, newline=''), delimiter=template['file']['delimiter'], strict=True))
    except csv.Error as e:
        raise FileRejected('MALFORMED_CSV', str(e))
    hr = template['file']['header_row']
    if len(rows) < hr:
        raise FileRejected('NO_HEADER', 'the header row is missing')
    header = [h.strip() for h in rows[hr - 1]]
    if len(set(header)) != len(header):
        raise FileRejected('DUPLICATE_HEADER', 'a column name appears twice')
    cols = template['columns']
    missing = [c['source_column'] for c in cols if c['source_column'] not in header]
    if missing:
        raise FileRejected('MISSING_COLUMNS', ', '.join(missing))
    mapped_names = {c['source_column'] for c in cols}
    unmapped = tuple(h for h in header if h not in mapped_names)
    body = rows[hr:]
    if len(body) > limits.max_rows:
        raise FileRejected('TOO_MANY_ROWS', f'{len(body)} rows')
    unit, mver = template['money']['unit'], template_digest(template)
    idx = {h: i for i, h in enumerate(header)}
    out, blank, n = [], 0, 0
    for r in body:
        if not r or all(c.strip() == '' for c in r):
            blank += 1
            continue
        n += 1
        problems, warnings, mapped, unknown = [], [], {}, {}
        if len(r) != len(header):
            raw = {h: (r[i] if i < len(r) else '') for i, h in enumerate(header)}
            for j, extra in enumerate(r[len(header):]):
                raw[f'_extra_{j + 1}'] = extra
            problems.append({'code': 'RAGGED_ROW', 'field': '', 'severity': 'reject', 'detail': f'{len(r)} cells for {len(header)} columns'})
            out.append(RowResult(n, raw, {}, {}, tuple(problems), (), '', canon.digest(raw)))
            continue
        raw = {h: r[idx[h]] for h in header}
        for h, v in raw.items():
            if len(v) > limits.max_cell_chars:
                problems.append({'code': 'CELL_TOO_LONG', 'field': h, 'severity': 'reject', 'detail': f'{len(v)} characters'})
            bad = _bad_char(v)
            if bad is not None:
                problems.append({'code': 'HIDDEN_CHARACTER', 'field': h, 'severity': 'reject', 'detail': f'U+{ord(bad):04X} in {h}'})
        if not problems:
            for c in cols:
                v = raw[c['source_column']].strip()
                tf = c['target_field']
                if v == '':
                    if c['required']:
                        problems.append({'code': 'REQUIRED_MISSING', 'field': tf, 'severity': 'reject', 'detail': f'{c["source_column"]} is blank'})
                    else:
                        unknown[tf] = 'no_data'
                    continue
                val, code, detail, warn = _cell(c, v, unit, limits)
                if code:
                    if c['required']:
                        problems.append({'code': code, 'field': tf, 'severity': 'reject', 'detail': detail})
                    else:
                        unknown[tf] = 'invalid'
                        problems.append({'code': code, 'field': tf, 'severity': 'hold', 'detail': detail})
                    continue
                mapped[tf] = val
                if warn:
                    warnings.append({'code': warn, 'field': tf})
        key = ''
        if not any(p['severity'] == 'reject' for p in problems):
            parts = [raw[k].strip() for k in template['natural_key']]
            key = '|'.join(parts)
            if limits.ascii_identifiers and (not key.isascii() or any(ch.isspace() and ch != ' ' for ch in key)):
                problems.append({'code': 'NON_ASCII_IDENTIFIER', 'field': ','.join(template['natural_key']), 'severity': 'reject', 'detail': 'identifiers must be plain ASCII'})
        out.append(RowResult(n, raw, mapped, unknown, tuple(problems), tuple(warnings), key if not any(p['severity'] == 'reject' for p in problems) else '', canon.digest(raw)))
    return FileParse(sha, len(data), template['template_id'], mver, tuple(header), unmapped, tuple(out), blank)
