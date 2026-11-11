"""Boundary and guard tests added after the first mutation run showed they were missing: exact limits (a value AT the limit is accepted, one past it is refused), every
branch of each guard on its own, and the fail-safe behaviour of small helpers.  Each test says what it protects."""
import copy, os, unittest
from . import _path                                         # noqa: F401
from .helpers_ingest import INV_H, World, csvb, inv, inv_file, load_suppliers, tpl
from . import test_ingest_reconcile as TR
from apg import canon
from apg.ingest import demo_setup as D, documents as DOC, entities as E, filestore as FST, freshness as F, jobs, mapping as M, pipeline as P, reconcile as R, review, views
from apg.ingest.ports_m3 import SCANNER_ROLE, IntegrityError
from apg.ingest.specs import IngestPolicy
from apg.ports import PayloadInvalid
from apg.source_authority import AuthorityError, AuthorityRegister, AuthorityRule
from apg.values import Known, Unknown

T = tpl('TPL-BZ-AP-INVOICES')


def one(cells, template=T, header=INV_H, limits=None):
    return M.apply_template(template, csvb(header, [cells]), limits).rows[0]


def codes(row):
    return [p['code'] for p in row.problems]


class TestMappingBoundaries(unittest.TestCase):
    def test_file_size_limit_is_inclusive(self):
        data = inv_file(inv())
        M.apply_template(T, data, M.Limits(max_bytes=len(data)))                                     # exactly at the limit: accepted
        with self.assertRaises(M.FileRejected) as c:
            M.apply_template(T, data, M.Limits(max_bytes=len(data) - 1))
        self.assertEqual(c.exception.code, 'FILE_TOO_LARGE')

    def test_row_count_limit_is_inclusive(self):
        data = inv_file(inv('INV-1'), inv('INV-2'))
        self.assertEqual(len(M.apply_template(T, data, M.Limits(max_rows=2)).rows), 2)
        with self.assertRaises(M.FileRejected) as c:
            M.apply_template(T, data, M.Limits(max_rows=1))
        self.assertEqual(c.exception.code, 'TOO_MANY_ROWS')

    def test_cell_length_limit_is_inclusive(self):
        lim = M.Limits(max_cell_chars=10)
        self.assertFalse(one(inv(sin='S' * 10), limits=lim).rejected)
        r = one(inv(sin='S' * 11), limits=lim)
        self.assertTrue(r.rejected)
        self.assertIn('CELL_TOO_LONG', codes(r))

    def test_date_range_ends_are_inclusive(self):
        lim = M.Limits(min_date='2026-05-01', max_date='2026-05-31')
        for ok in ('2026-05-01', '2026-05-31', '2026-05-15'):
            self.assertFalse(one(inv(date=ok), limits=lim).rejected, ok)
        for bad in ('2026-04-30', '2026-06-01'):
            r = one(inv(date=bad), limits=lim)
            self.assertTrue(r.rejected, bad)
            self.assertIn('DATE_OUT_OF_RANGE', codes(r))

    def test_cents_range_end_is_inclusive_in_both_unit_systems(self):
        self.assertFalse(one(inv(ex=str(M.MAX_ABS_CENTS))).rejected)
        self.assertIn('OUT_OF_RANGE', codes(one(inv(ex=str(M.MAX_ABS_CENTS + 1)))))
        dol = tpl('TPL-EX-ACCOUNTING-DOLLARS'); H = ['Ref', 'Supplier', 'Job', 'Date', 'Total (inc GST)']
        top = f'${M.MAX_ABS_CENTS // 100:,}.00'                                                           # exactly 10**13 cents
        r = one(['R-1', 'S', 'J', '01/05/2026', top], dol, H)
        self.assertEqual((r.rejected, r.mapped['amount_inc_gst_cents']), (False, M.MAX_ABS_CENTS))
        r = one(['R-2', 'S', 'J', '01/05/2026', f'${M.MAX_ABS_CENTS // 100:,}.01'], dol, H)
        self.assertIn('OUT_OF_RANGE', codes(r))

    def test_bracketed_negative_dollars_need_both_brackets(self):
        dol = tpl('TPL-EX-ACCOUNTING-DOLLARS'); H = ['Ref', 'Supplier', 'Job', 'Date', 'Total (inc GST)']
        self.assertEqual(one(['R-1', 'S', 'J', '01/05/2026', '($5.00)'], dol, H).mapped['amount_inc_gst_cents'], -500)
        for half in ('($5.00', '$5.00)', '(5.00', '5.00)'):
            r = one(['R-1', 'S', 'J', '01/05/2026', half], dol, H)
            self.assertIn('INVALID_MONEY', codes(r), half)

    def test_boolean_cells(self):
        t = copy.deepcopy(T)
        t['columns'].append({'required': False, 'source_column': 'flag', 'target_field': 'flag', 'transform': 'none', 'type': 'boolean'})
        H = INV_H + ['flag']
        for text in ('true', 'TRUE', 'Yes', '1'):
            self.assertIs(one(inv() + [text], t, H).mapped['flag'], True, text)
        for text in ('false', 'No', '0'):
            self.assertIs(one(inv() + [text], t, H).mapped['flag'], False, text)
        r = one(inv() + ['maybe'], t, H)
        self.assertNotIn('flag', r.mapped)
        self.assertEqual(r.unknown['flag'], 'invalid')
        self.assertIn('INVALID_BOOLEAN', codes(r))
        self.assertNotIn('flag', one(inv() + [''], t, H).mapped)                                           # blank stays unknown
        self.assertEqual(one(inv() + ['7'], t, H).unknown['flag'], 'invalid')                              # only the listed words count

    def test_identifier_whitespace_rules(self):
        self.assertFalse(one(inv('INV 1')).rejected)                                                        # an ordinary inner space is allowed
        for ch in ('\t', ' ', ' '):
            r = one(inv('INV' + ch + '1'))
            self.assertTrue(r.rejected, repr(ch))

    def test_template_columns_and_natural_key_are_checked(self):
        base = copy.deepcopy(T)
        for bad in ([], 'abc', None):
            t = copy.deepcopy(base); t['columns'] = bad
            self.assertIn('columns', M.validate_template(t), repr(bad))
        for nk in (['no_such_column'], [], 'invoice_id'):
            t = copy.deepcopy(base); t['natural_key'] = nk
            self.assertIn('natural_key must name mapped source columns', M.validate_template(t), repr(nk))
        t = {k: copy.deepcopy(v) for k, v in base.items()}                                                  # a key naming EVERY mapped column is allowed
        t['columns'] = [c for c in t['columns'] if c['source_column'] in ('invoice_id', 'ex_gst_cents')]
        t['natural_key'] = ['invoice_id', 'ex_gst_cents']
        self.assertEqual(M.validate_template(t), [])
        t['natural_key'] = ['invoice_id', 'gst_cents']
        self.assertIn('natural_key must name mapped source columns', M.validate_template(t))


