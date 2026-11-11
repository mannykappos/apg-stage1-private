"""A corpus of deliberately faulty files, each with the outcome the pipeline MUST give.  Deterministic.  Synthetic.
The cases use the Builder Zero accounting invoice layout (TPL-BZ-AP-INVOICES) so the expectations are easy to read.  Amir can run the same corpus against the Engine's
own import path.  Expectation forms:
  {'file_rejected': CODE}                          the whole file is refused
  {'tenant_refused': True}                         a tenant claim naming another tenant: the whole file is refused and audited
  {'rows': {row_no: ('rejected', CODE) | ('stored', outcome, CODE_or_None)}, 'receipt_rows': n}   row_no counts data rows from 1;
          outcome is the intrinsic outcome of a stored row; CODE (if given) must appear among its pending or warning codes."""
import csv, io

HEADER = ['invoice_id', 'supplier_id', 'supplier_invoice_no', 'project_id', 'cost_code', 'po_id', 'invoice_date', 'ex_gst_cents', 'gst_cents', 'status', 'source_batch']
GOOD = ['INV-9001', 'SUP-001', 'SI-1001', 'PRJ-001', 'CC-01', 'PO-0001', '2026-05-01', '1000000', '100000', 'posted', 'B-corpus-1']


def _csv(rows, header=HEADER, delim=',', newline='\n'):
    b = io.StringIO()
    w = csv.writer(b, delimiter=delim, lineterminator=newline)
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return b.getvalue()


def _row(**kw):
    r = list(GOOD)
    for k, v in kw.items():
        r[HEADER.index(k)] = v
    return r


