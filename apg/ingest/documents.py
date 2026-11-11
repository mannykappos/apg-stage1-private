"""Documents and AI/OCR extraction.  Blueprint: Section 04 section 12 ("non-negotiable"), PG-DI-AC-07; Section 08 (quotes).

An extracted value is a CLAIM about a document, not a fact.  It is stored with the document hash, the tool and version, the time, where it was read, and whether it is
ambiguous -- and it stays UNVERIFIED until an authorised HUMAN verifies it.  A verifier may confirm a value or correct it; either way their identity, time, the value,
what evidence they looked at and a note are stored.  An ambiguous reading is never resolved by the software: the candidates are shown, the person chooses.
Verification is by role (document_verifier), by humans only (an AI or service actor is refused), and it applies to the document's exact bytes (a changed document needs
a new extraction).
`standin_extract_quote` is a deterministic TEXT parser standing in for a real OCR/AI extraction service, which needs the Engine and a vendor (handoff register EDR-22).
It exists so the control around it can be built and tested; it is not an extraction product and makes no accuracy claim."""
import hashlib, re
from .. import canon
from ..source_authority import AuthorityError, Observation
from ..values import AMBIGUOUS, Known, Unknown

VERIFIER_ROLE = 'document_verifier'
STANDIN_TOOL = 'apg-standin-text-quote-parser-1'
MATERIAL_FIELDS = ('quantity', 'unit_rate_cents', 'valid_until', 'supplier_text')


def _qty(text):
    t = text.strip()
    if re.fullmatch(r'[0-9]+', t):
        return {'candidates': [int(t)], 'ambiguous': False, 'why': ''}
    if re.fullmatch(r'[0-9OolI]+', t) and re.search(r'[0-9]', t) and re.search(r'[OolI]', t):
        fixed = t.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1')
        return {'candidates': [int(fixed)], 'ambiguous': True, 'why': 'letters inside a number (zero or the letter?)'}
    return {'candidates': [], 'ambiguous': True, 'why': 'not readable as a whole number'}


def _rate(text):
    t = text.strip().lstrip('$')
    m = re.fullmatch(r'([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)(?:\.([0-9]+))?', t)
    if not m:
        return {'candidates': [], 'ambiguous': True, 'why': 'not readable as a dollar amount'}
    whole, frac = m.group(1), m.group(2)
    if frac is not None and len(frac) == 3:                       # '2.650': a decimal point (2.65 dollars) or a thousands separator (2,650 dollars)?
        cands = [int(whole.replace(',', '')) * 1000 * 100 + int(frac) * 100]
        if frac[2] == '0':
            cands.insert(0, int(whole.replace(',', '')) * 100 + int(frac[:2]))
        return {'candidates': cands, 'ambiguous': True, 'why': 'decimal point or thousands separator?'}
    if frac is not None and len(frac) > 2:
        return {'candidates': [], 'ambiguous': True, 'why': 'more than two decimals'}
    return {'candidates': [int(whole.replace(',', '')) * 100 + int((frac or '0').ljust(2, '0'))], 'ambiguous': False, 'why': ''}


def standin_extract_quote(text):
    """-> list of extracted fields.  Each: name, text (as read), location, candidates (whole numbers), ambiguous, why."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        line = re.sub(r'\s*\[.*?\]\s*$', '', line)                    # drop the scan annotation in the sample documents
        m = re.match(r'\s*Supplier:\s*(.+)$', line)
        if m:
            out.append({'name': 'supplier_text', 'text': m.group(1).strip(), 'location': f'line {n}', 'candidates': [], 'ambiguous': False, 'why': ''})
        m = re.match(r'\s*Quantity:\s*(\S+)', line)
        if m:
            out.append(dict(name='quantity', text=m.group(1), location=f'line {n}', **_qty(m.group(1))))
        m = re.match(r'\s*(?:Rate|Unit price):\s*(\$?[0-9][0-9,\.]*)', line)
        if m:
            out.append(dict(name='unit_rate_cents', text=m.group(1), location=f'line {n}', **_rate(m.group(1))))
        m = re.match(r'\s*Valid until:\s*(.+)$', line)
        if m:
            out.append({'name': 'valid_until', 'text': m.group(1).strip(), 'location': f'line {n}', 'candidates': [], 'ambiguous': True, 'why': 'a date written as text is not interpreted by the stand-in (day/month order, two-digit year)'})
    return out


def register_extraction(scoped, clock, doc_id, data, fields, tool=STANDIN_TOOL, tool_version='1'):
    """Store the document's hash and the extraction.  Everything starts UNVERIFIED.  Re-registering identical bytes and identical output changes nothing."""
    if not isinstance(data, (bytes, bytearray)):
        raise AuthorityError('a document is bytes')
    rec = {'doc_sha256': hashlib.sha256(data).hexdigest(), 'registered_by': scoped.ctx.user_id, 'registered_at': clock.now(), 'tool': tool, 'tool_version': tool_version,
           'fields': {f['name']: dict(f, verification=None) for f in fields}}
    cur = scoped.get('extracted_document', doc_id)
    if cur is not None:
        if cur.payload['doc_sha256'] != rec['doc_sha256']:
            raise AuthorityError('this document id already holds a different document; register it under a new id')
        same = {n: {k: v for k, v in f.items() if k != 'verification'} for n, f in cur.payload['fields'].items()} == {n: {k: v for k, v in f.items() if k != 'verification'} for n, f in rec['fields'].items()}
        if same:
            return cur
        raise AuthorityError('a different extraction of the same document needs a new document id')
    out = scoped.put('extracted_document', doc_id, rec, expected_revision=0)
    scoped.log('document.extracted', doc_id, 'unverified', reason=tool, detail={'fields': sorted(rec['fields'])})
    return out