class TestEntityGuards(unittest.TestCase):
    def test_blank_and_non_text_supplier_references_are_unresolved(self):
        d = E.SupplierDirectory([('SUP-1', 'Alpha Concrete Pty Ltd')])
        for v in (None, '', '   ', 5, b'x'):
            m = d.resolve(v)
            self.assertEqual((m.status, m.method, m.supplier_id), (E.UNRESOLVED, 'blank', None), repr(v))

    def test_directory_ignores_suppliers_without_a_usable_identifier(self):
        d = E.SupplierDirectory([(None, 'Ghost One'), ('', 'Ghost Two'), ('  ', 'Ghost Three'), (7, 'Ghost Four'), ('SUP-1', 'Alpha Concrete Pty Ltd')])
        self.assertEqual(d.ids(), ('SUP-1',))
        self.assertEqual(d.resolve('Ghost One').status, E.UNRESOLVED)

    def test_a_look_alike_is_never_chosen(self):
        d = E.SupplierDirectory([('SUP-1', 'Alpha Concrete Pty Ltd'), ('SUP-2', 'Alpha Concrete Supplies Pty Ltd')])
        m = d.resolve('Alpha Concrete')
        self.assertEqual((m.status, m.supplier_id, m.candidates), (E.AMBIGUOUS, None, ('SUP-1', 'SUP-2')))
        d1 = E.SupplierDirectory([('SUP-1', 'Alpha Concrete Pty Ltd')])
        m = d1.resolve('Alpha Concrete Supplies')                                                           # a longer name that merely contains it
        self.assertEqual((m.status, m.supplier_id, m.candidates), (E.NEEDS_CONFIRMATION, None, ('SUP-1',)))
        m = d1.resolve('Alpha')                                                                             # a shorter name contained in it
        self.assertEqual((m.status, m.supplier_id), (E.NEEDS_CONFIRMATION, None))
        m = d1.resolve('Alpha Concrete Ltd')                                                                # same words, different legal form words: resembles, not equal
        self.assertEqual((m.status, m.supplier_id), (E.NEEDS_CONFIRMATION, None))
        d2 = E.SupplierDirectory([('SUP-1', 'Alpha Concrete Pty Ltd'), ('SUP-2', 'Alpha Concrete Pty Ltd')])
        self.assertEqual((d2.resolve('Alpha Concrete Pty Ltd').status, d2.resolve('Alpha Concrete Pty Ltd').candidates), (E.AMBIGUOUS, ('SUP-1', 'SUP-2')))


Q = tpl('TPL-BZ-QUOTES')
QH = ['quote_id', 'supplier_id', 'material_id', 'specification', 'issue_date', 'valid_until', 'unit_rate_cents', 'currency', 'fx_rate_used', 'fx_rate_date', 'freight_cents_per_unit',
      'incoterm_delivery_basis', 'lead_time_days', 'price_kind']


def quote(issue, until):
    return ['Q-1', 'SUP-1', 'MAT-1', 'spec', issue, until, '1000', 'AUD', '', '', '0', 'FOB', '5', 'quote']