def cases():
    C = []

    def add(cid, desc, data, expect, limits=None):
        C.append({'id': cid, 'desc': desc, 'data': data if isinstance(data, bytes) else data.encode('utf-8'), 'expect': expect, 'limits': limits})
    ok = _csv([GOOD])
    # ---- whole-file refusals
    add('F01', 'empty file', b'', {'file_rejected': 'EMPTY_FILE'})
    add('F02', 'binary content (NUL byte)', ok.encode() + b'\x00', {'file_rejected': 'NUL_BYTE'})
    add('F03', 'not valid UTF-8', b'invoice_id,supplier_id\n\xff\xfe,SUP-001\n', {'file_rejected': 'ENCODING'})
    add('F04', 'a mapped column is missing from the header', _csv([GOOD[:7]], HEADER[:7]), {'file_rejected': 'MISSING_COLUMNS'})
    add('F05', 'a column name appears twice', _csv([GOOD + ['x']], HEADER + ['invoice_id']), {'file_rejected': 'DUPLICATE_HEADER'})
    add('F06', 'a quoted cell is never closed', ok + 'INV-9002,"SUP-001,SI-1,PRJ-001,CC-01,,2026-05-01,5,5,posted,B\n', {'file_rejected': 'MALFORMED_CSV'})
    add('F07', 'file larger than the allowed size', ok, {'file_rejected': 'FILE_TOO_LARGE'}, limits={'max_bytes': 50})
    add('F08', 'more rows than allowed', _csv([GOOD, _row(invoice_id='INV-9002'), _row(invoice_id='INV-9003')]), {'file_rejected': 'TOO_MANY_ROWS'}, limits={'max_rows': 2})
    add('F09', 'a byte-order mark makes the first column name wrong', '﻿' + ok, {'file_rejected': 'MISSING_COLUMNS'})
    add('F10', 'semicolon-separated file', _csv([GOOD], delim=';'), {'file_rejected': 'MISSING_COLUMNS'})
    add('F11', 'header only, no data rows: a valid empty delivery, recorded', _csv([]), {'rows': {}, 'receipt_rows': 0})
    # ---- row-level rejections
    bad = {
        'R01': ('row with too few cells', None, 'RAGGED_ROW'), 'R02': ('row with too many cells', None, 'RAGGED_ROW'),
        'R03': ('required identifier blank', _row(invoice_id=''), 'REQUIRED_MISSING'), 'R04': ('money with a decimal point in a cents file', _row(ex_gst_cents='12.5'), 'INVALID_MONEY'),
        'R05': ('money in scientific notation', _row(ex_gst_cents='1e6'), 'INVALID_MONEY'), 'R06': ('Arabic-Indic digits', _row(ex_gst_cents='١٢٣'), 'INVALID_MONEY'),
        'R07': ('a date that does not exist', _row(invoice_date='2026-02-30'), 'INVALID_DATE'), 'R08': ('day/month/year in an ISO column', _row(invoice_date='13/05/2026'), 'INVALID_DATE'),
        'R09': ('unpadded date (not exactly the template format)', _row(invoice_date='2026-5-3'), 'INVALID_DATE'), 'R10': ('zero-width space inside an identifier', _row(invoice_id='INV-9​010'), 'HIDDEN_CHARACTER'),
        'R11': ('non-breaking hyphen makes a look-alike identifier', _row(invoice_id='INV‑9011'), 'NON_ASCII_IDENTIFIER'), 'R12': ('full-width digits in an identifier', _row(invoice_id='INV-９０１２'), 'NON_ASCII_IDENTIFIER'),
        'R13': ('control character in a text cell', _row(supplier_invoice_no='SI\x07-1'), 'HIDDEN_CHARACTER'), 'R14': ('amount beyond the accepted range', _row(ex_gst_cents='99999999999999999'), 'OUT_OF_RANGE'),
        'R15': ('date before the accepted range', _row(invoice_date='1899-01-01'), 'DATE_OUT_OF_RANGE'), 'R16': ('absurdly long cell', _row(supplier_invoice_no='S' * 6000), 'CELL_TOO_LONG'),
        'R17': ('required amount blank', _row(ex_gst_cents=''), 'REQUIRED_MISSING'), 'R18': ('amount given with a currency symbol in a cents file', _row(ex_gst_cents='$100'), 'INVALID_MONEY'),
    }
    for cid, (desc, row, code) in bad.items():
        if cid == 'R01':
            data = _csv([GOOD]) + 'INV-9002,SUP-001,SI-2\n'
        elif cid == 'R02':
            data = _csv([GOOD]) + ','.join(_row(invoice_id='INV-9002')) + ',extra,cells\n'
        else:
            data = _csv([GOOD, row])
        add(cid, desc, data, {'rows': {1: ('stored', 'accepted', None), 2: ('rejected', code)}})
    # ---- stored, but held or warned
    add('H01', 'optional amount is not a number: stored, unknown, held', _csv([_row(gst_cents='abc')]), {'rows': {1: ('stored', 'pending_reconciliation', 'INVALID_VALUE:gst_cents:INVALID_MONEY')}})
    add('H02', 'negative invoice amount: sign convention', _csv([_row(ex_gst_cents='-500')]), {'rows': {1: ('stored', 'pending_reconciliation', 'SIGN_CONVENTION:amount_ex_gst_cents')}})
    add('H03', 'zero invoice amount', _csv([_row(ex_gst_cents='0')]), {'rows': {1: ('stored', 'pending_reconciliation', 'SIGN_CONVENTION:amount_ex_gst_cents')}})
    add('H04', 'invoice dated after the day it was received', _csv([_row(invoice_date='2031-01-01')]), {'rows': {1: ('stored', 'pending_reconciliation', 'FUTURE_DATED:invoice_date')}})
    add('H05', 'blank GST: stays unknown (never zero)', _csv([_row(gst_cents='')]), {'rows': {1: ('stored', 'accepted_with_warnings', 'VALUE_MISSING:gst_cents')}})
    add('H06', 'spreadsheet formula in a text cell: kept as text, flagged', _csv([_row(supplier_invoice_no='=HYPERLINK("x")')]), {'rows': {1: ('stored', 'accepted_with_warnings', 'FORMULA_PREFIX:supplier_invoice_number')}})
    add('H07', 'blank cost code (a critical value under the default policy)', _csv([_row(cost_code='')]), {'rows': {1: ('stored', 'pending_reconciliation', 'CRITICAL_VALUE_MISSING:cost_code_ref')}})
    add('H08', 'cells padded with spaces are trimmed, nothing else changes', _csv([_row(invoice_id='  INV-9001  ', ex_gst_cents=' 1000000 ')]), {'rows': {1: ('stored', 'accepted', None)}})
    add('H09', 'Windows line endings', _csv([GOOD], newline='\r\n'), {'rows': {1: ('stored', 'accepted', None)}})
    add('H10', 'blank lines between rows are skipped and counted', _csv([GOOD]) + '\n\n', {'rows': {1: ('stored', 'accepted', None)}})
    # ---- tenant claims in the file
    add('T01', 'an unmapped column naming the SAME tenant: stripped, row stored', _csv([GOOD + ['zero_one']], HEADER + ['tenant_id']), {'rows': {1: ('stored', 'accepted', None)}, 'stripped': ['tenant_id']})
    add('T02', 'an unmapped column naming ANOTHER tenant', _csv([GOOD + ['zero_two']], HEADER + ['Tenant ID']), {'tenant_refused': True})
    add('T03', 'JSON text hidden in a cell naming another tenant', _csv([_row(supplier_invoice_no='{"tenantId": "zero_two"}')]), {'tenant_refused': True})
    add('T04', 'organisation column naming another tenant', _csv([GOOD + ['zero_two']], HEADER + ['org_id']), {'tenant_refused': True})
    add('T05', 'a tenant claim only in the SECOND row', _csv([GOOD + ['zero_one'], _row(invoice_id='INV-9002') + ['zero_two']], HEADER + ['tenant_id']), {'tenant_refused': True})
    return C


