"""The specification comparability gate.  Blueprint: Section 08 section 4.1 (mandatory), sections 2 (comparable before cheaper), 5 (AI-assisted extraction follows Section 04 human verification before a
value becomes authoritative), 18 decision 1 (no definitive ranking unless specification and commercial terms are sufficiently comparable; labelled indicative comparisons allowed); PG-MP-AC-02, 03.

Five classes, decided by rules that can be read and tested:

  comparable                  every required attribute met on VERIFIED evidence, and the commercial basis needs no adjustment
  comparable_with_adjustment  as above, but the basis differs in ways the policy can quantify and that are recorded as adjustments (freight added, currency converted, unit converted)
  partially_comparable        nothing FAILS, but something cannot be verified or quantified (the quote's own text is not verified against the register; a landed-cost component is missing; an
                              adjustment cannot be quantified; the basis of a reference price is not recorded): indicative benchmarking only, never a definitive ranking
  not_comparable              a required attribute FAILS, the families differ, or the units cannot be converted: no defensible price comparison
  unverified                  the specification register is missing or not approved, a material or a requirement is not in it or not approved, or a required attribute is unknown on both sides

A FAILURE is enough to block, from any evidence (the catalogue code is enough to show that 32 MPa concrete is not 40 MPa concrete).  A PASS needs verification: the catalogue specification of a material
CODE can vouch for a purchase-order rate (the code on an order is what was ordered) but not for a supplier's quote, whose own text can differ from the code; a quote passes only on attributes read from its
text AND verified by a person other than whoever extracted them.  The system never marks a reading verified itself."""
from . import common as C

CLASSES = ('comparable', 'comparable_with_adjustment', 'partially_comparable', 'not_comparable', 'unverified')
RANKABLE = ('comparable', 'comparable_with_adjustment', 'partially_comparable')
DEFINITIVE_OK = ('comparable', 'comparable_with_adjustment')
UNIT_ATTRIBUTE = 'unit'


def readings(F, quote_key):
    """-> {attribute: reading}.  reading: value text, verified flag, who extracted and verified, record ref and revision.  Held readings are listed under '_held'."""
    out, held = {}, []
    for key in sorted(F.kind('quote_reading')):
        v = C.simple_view(F, 'quote_reading', key, ('quote_ref', 'attribute_name', 'value_text'))
        if v is None:
            continue
        if not C.names_quote(F, 'quote_reading', key, quote_key):
            continue
        if not v['ok']:
            held.append({'ref': v['ref'], 'why': v['why']})
            continue
        f = v['f']
        by, ext = f.get('verified_by'), f.get('extracted_by')
        verified = bool(by and by.strip() and f.get('verified_on') and by != ext)
        out[f['attribute_name']] = {'value': f['value_text'], 'verified': verified, 'extracted_by': ext, 'extractor_kind': f.get('extractor_kind'), 'verified_by': by if verified else None,
                                    'ref': v['ref'], 'revision': v['rev']}
    return out, held


def _value_of(rule, text):
    """Reading text -> comparable value: an integer for at_least / at_most, the trimmed text for exact.  None when a numeric attribute is not a whole number."""
    if rule == 'exact':
        return text.strip()
    t = text.strip()
    return int(t) if t.isascii() and t.isdigit() else None


def _cmp(rule, required, offered):
    if rule == 'exact':
        return str(offered) == str(required)
    if offered is None:
        return None
    return offered >= required if rule == 'at_least' else offered <= required


def attribute_check(spec, req_material, offer_material, offer_readings, offer_kind):
    """-> dict: the spec-only part of the gate.  result per attribute is pass | fail | unknown; `verified` says whether every PASS rests on evidence that may vouch for it."""
    mats = spec['materials']
    rq, of = mats.get(req_material), mats.get(offer_material)
    if rq is None or of is None:
        return {'status': 'unknown', 'family': None, 'attributes': [], 'reasons': ['material %s is not in the specification register' % (req_material if rq is None else offer_material)], 'verified': False}
    if rq['family'] != of['family']:
        return {'status': 'fail', 'family': rq['family'], 'attributes': [], 'reasons': ['different product families (%s and %s)' % (rq['family'], of['family'])], 'verified': False}
    fam = spec['families'][rq['family']]['attributes']
    rows, reasons, verified = [], [], True
    for a in sorted(rq['attributes']):
        rule = fam[a]['match']
        req = rq['attributes'][a]
        cat = of['attributes'].get(a)
        rd = offer_readings.get(a)
        rv = _value_of(rule, rd['value']) if rd is not None else None
        if rd is not None and rv is None:
            rd = None                                              # a numeric attribute that is not a whole number cannot be read
        src, val = None, None
        if rd is not None and rd['verified']:
            src, val = 'verified_reading', rv
            if cat is not None and str(cat) != str(rv) and rule == 'exact':
                reasons.append('attribute %s: the verified reading (%s) disagrees with the catalogue (%s)' % (a, rv, cat))
        elif cat is not None:
            src, val = 'catalogue', cat
        elif rd is not None:
            src, val = 'unverified_reading', rv
        res = None if val is None else _cmp(rule, req, val)
        row = {'attribute': a, 'match': rule, 'required': req, 'offered': val, 'source': src, 'result': 'unknown' if res is None else ('pass' if res else 'fail')}
        if row['result'] == 'pass' and src != 'verified_reading' and not (src == 'catalogue' and offer_kind == 'purchase_order'):
            verified = False
        if row['result'] == 'pass' and src == 'unverified_reading':
            row['result'] = 'unknown'                              # an unverified reading cannot pass anything; it can only be shown
        if row['result'] == 'fail':
            reasons.append('attribute %s: %s offered against %s required (%s)' % (a, val, req, rule))
        elif row['result'] == 'unknown':
            reasons.append('attribute %s cannot be assessed (nothing usable offered)' % a)
        rows.append(row)
    st = 'fail' if any(r['result'] == 'fail' for r in rows) else ('unknown' if any(r['result'] == 'unknown' for r in rows) else 'pass')
    return {'status': st, 'family': rq['family'], 'attributes': rows, 'reasons': reasons, 'verified': verified and st == 'pass'}