class TestPipelineBoundaries(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.s = self.w.who('a')

    def test_a_quote_valid_until_before_it_was_issued_is_held_and_equal_dates_are_fine(self):
        def pend(issue, until, entity='supplier_quote'):
            row = one(quote(issue, until), Q, QH)
            return P.intrinsic_findings(entity, row, IngestPolicy(), '2026-10-01')[0]
        self.assertIn('DATE_ORDER:valid_until_before_issue_date', pend('2026-05-02', '2026-05-01'))
        self.assertNotIn('DATE_ORDER:valid_until_before_issue_date', pend('2026-05-01', '2026-05-01'))
        self.assertNotIn('DATE_ORDER:valid_until_before_issue_date', pend('2026-05-01', '2026-05-02'))
        self.assertNotIn('DATE_ORDER:valid_until_before_issue_date', pend('2026-05-02', '2026-05-01', entity='ap_invoice'))   # only quotes have this rule

    def test_future_dated_boundary_is_the_receipt_day_plus_the_allowed_days(self):
        def pend(date, allowed):
            return [c for c in P.intrinsic_findings('ap_invoice', one(inv(date=date)), IngestPolicy(future_days_allowed=allowed), '2026-10-01')[0] if c.startswith('FUTURE_DATED')]
        self.assertEqual(pend('2026-10-01', 0), [])                                      # dated the day it was received
        self.assertEqual(pend('2026-10-02', 0), ['FUTURE_DATED:invoice_date'])
        self.assertEqual(pend('2026-10-03', 2), [])
        self.assertEqual(pend('2026-10-04', 2), ['FUTURE_DATED:invoice_date'])

    def test_delivery_decision_when_a_conflict_is_already_open(self):
        ex = {'conflict': {'contenders': [{'content_hash': 'a', 'source_revision': 3}, {'content_hash': 'b', 'source_revision': 5}]}}
        self.assertEqual(P.decide(ex, 'c', 6)[0], 'revision')                              # above every version
        self.assertEqual(P.decide(ex, 'c', 5)[0], 'conflict')                              # equal to the highest is not above it
        self.assertEqual(P.decide(ex, 'c', 4)[0], 'conflict')
        self.assertEqual(P.decide(ex, 'c', None)[0], 'conflict')
        self.assertEqual(P.decide(ex, 'a', 3)[0], 'duplicate')
        self.assertEqual(P.decide(ex, 'a', 4)[0], 'conflict')                              # same content under another revision is a different version
        unordered = {'conflict': {'contenders': [{'content_hash': 'a', 'source_revision': 3}, {'content_hash': 'b', 'source_revision': None}]}}
        self.assertEqual(P.decide(unordered, 'c', 9)[0], 'conflict')                      # no order can be established

    def test_delivery_decision_for_a_single_stored_version(self):
        ex = {'conflict': None, 'content_hash': 'a', 'source_revision': 3}
        self.assertEqual([P.decide(ex, 'b', r)[0] for r in (4, 3, 2, None)], ['revision', 'conflict', 'stale', 'conflict'])
        self.assertEqual([P.decide(ex, 'a', r)[0] for r in (3, None, 4)], ['duplicate', 'duplicate', 'revision'])
        self.assertEqual(P.decide(None, 'a', 1)[0], 'new')

    def test_conflict_contenders_are_ordered_whatever_order_they_arrived_in(self):
        mk = lambda h, r: {'content_hash': h, 'source_revision': r}
        a = P._conflict_payload('budget_line', 's', 'K', [mk('h', 3), mk('h', None), mk('h', 1), mk('g', 9)])
        b = P._conflict_payload('budget_line', 's', 'K', [mk('g', 9), mk('h', 1), mk('h', 3), mk('h', None)])
        self.assertEqual(a, b)
        self.assertEqual([(c['content_hash'], c['source_revision']) for c in a['conflict']['contenders']], [('g', 9), ('h', None), ('h', 1), ('h', 3)])

    def test_a_late_version_is_kept_as_a_contender_not_dropped(self):
        bud = tpl('TPL-BZ-BUDGET-LINES')
        H = ['project_id', 'cost_code', 'budget_cents', 'revision', 'revision_date']
        go = lambda cents, rev, n: P.ingest_file(self.s, self.w.clock, bud, csvb(H, [['PRJ-001', 'CC-01', cents, rev, '2026-01-01']]), 'job_costing', n, D.DEMO_POLICY, 'source_revision_label')
        go('100', 'R5', 'a.csv')
        go('200', 'R5', 'b.csv')                                  # same revision, different content: conflict with two versions
        r = go('100', 'R4', 'c.csv')                              # an older revision of the first content arrives
        self.assertEqual(r['counts']['conflict'], 1)
        cons = self.s.get('budget_line', 'PRJ-001|CC-01').payload['conflict']['contenders']
        self.assertEqual(sorted(c['source_revision'] for c in cons), [4, 5, 5])
        self.assertEqual(self.s.get('budget_line', 'PRJ-001|CC-01').payload['intrinsic']['outcome'], 'quarantined')

    def test_an_unreadable_revision_label_is_warned_and_a_readable_one_is_not(self):
        bud = tpl('TPL-BZ-BUDGET-LINES')
        H = ['project_id', 'cost_code', 'budget_cents', 'revision', 'revision_date']
        go = lambda key, rev: P.ingest_file(self.s, self.w.clock, bud, csvb(H, [[key, 'CC-01', '100', rev, '2026-01-01']]), 'job_costing', key + '.csv', D.DEMO_POLICY, 'source_revision_label')
        go('PRJ-A', 'draft-a'); go('PRJ-B', 'R2')
        warn = lambda k: self.s.get('budget_line', k + '|CC-01').payload['intrinsic']['warnings']
        self.assertIn('REVISION_UNPARSED', warn('PRJ-A'))
        self.assertNotIn('REVISION_UNPARSED', warn('PRJ-B'))

    def test_a_rejected_file_is_audited_under_its_own_name_or_a_stand_in(self):
        for name, shown in (('my file.csv', 'my file.csv'), ('', 'file')):
            P.ingest_file(self.s, self.w.clock, T, b'', 'accounting', name, D.DEMO_POLICY)
            ev = [e for e in self.w.audit.read(self.s.ctx) if e.event_type == 'ingest.file_rejected'][-1]
            self.assertEqual(ev.resource, shown)


CR_H, PM_H, PAY_H, PO_H, AS_OF, REG = TR.CR_H, TR.PM_H, TR.PAY_H, TR.PO_H, TR.AS_OF, TR.REG
CRT, PMT, PAYT, POT, po = TR.CRT, TR.PMT, TR.PAYT, TR.POT, TR.po


class TestReconcileGaps(TR.Base):
    def test_a_held_record_keeps_its_amount_visible_but_a_rejected_one_has_none(self):
        self.invs(inv(po='PO-404'))
        self.rc()
        st = self.state('ap_invoice', 'INV-1')
        self.assertEqual((st['effective_outcome'], st['amount_cents'], st['review']), ('pending_reconciliation', 1000000, {'status': 'open'}))
        review.decide(self.rec, 'ap_invoice/INV-1', 'reject', 'not our invoice')
        self.rc()
        st = self.state('ap_invoice', 'INV-1')
        self.assertEqual((st['effective_outcome'], st['amount_cents'], st['review']['status']), ('rejected', None, 'rejected'))

    def test_a_held_record_shows_the_competing_values_of_its_own_conflict_only(self):
        self.put(POT, PO_H, [po('PO-1')], 'procurement')
        self.invs(inv('INV-1', po='PO-1', ex='500'), inv('INV-2', sin='SI-2', po='PO-404', ex='800'))
        self.put(PMT, PM_H, [['INV-1', 'SUP-001', 'PRJ-001', '600', 'pm'], ['INV-2', 'SUP-001', 'PRJ-001', '800', 'pm']], 'pm_system')
        self.rc()
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'quarantined')
        q = R.ReviewQueue(self.s)
        got = {i.key: i.payload['candidates'] for i in q.open_items()}
        self.assertEqual(got['ap_invoice/INV-1'], [['accounting', '500'], ['pm_system', '600']])
        self.assertEqual(got['ap_invoice/INV-2'], [])                       # held for another reason: no competing values to show

    def test_the_review_item_records_the_register_it_was_held_under(self):
        self.conflicted()
        self.assertEqual(R.ReviewQueue(self.s).open_items()[0].payload['register_version'], REG.version)
        self.setUp()
        self.invs(inv('INV-1', ex='500')); self.invs(inv('INV-1', ex='700'))
        self.rc(None)                                                       # no register at all: the item says so with an empty version, not a made-up one
        self.assertEqual(self.s.get('quarantine', 'ap_invoice/INV-1').payload['register_version'], '')

    def conflicted(self):
        self.invs(inv('INV-1', ex='500'))
        self.invs(inv('INV-1', ex='700'))
        self.rc()

    def test_a_conflicted_credit_note_and_payment_are_held_without_disturbing_the_run(self):
        self.invs(inv('INV-1', ex='1000', gst='100'))
        self.put(CRT, CR_H, [['CRN-1', 'SUP-001', 'INV-1', '2026-07-25', '300', '']], 'accounting')
        self.put(CRT, CR_H, [['CRN-1', 'SUP-001', 'INV-1', '2026-07-25', '400', '']], 'accounting')
        self.put(PAYT, PAY_H, [['P1', 'INV-1', '2026-06-01', '100']], 'accounting')
        self.put(PAYT, PAY_H, [['P1', 'INV-1', '2026-06-01', '200']], 'accounting')
        self.rc()
        for kind, key in (('credit_note', 'CRN-1'), ('payment', 'P1')):
            self.assertEqual(self.outcome(kind, key), 'quarantined', kind)
            self.assertEqual(self.codes(kind, key), ['CONFLICT_SAME_KEY'], kind)
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'accepted_with_warnings')              # the invoice is not touched by a credit nobody can trust

    def test_a_cross_check_for_a_record_that_exists_but_is_held_is_not_called_orphaned(self):
        self.conflicted()
        self.put(PMT, PM_H, [['INV-1', 'SUP-001', 'PRJ-001', '500', 'pm']], 'pm_system')
        self.rc()
        self.assertEqual(self.codes('pm_invoice', 'INV-1'), [])
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'quarantined')
        self.put(PMT, PM_H, [['INV-9', 'SUP-001', 'PRJ-001', '500', 'pm']], 'pm_system')            # no primary at all is the orphan case
        self.rc()
        self.assertEqual(self.codes('pm_invoice', 'INV-9'), ['SECONDARY_WITHOUT_PRIMARY:INV-9'])

    def test_a_stored_amount_that_is_not_a_whole_number_fails_safe(self):
        for bad in (True, 'abc', None):            # (a float cannot even be stored: the record store refuses it)
            with self.subTest(bad=repr(bad)):
                self.setUp()
                self.invs(inv('INV-1', ex='1000'))
                self.rc()
                cur = self.s.get('ap_invoice', 'INV-1')
                p = canon.deep_copy(cur.payload); p['fields']['amount_ex_gst_cents'] = bad
                self.s.put('ap_invoice', 'INV-1', p, expected_revision=cur.revision)
                self.rc()
                st = self.state('ap_invoice', 'INV-1')
                self.assertEqual(st['effective_outcome'], 'pending_reconciliation')
                self.assertTrue(any(c.startswith('AUTHORITATIVE_VALUE_UNKNOWN') for c in self.codes('ap_invoice', 'INV-1')))
                self.assertEqual(views.invoice_cost_view(self.s, AS_OF)[0].cents, 0)

    def test_a_supplier_record_that_is_itself_held_does_not_become_the_supplier_list(self):
        from .helpers_ingest import sup_file
        w = World(); s = w.who('x', roles=('importer',))
        P.ingest_file(s, w.clock, tpl('TPL-BZ-SUPPLIERS'), sup_file(('SUP-001', 'Alpha Concrete Pty Ltd')), 'master', 's.csv', IngestPolicy())      # strict: the blank ABN holds it
        self.assertEqual(s.get('supplier', 'SUP-001').payload['intrinsic']['outcome'], 'pending_reconciliation')
        P.ingest_file(s, w.clock, TR.INVT, inv_file(inv()), 'accounting', 'i.csv', D.DEMO_POLICY)
        R.reconcile(s, REG, AS_OF)
        st = s.get('recon_state', 'ap_invoice/INV-1').payload
        self.assertIsNone(st['supplier_id'])
        self.assertIn('SUPPLIER_UNVERIFIABLE_NO_MASTER', [f['code'] for f in st['findings']])