def verify_field(scoped, clock, doc_id, name, value, evidence, note):
    """A human document_verifier confirms or corrects one extracted value.  Returns the stored record."""
    ctx = scoped.ctx
    if ctx.actor_kind != 'human' or VERIFIER_ROLE not in ctx.roles:
        scoped.log('document.refused', f'{doc_id}/{name}', 'refused', reason='verification needs a human document_verifier')
        raise AuthorityError('verification needs a human holding the document_verifier role')
    if isinstance(value, bool) or not (isinstance(value, int) or (isinstance(value, str) and value.strip())):
        raise AuthorityError('a verified value must be a whole number (cents or a count) or, for a text field, non-empty text')
    if not isinstance(note, str) or not note.strip() or not isinstance(evidence, str) or not evidence.strip():
        raise AuthorityError('the evidence considered and a note are required')
    cur = scoped.get('extracted_document', doc_id)
    if cur is None or name not in cur.payload['fields']:
        raise AuthorityError('no such extracted field')
    p = canon.deep_copy(cur.payload)
    f = p['fields'][name]
    if f['candidates'] and not isinstance(value, int) or (not f['candidates'] and name in ('quantity', 'unit_rate_cents') and not isinstance(value, int)):
        raise AuthorityError('this field takes a whole number')
    disposition = 'confirmed' if (not f['ambiguous'] and f['candidates'] == [value]) or (not f['candidates'] and not f['ambiguous'] and f['text'] == value) else 'corrected'
    f['verification'] = {'value': value, 'by': ctx.user_id, 'at': clock.now(), 'evidence': evidence, 'note': note, 'disposition': disposition, 'doc_sha256': p['doc_sha256']}
    out = scoped.put('extracted_document', doc_id, p, expected_revision=cur.revision)
    scoped.log('document.verified', f'{doc_id}/{name}', disposition, reason=ctx.user_id)
    return out


def observation(scoped, doc_id, name, source='document_extraction'):
    """The Observation the authority logic needs: origin 'ai_extracted', human_verified only when a person verified THIS value of THIS document."""
    cur = scoped.get('extracted_document', doc_id)
    if cur is None or name not in cur.payload['fields']:
        return Observation(source, Unknown('no_data', 'no such extracted field'), f'extracted_document/{doc_id}/{name}', '', None, origin='ai_extracted', human_verified=False)
    f = cur.payload['fields'][name]
    v = f['verification']
    if v is not None and v['doc_sha256'] == cur.payload['doc_sha256'] and isinstance(v['value'], int):
        return Observation(source, Known(v['value']), f'extracted_document/{doc_id}@{cur.revision}/{name}', v['at'], None, origin='ai_extracted', human_verified=True)
    if len(f['candidates']) == 1 and not f['ambiguous']:
        return Observation(source, Known(f['candidates'][0]), f'extracted_document/{doc_id}@{cur.revision}/{name}', cur.payload['registered_at'], None, origin='ai_extracted', human_verified=False)
    return Observation(source, Unknown(AMBIGUOUS, f['why'] or 'ambiguous reading'), f'extracted_document/{doc_id}@{cur.revision}/{name}', cur.payload['registered_at'], None, origin='ai_extracted', human_verified=False)


def verified_text(scoped, doc_id, name):
    """The text a person verified for a text field of this exact document, or None."""
    cur = scoped.get('extracted_document', doc_id)
    if cur is None or name not in cur.payload['fields']:
        return None
    v = cur.payload['fields'][name]['verification']
    return v['value'] if v is not None and v['doc_sha256'] == cur.payload['doc_sha256'] and isinstance(v['value'], str) else None
