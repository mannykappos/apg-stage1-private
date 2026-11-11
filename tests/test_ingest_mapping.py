import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_ingest import INV_H, csvb, inv, inv_file, tpl
from apg.ingest import mapping as M

T = tpl('TPL-BZ-AP-INVOICES')


def one(row_cells, template=T, header=INV_H):
    fp = M.apply_template(template, csvb(header, [row_cells]))
    return fp.rows[0]


class TestParsing(unittest.TestCase):
    def test_blank_optional_is_unknown_not_zero_or_empty(self):
        r = one(inv(gst=''))
        self.assertNotIn('gst_cents', r.mapped)
        self.assertEqual(r.unknown['gst_cents'], 'no_data')
        self.assertFalse(r.rejected)

    def test_zero_is_a_value_and_blank_is_not(self):
        r = one(inv(gst='0'))
        self.assertEqual(r.mapped['gst_cents'], 0)
        self.assertNotIn('gst_cents', r.unknown)

    def test_required_blank_rejects_the_row(self):
        for col, idx in (('invoice_id', 0), ('supplier_id', 1), ('invoice_date', 6), ('ex_gst_cents', 7)):
            cells = inv(); cells[idx] = '   '
            r = one(cells)
            self.assertTrue(r.rejected, col)
            self.assertIn('REQUIRED_MISSING', [p['code'] for p in r.problems])

    def test_invalid_optional_is_unknown_invalid_and_held_not_rejected(self):
        r = one(inv(gst='12.5'))
        self.assertFalse(r.rejected)
        self.assertEqual(r.unknown['gst_cents'], 'invalid')
        self.assertEqual([p['severity'] for p in r.problems], ['hold'])

    def test_money_in_a_cents_file_must_be_whole_ascii_digits(self):
        for bad in ('1,000', '1.0', '$5', '1e3', '--5', '+5', '5 000', '٥', '', 'NaN', '0x10'):
            cells = inv(ex=bad)
            r = one(cells)
            self.assertTrue(r.rejected or bad == '', bad)

    def test_negative_cents_parse_and_range_is_enforced(self):
        self.assertEqual(one(inv(ex='-500')).mapped['amount_ex_gst_cents'], -500)
        self.assertTrue(one(inv(ex=str(10 ** 13 + 1))).rejected)
        self.assertFalse(one(inv(ex=str(10 ** 13))).rejected)

    def test_dates_must_be_written_exactly_as_the_template_says(self):
        for bad in ('2026-02-30', '2026-5-3', '03/05/2026', '2026/05/03', '20260503', '2026-05-03T00:00', ' ', '1899-12-31', '2101-01-01'):
            self.assertTrue(one(inv(date=bad)).rejected, bad)
        self.assertEqual(one(inv(date='2026-05-03')).mapped['invoice_date'], '2026-05-03')

    def test_leap_day(self):
        self.assertFalse(one(inv(date='2028-02-29')).rejected)
        self.assertTrue(one(inv(date='2027-02-29')).rejected)

    def test_hidden_and_control_characters_reject_the_row_in_any_column(self):
        for ch in ('​', '‮', '﻿', '\x07', '\x1b', '⁠'):
            for idx in (0, 2, 3):
                cells = inv(); cells[idx] = 'A' + ch + 'B'
                self.assertIn('HIDDEN_CHARACTER', [p['code'] for p in one(cells).problems], (repr(ch), idx))

    def test_tab_and_newline_inside_a_quoted_text_cell_are_allowed(self):
        r = one(inv(sin='line1\nline2\tx'))
        self.assertFalse(r.rejected)

    def test_identifiers_must_be_plain_ascii(self):
        for bad in ('INV‑1', 'INV-１', 'INV-1', 'INV 1', 'İNV-1'):
            r = one(inv(invoice_id=bad))
            if bad == 'INV-1':
                self.assertFalse(r.rejected)            # V is plain 'V'
            else:
                self.assertTrue(r.rejected, repr(bad))

    def test_formula_prefix_is_kept_and_flagged_not_executed(self):
        r = one(inv(sin='=1+1'))
        self.assertEqual(r.mapped['supplier_invoice_number'], '=1+1')
        self.assertEqual([w['code'] for w in r.warnings], ['FORMULA_PREFIX'])
        self.assertEqual(r.warnings[0]['field'], 'supplier_invoice_number')

    def test_negative_number_in_text_is_not_flagged_as_formula(self):
        r = one(inv(sin='-12'))
        self.assertEqual(r.warnings, ())

    def test_raw_text_is_preserved_next_to_the_normalised_value(self):
        r = one(inv(ex=' 000123 '))
        self.assertEqual(r.raw['ex_gst_cents'], ' 000123 ')
        self.assertEqual(r.mapped['amount_ex_gst_cents'], 123)

    def test_unmapped_columns_are_reported_and_kept(self):
        fp = M.apply_template(T, csvb(INV_H + ['note'], [inv() + ['hello']]))
        self.assertEqual(fp.unmapped_columns, ('note',))
        self.assertEqual(fp.rows[0].raw['note'], 'hello')

    def test_ragged_rows_are_rejected_with_their_cells_kept(self):
        fp = M.apply_template(T, b','.join(h.encode() for h in INV_H) + b'\nINV-1,SUP-1\nA,B,C,D,E,F,G,H,I,J,K,L,M\n')
        self.assertEqual([r.rejected for r in fp.rows], [True, True])
        self.assertEqual(fp.rows[1].raw['_extra_1'], 'L')

    def test_blank_lines_are_counted_not_rows(self):
        fp = M.apply_template(T, csvb(INV_H, [inv()]) + b'\n,,,,,,,,,,\n')
        self.assertEqual((len(fp.rows), fp.blank_rows), (1, 2))

    def test_row_numbers_count_data_rows(self):
        fp = M.apply_template(T, csvb(INV_H, [inv('INV-1'), inv('INV-2'), inv('INV-3')]))
        self.assertEqual([r.row_no for r in fp.rows], [1, 2, 3])
        self.assertEqual([r.natural_key for r in fp.rows], ['INV-1', 'INV-2', 'INV-3'])

    def test_a_rejected_row_has_no_natural_key(self):
        self.assertEqual(one(inv(date='bad')).natural_key, '')

    def test_file_hash_and_mapping_version_are_stable_and_change_with_content(self):
        a = M.apply_template(T, inv_file(inv())); b = M.apply_template(T, inv_file(inv()))
        c = M.apply_template(T, inv_file(inv(ex='5')))
        self.assertEqual((a.file_sha256, a.mapping_version), (b.file_sha256, b.mapping_version))
        self.assertNotEqual(a.file_sha256, c.file_sha256)
        t2 = copy.deepcopy(T); t2['columns'][0]['transform'] = 'upper'
        self.assertNotEqual(M.apply_template(t2, inv_file(inv())).mapping_version, a.mapping_version)

    def test_enum_boolean_decimal_types(self):
        q = tpl('TPL-BZ-QUOTES')
        H = ['quote_id', 'supplier_id', 'material_id', 'specification', 'issue_date', 'valid_until', 'unit_rate_cents', 'currency', 'fx_rate_used', 'fx_rate_date', 'freight_cents_per_unit',
             'incoterm_delivery_basis', 'lead_time_days', 'price_kind']
        good = ['Q-1', 'SUP-1', 'MAT-1', 'spec', '2026-01-01', '2026-02-01', '1000', 'usd', '0.6612', '2026-01-01', '0', 'FOB', '5', 'quote']
        r = M.apply_template(q, csvb(H, [good])).rows[0]
        self.assertEqual((r.mapped['currency_code'], r.mapped['fx_rate_used']), ('USD', '0.6612'))       # exact text, never a float
        for idx, bad in ((7, 'XXX'), (8, '0.66123456'), (8, '1e-3'), (12, '5.5'), (8, '.5')):
            g = list(good); g[idx] = bad
            self.assertTrue(M.apply_template(q, csvb(H, [g])).rows[0].problems, (idx, bad))