class TestViewGaps(TR.Base):
    def test_a_credit_against_an_invoice_nobody_trusts_yet_stays_visible_and_unnetted(self):
        self.invs(inv('INV-1', ex='1000', po='PO-404'))
        self.put(CRT, CR_H, [['CRN-1', 'SUP-001', 'INV-1', '2026-07-25', '400', '']], 'accounting')
        self.rc()
        auth, _ = views.invoice_cost_view(self.s, AS_OF)
        rows = {x[0]: x for x in auth.excluded}
        self.assertEqual(rows['credit:CRN-1'][1:], ('pending_reconciliation', ('CREDIT_NOT_LINKED_TO_A_TRUSTED_INVOICE',)))
        self.assertEqual(rows['INV-1'][1], 'pending_reconciliation')
        self.assertEqual(auth.cents, 0)

    def test_a_held_credit_with_no_trusted_invoice_keeps_its_own_status_and_reasons(self):
        self.put(CRT, CR_H, [['CRN-1', 'SUP-001', 'INV-1', '2026-07-25', '300', '']], 'accounting')
        self.put(CRT, CR_H, [['CRN-1', 'SUP-001', 'INV-1', '2026-07-25', '400', '']], 'accounting')
        self.rc()
        auth, _ = views.invoice_cost_view(self.s, AS_OF)
        row = [x for x in auth.excluded if x[0] == 'credit:CRN-1'][0]
        self.assertEqual(row[1:], ('quarantined', ('CONFLICT_SAME_KEY',)))
        self.assertEqual([x[0] for x in views.invoice_cost_view(self.s, AS_OF, project='PRJ-001')[0].excluded if x[0].startswith('credit:')], [])      # a project view never lists unlinked credits

    def test_gst_counts_only_trusted_records_that_have_been_reconciled(self):
        self.invs(inv('INV-1', ex='1000', gst='100'), inv('INV-2', sin='SI-2', ex='2000', gst='500', po='PO-404'))
        self.put(CRT, CR_H, [['CRN-1', 'SUP-001', 'INV-1', '2026-07-25', '300', '30']], 'accounting')
        self.put(CRT, CR_H, [['CRN-2', 'SUP-001', 'INV-2', '2026-07-25', '300', '40']], 'accounting')
        self.put(CRT, CR_H, [['CRN-3', 'SUP-001', 'INV-1', '2026-07-25', '1', '']], 'accounting')
        self.put(CRT, CR_H, [['CRN-3', 'SUP-001', 'INV-1', '2026-07-25', '2', '']], 'accounting')       # conflicted: not trusted, and it has no GST figure to guess from
        self.rc()
        self.invs(inv('INV-3', sin='SI-3', ex='9000', gst='900'))                                         # arrives after the last reconcile
        self.put(CRT, CR_H, [['CRN-4', 'SUP-001', 'INV-1', '2026-07-25', '1', '1']], 'accounting')
        g = views.gst_view(self.s)
        self.assertEqual(g.cents, 100 - 30)                       # INV-1 less its credit; INV-2 (held) and its credit, INV-3 and CRN-4 (not reconciled) and CRN-3 (conflict) are not in it