def unit_check(spec, req_material, offer_material, offer_readings, master_unit_req, master_unit_offer):
    """-> {'status': same | converted | incompatible | unverified, ...}.  Quotes record no unit: the unit comes from a verified `unit` reading, else it is only INFERRED from the material master."""
    rd = offer_readings.get(UNIT_ATTRIBUTE)
    unit_req = (spec['materials'].get(req_material) or {}).get('unit') or master_unit_req
    verified = rd is not None and rd['verified']
    unit_offer = rd['value'].strip() if verified else ((spec['materials'].get(offer_material) or {}).get('unit') or master_unit_offer)
    if unit_req is None or unit_offer is None:
        return {'status': 'unverified', 'from': unit_offer, 'to': unit_req, 'factor_micro': None, 'inferred': not verified, 'why': 'a unit is not recorded'}
    if unit_req == unit_offer:
        return {'status': 'same' if verified else 'unverified', 'from': unit_offer, 'to': unit_req, 'factor_micro': C.MICRO, 'inferred': not verified,
                'why': '' if verified else 'the quote records no unit and no verified unit reading exists; the unit is inferred from the material master'}
    for c in spec.get('unit_conversions', []):
        if c['material'] in (req_material, offer_material) and c['from_unit'] == unit_offer and c['to_unit'] == unit_req:
            return {'status': 'converted' if verified else 'unverified', 'from': unit_offer, 'to': unit_req, 'factor_micro': c['factor_micro'], 'inferred': not verified,
                    'why': '' if verified else 'conversion declared, but the offered unit is inferred, not verified'}
    return {'status': 'incompatible', 'from': unit_offer, 'to': unit_req, 'factor_micro': None, 'inferred': not verified, 'why': 'no declared conversion from %s to %s' % (unit_offer, unit_req)}


def classify(spec_ok, attr, unit, commercial, req_approved=True, offer_kind='quote'):
    """-> (class, codes, reasons).  spec_ok False means the register is missing or not approved.  commercial: {'adjustments': [...], 'unquantified': [(code, text)]} from the landed-cost step.
    `codes` are stable machine-readable reasons (a rule can tolerate a named one); `reasons` is the same list in words."""
    if not spec_ok:
        return 'unverified', ['SPEC_REGISTER_UNAPPROVED'], ['the specification register is missing or not approved']
    if not req_approved:
        return 'unverified', ['REQUIREMENT_UNAPPROVED'], ['the specification requirement is not approved by a person']
    if attr['status'] == 'fail':
        return 'not_comparable', ['ATTRIBUTE_FAILS'], list(attr['reasons'])
    if unit['status'] == 'incompatible':
        return 'not_comparable', ['UNIT_INCOMPATIBLE'], ['units cannot be converted: ' + unit['why']]
    if attr['status'] == 'unknown':
        return 'unverified', ['ATTRIBUTE_UNKNOWN'], list(attr['reasons'])
    codes, reasons = [], list(attr['reasons'])
    if not attr['verified']:
        codes.append('QUOTE_TEXT_UNVERIFIED')
        reasons.append('the quote text is not verified against the register: required attributes pass only on the catalogue code')
    if unit['status'] == 'unverified':
        codes.append('UNIT_UNVERIFIED')
        reasons.append(unit['why'])
    for code, text in commercial['unquantified']:
        codes.append(code)
        reasons.append(text)
    if codes:
        return 'partially_comparable', codes, reasons
    if commercial['adjustments'] or unit['status'] == 'converted':
        return 'comparable_with_adjustment', [], reasons
    return 'comparable', [], reasons