class TestFileLevel(unittest.TestCase):
    def test_refusals(self):
        cases = [(b'', 'EMPTY_FILE'), (b'a,b\x00', 'NUL_BYTE'), (b'\xff\xfe', 'ENCODING'), (b'invoice_id\n1\n', 'MISSING_COLUMNS')]
        for data, code in cases:
            with self.assertRaises(M.FileRejected) as cm:
                M.apply_template(T, data)
            self.assertEqual(cm.exception.code, code)

    def test_not_bytes_and_limits(self):
        with self.assertRaises(M.FileRejected):
            M.apply_template(T, 'text')
        with self.assertRaises(M.FileRejected) as cm:
            M.apply_template(T, inv_file(inv()), M.Limits(max_bytes=10))
        self.assertEqual(cm.exception.code, 'FILE_TOO_LARGE')

    def test_header_row_other_than_one(self):
        t = copy.deepcopy(T); t['file']['header_row'] = 3
        data = b'junk line\nmore junk\n' + inv_file(inv())
        self.assertEqual(len(M.apply_template(t, data).rows), 1)
        with self.assertRaises(M.FileRejected):
            M.apply_template(t, b'only one line\n')

    def test_encoding_utf8_sig_template(self):
        ex = tpl('TPL-EX-ACCOUNTING-DOLLARS')
        data = '﻿Ref,Supplier,Job,Date,Total (inc GST)\nEX-1,A,J1,05/03/2026,"1,100.00"\n'.encode('utf-8')
        r = M.apply_template(ex, data).rows[0]
        self.assertEqual(r.mapped['amount_inc_gst_cents'], 110000)