class TestReviewGuards(TR.Base):
    def test_only_a_human_entity_steward_can_resolve_a_supplier(self):
        self.invs(inv('INV-1', supplier='Metro Steel'))
        self.rc()
        for who in (self.w.who('ai', user='bot', roles=('entity_steward',), kind='ai'), self.w.who('svc', user='svc', roles=('entity_steward',), kind='service'), self.rec, self.s):
            with self.assertRaises(AuthorityError):
                review.resolve_supplier(who, 'ap_invoice', 'INV-1', 'SUP-003', 'n')
        with self.assertRaises(AuthorityError):
            review.resolve_supplier(self.stew, 'ap_invoice', 'INV-1', 'SUP-003', ' ')
        with self.assertRaises(AuthorityError):
            review.resolve_supplier(self.stew, 'ap_invoice', 'INV-1', 'SUP-404', 'n')
        with self.assertRaises(AuthorityError):
            review.resolve_supplier(self.stew, 'ap_invoice', 'INV-404', 'SUP-003', 'n')
        self.put(PAYT, PAY_H, [['P1', 'INV-1', '2026-06-01', '5']], 'accounting')
        with self.assertRaises(AuthorityError) as c:
            review.resolve_supplier(self.stew, 'payment', 'P1', 'SUP-003', 'n')               # a payment names no supplier
        self.assertIn('no supplier text', str(c.exception))
        review.resolve_supplier(self.stew, 'ap_invoice', 'INV-1', 'SUP-003', 'checked the ABN')

    def test_alias_proposal_and_approval_guards(self):
        with self.assertRaises(AuthorityError):
            review.propose_alias(self.stew, 'M Steel', 'SUP-404')
        with self.assertRaises(AuthorityError) as c:
            review.approve_alias(self.stew, 'never proposed', 'n')
        self.assertIn('no proposed alias', str(c.exception))
        review.propose_alias(self.stew, 'M Steel', 'SUP-003')
        for who in (self.w.who('ai', user='bot', roles=('entity_steward',), kind='ai'), self.rec, self.s):
            with self.assertRaises(AuthorityError) as c:
                review.approve_alias(who, 'M Steel', 'n')
            self.assertIn('human entity steward', str(c.exception))
        with self.assertRaises(AuthorityError):
            review.approve_alias(self.stew, 'M Steel', 'n')                                   # the proposer cannot approve their own
        other = self.w.who('stew2', user='sue', roles=('entity_steward',))
        review.approve_alias(other, 'M Steel', 'ok')
        with self.assertRaises(AuthorityError) as c:
            review.approve_alias(other, 'M Steel', 'again')                                   # already approved: nothing left to approve
        self.assertIn('no proposed alias', str(c.exception))

    def test_deciding_on_a_record_that_is_not_held_is_refused(self):
        with self.assertRaises(AuthorityError) as c:
            review.decide(self.rec, 'ap_invoice/INV-404', 'accept', 'n')
        self.assertIn('no such held record', str(c.exception))

    def test_a_decision_stops_counting_when_the_rule_on_who_decides_or_how_many_changes(self):
        def reg_with(role, need, name):
            rules = tuple(r if r.entity_kind != 'ap_invoice' else AuthorityRule('ap_invoice', 'amount_ex_gst_cents', 'accounting', ('pm_system',), 'source_owned', 'quarantine', role, need, '2025-01-01', None, 'o', 'e') for r in REG.rules)
            return AuthorityRegister(name, rules, 'synthetic.proposer', REG.approvals)
        for role, need in (('reconciler', 2), ('senior_reconciler', 1)):
            with self.subTest(role=role, need=need):
                self.setUp()
                self.invs(inv('INV-1', ex='500')); self.invs(inv('INV-1', ex='700')); self.rc()
                review.decide(self.rec, 'ap_invoice/INV-1', 'correct', 'confirmed with the supplier statement', 700)
                self.rc()
                self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'accepted_with_warnings')
                self.rc(reg_with(role, need, 'SYN-REG-CHANGED'))        # the people who must decide, or how many, are now different: the earlier decision no longer counts
                self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'quarantined')
                self.assertEqual(len(R.ReviewQueue(self.s).open_items()), 1)