def check_case(case, scoped, clock, template, policy, ingest_file, Limits, TenantMismatch):
    """Run one case in the given tenant-scoped world.  -> (ok, message).  The caller supplies the functions so this module has no import cycle and Amir can pass his own."""
    from dataclasses import replace
    e, pol = case['expect'], policy
    if case['limits']:
        pol = replace(policy, limits=replace(Limits(), **case['limits']))
    before = len(scoped.query('ap_invoice'))
    try:
        rec = ingest_file(scoped, clock, template, case['data'], 'accounting', case['id'] + '.csv', pol)
    except TenantMismatch:
        return (e.get('tenant_refused') is True and len(scoped.query('ap_invoice')) == before, 'tenant claim refused' if e.get('tenant_refused') else 'unexpected tenant refusal')
    if 'tenant_refused' in e:
        return False, 'a foreign tenant claim was NOT refused'
    if 'file_rejected' in e:
        return (rec.get('status') == 'file_rejected' and rec.get('code') == e['file_rejected'] and len(scoped.query('ap_invoice')) == before, f'got {rec.get("status")} {rec.get("code")}')
    if rec.get('status') != 'ingested':
        return False, f'file not ingested: {rec}'
    res = {r['row']: r for r in rec['results']}
    if 'receipt_rows' in e and rec['counts']['rows'] != e['receipt_rows']:
        return False, f'row count {rec["counts"]["rows"]}'
    for n, want in e['rows'].items():
        got = res.get(n)
        if got is None:
            return False, f'row {n} missing from the receipt'
        if want[0] == 'rejected':
            if got['result'] != 'rejected' or want[1] not in got['codes']:
                return False, f'row {n}: wanted rejected {want[1]}, got {got}'
        else:
            if got['result'] not in ('new', 'revision'):
                return False, f'row {n}: wanted stored, got {got}'
            rc = scoped.get('ap_invoice', got['key'])
            outcome = rc.payload['intrinsic']['outcome']
            codes = rc.payload['intrinsic']['pending'] + rc.payload['intrinsic']['warnings']
            if outcome != want[1] or (want[2] and want[2] not in codes):
                return False, f'row {n}: wanted {want[1]} {want[2]}, got {outcome} {codes}'
    if 'stripped' in e and rec['stripped_scope_columns'] != e['stripped']:
        return False, f'stripped columns {rec["stripped_scope_columns"]}'
    stored = len(scoped.query('ap_invoice')) - before
    if stored != rec['counts']['new'] + rec['counts']['revision'] - 0 and stored != rec['counts']['new']:
        return False, f'stored {stored} records but the receipt says {rec["counts"]}'
    return True, 'ok'