class TestDollars(unittest.TestCase):
    def setUp(self):
        self.t = tpl('TPL-EX-ACCOUNTING-DOLLARS')

    def amt(self, text):
        r = M.apply_template(self.t, csvb(['Ref', 'Supplier', 'Job', 'Date', 'Total (inc GST)'], [['E', 'S', 'J', '05/03/2026', text]])).rows[0]
        return None if r.rejected else r.mapped['amount_inc_gst_cents']

    def test_exact_conversion(self):
        for text, want in (('1,100.00', 110000), ('$55.55', 5555), ('55', 5500), ('0.05', 5), ('1,234,567.8', 123456780), ('(12.00)', -1200), ('-3.10', -310), ('$0', 0)):
            self.assertEqual(self.amt(text), want, text)

    def test_never_rounds_or_guesses(self):
        for bad in ('55.555', '1.234', '1,00', '1,0000', ',100', '1.', '.50', '12 .00', '$$5', '(5', 'five', '1,100,00.00', '１００'):
            self.assertIsNone(self.amt(bad), bad)


class TestTemplateValidation(unittest.TestCase):
    def test_all_shipped_templates_are_valid(self):
        import glob, json, os
        from ._path import HERE_ROOT
        files = glob.glob(os.path.join(HERE_ROOT, 'import_templates', '*.json')) + glob.glob(os.path.join(HERE_ROOT, 'ingest_templates', '*.json'))
        self.assertGreaterEqual(len(files), 12)
        for f in files:
            self.assertEqual(M.validate_template(json.load(open(f))), [], f)

    def break_it(self, fn):
        t = copy.deepcopy(T); fn(t)
        return M.validate_template(t)

    def test_each_break_is_caught(self):
        brk = {
            'tenant column': lambda t: t['columns'][0].update(target_field='tenant_id'),
            'tenant binding': lambda t: t.update(tenant_binding='file_column'),
            'not a draft': lambda t: t.update(status='verified'),
            'bad category': lambda t: t.update(source_category='SRC-99'),
            'bad money unit': lambda t: t['money'].update(unit='euros'),
            'duplicate target': lambda t: t['columns'][1].update(target_field=t['columns'][0]['target_field']),
            'duplicate source': lambda t: t['columns'][1].update(source_column=t['columns'][0]['source_column']),
            'bad type': lambda t: t['columns'][0].update(type='blob'),
            'bad transform': lambda t: t['columns'][0].update(transform='eval'),
            'date without format': lambda t: [c.pop('date_format') for c in t['columns'] if c['type'] == 'date'],
            'blank is zero': lambda t: t['columns'][8].update(missing_means='zero'),
            'natural key unmapped': lambda t: t.update(natural_key=['nope']),
            'natural key optional': lambda t: t.update(natural_key=['cost_code']),
            'no columns': lambda t: t.update(columns=[]),
            'bad delimiter': lambda t: t['file'].update(delimiter=',,'),
            'bad encoding': lambda t: t['file'].update(encoding='no-such-codec'),
            'bad header row': lambda t: t['file'].update(header_row=0),
            'required not boolean': lambda t: t['columns'][0].update(required='yes'),
            'cents file converting dollars': lambda t: [c.update(transform='dollars_to_cents') for c in t['columns'] if c['type'] == 'money_cents'],
        }
        for name, fn in brk.items():
            self.assertTrue(self.break_it(fn), name)

    def test_an_invalid_template_is_refused_at_apply_time(self):
        t = copy.deepcopy(T); t['tenant_binding'] = 'file_column'
        with self.assertRaises(M.FileRejected) as cm:
            M.apply_template(t, inv_file(inv()))
        self.assertEqual(cm.exception.code, 'TEMPLATE_INVALID')


if __name__ == '__main__':
    unittest.main()