def doc_text(name):
    from ._path import HERE_ROOT
    return open(os.path.join(HERE_ROOT, 'builder_zero', 'zero_one', 'SRC-11_documents', name), 'rb').read()


class TestDocumentGaps(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.s = self.w.who('imp'); self.v = self.w.who('ver', user='vera', roles=(DOC.VERIFIER_ROLE,))

    def reg(self, doc_id, text):
        data = text.encode()
        DOC.register_extraction(self.s, self.w.clock, doc_id, data, DOC.standin_extract_quote(text))

    def verified(self, doc_id, name):
        return self.s.get('extracted_document', doc_id).payload['fields'][name]['verification']['disposition']

    def test_a_document_must_be_bytes(self):
        with self.assertRaises(AuthorityError):
            DOC.register_extraction(self.s, self.w.clock, 'D-1', 'text, not bytes', [])

    def test_confirmed_only_when_the_person_agrees_with_an_unambiguous_reading(self):
        self.reg('D-1', 'Supplier: Alpha Concrete\nQuantity: 10\nRate: $2.00\n')
        self.reg('D-2', 'Supplier: Alpha Concrete\nQuantity: 10\nRate: $2.00\n ')              # a second copy of the same text, verified differently
        DOC.verify_field(self.v, self.w.clock, 'D-1', 'quantity', 10, 'page 1', 'agrees')
        DOC.verify_field(self.v, self.w.clock, 'D-2', 'quantity', 11, 'page 1', 'the page says 11')
        self.assertEqual((self.verified('D-1', 'quantity'), self.verified('D-2', 'quantity')), ('confirmed', 'corrected'))
        DOC.verify_field(self.v, self.w.clock, 'D-1', 'supplier_text', 'Alpha Concrete', 'page 1', 'agrees')        # a text field with a single reading
        DOC.verify_field(self.v, self.w.clock, 'D-2', 'supplier_text', 'Alpha Concrete Pty Ltd', 'page 1', 'full legal name')
        self.assertEqual((self.verified('D-1', 'supplier_text'), self.verified('D-2', 'supplier_text')), ('confirmed', 'corrected'))

    def test_an_ambiguous_reading_is_never_called_confirmed_even_when_the_person_picks_its_only_candidate(self):
        self.reg('D-1', 'Quantity: 4O\n')
        f = self.s.get('extracted_document', 'D-1').payload['fields']['quantity']
        self.assertEqual((f['candidates'], f['ambiguous']), ([40], True))
        DOC.verify_field(self.v, self.w.clock, 'D-1', 'quantity', 40, 'page 1', 'the letter O was a zero')
        self.assertEqual(self.verified('D-1', 'quantity'), 'corrected')

    def test_an_unreadable_number_takes_a_whole_number_only(self):
        self.reg('D-1', 'Quantity: forty\n')
        self.assertEqual(self.s.get('extracted_document', 'D-1').payload['fields']['quantity']['candidates'], [])
        with self.assertRaises(AuthorityError):
            DOC.verify_field(self.v, self.w.clock, 'D-1', 'quantity', 'forty', 'page 1', 'n')
        DOC.verify_field(self.v, self.w.clock, 'D-1', 'quantity', 40, 'page 1', 'n')
        self.assertEqual(self.verified('D-1', 'quantity'), 'corrected')

    def test_what_the_authority_logic_is_told_about_an_extracted_value(self):
        a, c = doc_text('quote_ambiguous_SUP-004.txt'), doc_text('quote_clear_SUP-006.txt')
        DOC.register_extraction(self.s, self.w.clock, 'DOC-002', a, DOC.standin_extract_quote(a.decode()))
        DOC.register_extraction(self.s, self.w.clock, 'DOC-001', c, DOC.standin_extract_quote(c.decode()))
        o = DOC.observation(self.s, 'DOC-002', 'quantity')                          # one candidate but ambiguous: it is NOT offered as a value
        self.assertEqual((type(o.value), o.value.reason, o.value.detail, o.human_verified), (Unknown, 'ambiguous', 'letters inside a number (zero or the letter?)', False))
        o = DOC.observation(self.s, 'DOC-001', 'supplier_text')                     # not ambiguous but no number to offer
        self.assertEqual((type(o.value), o.value.reason, o.value.detail), (Unknown, 'ambiguous', 'ambiguous reading'))
        o = DOC.observation(self.s, 'DOC-001', 'quantity')                          # a clear reading is a value, still unverified
        self.assertEqual((o.value, o.human_verified, o.origin), (Known(2000, ()), False, 'ai_extracted'))
        self.assertEqual(DOC.observation(self.s, 'DOC-001', 'nonsense').value.reason, 'no_data')
        self.assertEqual(DOC.observation(self.s, 'DOC-404', 'quantity').value.reason, 'no_data')

    def test_verified_text_of_nothing_is_none(self):
        self.reg('D-1', 'Supplier: Alpha Concrete\n')
        self.assertIsNone(DOC.verified_text(self.s, 'D-404', 'supplier_text'))
        self.assertIsNone(DOC.verified_text(self.s, 'D-1', 'no_such_field'))
        self.assertIsNone(DOC.verified_text(self.s, 'D-1', 'supplier_text'))               # not yet verified
        DOC.verify_field(self.v, self.w.clock, 'D-1', 'supplier_text', 'Alpha Concrete', 'page 1', 'n')
        self.assertEqual(DOC.verified_text(self.s, 'D-1', 'supplier_text'), 'Alpha Concrete')


class TestSupportGaps(unittest.TestCase):
    def test_currency_conversion_refuses_a_zero_rate_both_ways_and_rounds_negatives_and_zero(self):
        for frm, to in (('AUD', 'USD'), ('USD', 'AUD')):
            with self.assertRaises(ValueError):
                F.convert_minor(100, '0', frm, to, 'AUD/USD', '2026-09-30', 'src')
        with self.assertRaises(ValueError):
            F.convert_minor(100, '-0.5', 'AUD', 'USD', 'AUD/USD', '2026-09-30', 'src')
        with self.assertRaises(ValueError):
            F.convert_minor(1.5, '0.5', 'AUD', 'USD', 'AUD/USD', '2026-09-30', 'src')
        with self.assertRaises(ValueError):
            F.convert_minor(True, '0.5', 'AUD', 'USD', 'AUD/USD', '2026-09-30', 'src')
        conv = lambda n: F.convert_minor(n, '0.5', 'AUD', 'USD', 'AUD/USD', '2026-09-30', 'src')['converted_minor']
        self.assertEqual([conv(n) for n in (0, 1, -1, 3, -3, 100, -100)], [0, 1, -1, 2, -2, 50, -50])          # half rounds away from zero, symmetrically

    def runner(self, handler, sleeps, **kw):
        w = World()
        w.provider._contract_register_session('a', 'zero_one', 'ann', ('importer',), 'human', 360000)
        job = {'job_id': 'J1', 'credentials': 'a', 'payload': {}}
        return w, job, jobs.JobRunner(w.provider, w.store, w.audit, handler, sleep=sleeps.append, **kw)

    def test_one_attempt_is_a_valid_limit_and_means_exactly_one_try_and_no_wait(self):
        calls, sleeps = [], []
        def h(s, p):
            calls.append(1); raise jobs.TransientError('down')
        w, job, rn = self.runner(h, sleeps, max_attempts=1)
        r = rn.run(job)
        self.assertEqual((r['status'], r['attempts'], len(calls), sleeps), ('dead_letter', 1, 1, []))
        for bad in (0, -1, 1.0, None, '3'):
            with self.assertRaises(ValueError, msg=repr(bad)):
                jobs.JobRunner(w.provider, w.store, w.audit, h, max_attempts=bad)

    def test_a_success_says_it_was_recorded_and_attempts_add_up_across_a_requeue(self):
        mode = {'fail': True}
        def h(s, p):
            if mode['fail']:
                raise jobs.TransientError('down')
            return {'ok': 1}
        w, job, rn = self.runner(h, [], max_attempts=3)
        self.assertEqual(rn.run(job)['status'], 'dead_letter')
        mode['fail'] = False
        r = rn.requeue(job)
        self.assertEqual((r['status'], r['attempts'], r['recorded'], r['replay']), ('succeeded', 4, True, False))        # 3 earlier tries + 1
        self.assertEqual(w.store.get(w.provider.resolve('a'), 'job', 'J1').payload['attempts'], 4)


class TestFileStoreGaps(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.u = self.w.who('u', user='ann', roles=('importer',)).ctx
        self.scan = self.w.who('scan', user='scanner-svc', roles=(SCANNER_ROLE,), kind='service').ctx

    def test_name_and_size_limits_are_inclusive(self):
        fs = FST.InMemoryFileStore(self.w.provider, max_bytes=10)
        fs.put(self.u, 'n' * 200, b'0123456789')                                  # 200 characters and exactly 10 bytes: accepted
        with self.assertRaises(PayloadInvalid):
            fs.put(self.u, 'n' * 201, b'x')
        with self.assertRaises(PayloadInvalid):
            fs.put(self.u, 'ok.csv', b'0123456789A')
        for bad in ('', '../x', 'a/b', 'a\\b', 'a\x00b', 5, None):
            with self.assertRaises(PayloadInvalid, msg=repr(bad)):
                fs.put(self.u, bad, b'x')

    def test_media_type_must_be_text(self):
        fs = FST.InMemoryFileStore(self.w.provider)
        for bad in (123, None, b'text/csv'):
            with self.assertRaises(PayloadInvalid, msg=repr(bad)):
                fs.put(self.u, 'a.csv', b'x', bad)
        self.assertEqual(fs.put(self.u, 'a.csv', b'x', 'text/csv').media_type, 'text/csv')

    def test_even_an_empty_file_is_protected_by_its_hash(self):
        fs = FST.InMemoryFileStore(self.w.provider)
        m = fs.put(self.u, 'empty.csv', b'')
        fs.record_scan(self.scan, m.file_id, 'clean')
        self.assertEqual(fs.read(self.u, m.file_id), b'')
        fs._contract_corrupt(self.u.tenant_id, m.file_id)
        with self.assertRaises(IntegrityError):
            fs.read(self.u, m.file_id)
