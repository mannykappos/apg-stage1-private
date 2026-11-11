import unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import common as C, events as EV, fresh as FR, fx as FX


def world(*quotes, fx_rows=(), obs_rows=()):
    m = mkt_world()
    if quotes:
        m.quote_rows(*quotes)
    if fx_rows:
        m.fx(*fx_rows)
    if obs_rows:
        m.observations(*obs_rows)
    return m


class TestFx(unittest.TestCase):
    def conv(self, m, minor=6900, cur='USD', as_of='2026-09-30'):
        a = m.analysis(as_of=as_of)
        return FX.convert(a.F, a.mp, minor, cur, as_of)

    def test_converts_at_the_latest_rate_on_or_before_the_as_of_day_and_records_source_date_and_method(self):
        m = world(fx_rows=[fxrow('2026-09-15', '0.6637'), fxrow('2026-09-30', '0.6540'), fxrow('2026-10-15', '0.7000')])
        c = self.conv(m)
        self.assertEqual((c['status'], c['aud_cents'], c['rate_micro'], c['rate_date'], c['rate_age_days']), ('converted', 10550, 654000, '2026-09-30', 0))     # 6900 / 0.6540 = 10550.46
        self.assertEqual((c['method'], c['convention'], c['rounding']), ('latest_on_or_before', 'foreign_per_aud', 'half_away_from_zero_once'))
        self.assertTrue(c['rate_source_ref'].startswith('fx_rate/'))
        self.assertGreaterEqual(c['rate_revision'], 1)

    def test_a_rate_dated_after_the_as_of_day_is_never_used(self):
        m = world(fx_rows=[fxrow('2026-10-15', '0.7000')])
        c = self.conv(m)
        self.assertEqual(c['status'], 'not_converted')
        self.assertIsNone(c['aud_cents'])
        self.assertIn('no usable AUD/USD rate on or before 2026-09-30', c['why'])

    def test_an_old_rate_is_used_but_its_age_is_reported_so_the_freshness_gate_can_judge_it(self):
        m = world(fx_rows=[fxrow('2026-05-02', '0.6612')])
        c = self.conv(m)
        self.assertEqual((c['status'], c['rate_age_days'], c['aud_cents']), ('converted', 151, 10436))                                                         # 6900 / 0.6612 = 10435.57

    def test_same_currency_needs_no_rate(self):
        m = world()
        c = self.conv(m, 12345, 'AUD')
        self.assertEqual((c['status'], c['aud_cents'], c['method'], c['rate_source_ref']), ('converted', 12345, 'none_same_currency', None))

    def test_an_unlisted_currency_is_not_converted_and_nothing_is_guessed(self):
        m = world(fx_rows=[fxrow('2026-09-30', '0.6540')])
        c = self.conv(m, 100, 'EUR')
        self.assertEqual((c['status'], c['aud_cents']), ('not_converted', None))

    def test_rounding_is_half_away_from_zero_once(self):
        m = world(fx_rows=[fxrow('2026-09-30', '2.0000')])
        self.assertEqual(self.conv(m, 1)['aud_cents'], 1)                                    # 0.5 rounds up
        self.assertEqual(self.conv(m, 3)['aud_cents'], 2)                                    # 1.5 rounds up
        self.assertEqual(self.conv(m, 2)['aud_cents'], 1)

    def test_a_zero_or_unreadable_rate_record_is_not_used(self):
        m = world(fx_rows=[fxrow('2026-09-30', '0')])
        c = self.conv(m)
        self.assertEqual(c['status'], 'not_converted')

    def test_two_different_rates_for_one_pair_and_day_are_a_conflict_and_neither_is_used(self):
        m = world(fx_rows=[fxrow('2026-09-30', '0.6540'), fxrow('2026-09-30', '0.7000')])
        c = self.conv(m)
        self.assertEqual((c['status'], c['aud_cents']), ('not_converted', None))
        self.assertIn('1 held or invalid rate records were not used', c['why'])

    def test_an_older_usable_rate_is_used_when_the_newer_one_is_in_conflict_and_the_age_shows_it(self):
        m = world(fx_rows=[fxrow('2026-09-15', '0.6637'), fxrow('2026-09-30', '0.6540'), fxrow('2026-09-30', '0.7000')])
        c = self.conv(m)
        self.assertEqual((c['status'], c['rate_date'], c['rate_age_days']), ('converted', '2026-09-15', 15))

    def test_the_stated_rate_is_converted_separately_and_never_substituted(self):
        s = FX.convert_stated(6900, 'USD', 'AUD', 661200, '2026-05-02', '2026-09-30')
        self.assertEqual((s['status'], s['aud_cents'], s['rate_age_days'], s['method']), ('converted', 10436, 151, 'supplier_stated'))
        none = FX.convert_stated(6900, 'USD', 'AUD', None, None, '2026-09-30')
        self.assertEqual((none['status'], none['aud_cents']), ('not_converted', None))
        undated = FX.convert_stated(6900, 'USD', 'AUD', 661200, None, '2026-09-30')
        self.assertIsNone(undated['rate_age_days'])

    def test_divergence_is_signed_and_absent_when_either_side_is_missing(self):
        self.assertEqual(FX.divergence_bps(10550, 10435), 110)                               # the reference rate makes it more expensive by 1.10%
        self.assertEqual(FX.divergence_bps(10000, 10100), -99)
        self.assertIsNone(FX.divergence_bps(None, 100))
        self.assertIsNone(FX.divergence_bps(100, None))
        self.assertIsNone(FX.divergence_bps(100, 0))


class TestFreshness(unittest.TestCase):
    TH = {'quote_max_age_days': 45, 'index_max_age_days': 45, 'fx_max_age_days': 30}

    def qstate(self, issue, valid, as_of='2026-09-30'):
        m = world(quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', issue, valid, '1000'))
        a = m.analysis(as_of=as_of)
        return FR.quote_state(a.ctx.quotes['Q-1'], as_of, self.TH)

    def test_the_last_valid_day_is_valid_and_the_day_after_is_expired(self):
        self.assertEqual(self.qstate('2026-09-01', '2026-09-30')['state'], 'current')
        s = self.qstate('2026-09-01', '2026-09-29')
        self.assertEqual((s['state'], s['days_to_expiry']), ('expired', -1))

    def test_age_exactly_at_the_threshold_is_current_and_one_day_more_is_stale(self):
        self.assertEqual(self.qstate('2026-08-16', '2026-12-31')['state'], 'current')        # 45 days
        self.assertEqual(self.qstate('2026-08-15', '2026-12-31')['state'], 'stale')          # 46 days

    def test_a_quote_dated_after_the_as_of_day_is_not_yet_usable(self):
        self.assertEqual(self.qstate('2026-09-10', '2026-12-31', as_of='2026-09-05')['state'], 'future')         # a run as of an earlier day than the quote's issue date

    def test_expiry_outranks_staleness(self):
        self.assertEqual(self.qstate('2026-03-01', '2026-06-30')['state'], 'expired')

    def test_the_state_record_carries_the_threshold_and_age_that_decided_it(self):
        s = self.qstate('2026-09-10', '2026-10-31')
        self.assertEqual((s['age_days'], s['threshold_days'], s['valid_until'], s['class']), (20, 45, '2026-10-31', 'quote'))

    def index(self, rows, as_of='2026-09-30'):
        m = world(obs_rows=rows)
        a = m.analysis(as_of=as_of)
        return FR.index_state(a.F, 'MAT-STEEL', as_of, self.TH)

    def test_index_unavailable_when_nothing_is_stored_or_all_is_after_the_as_of_day(self):
        self.assertEqual(self.index([])['state'], 'unavailable')
        s = self.index([obs('O1', date='2026-10-20')])
        self.assertEqual((s['state'], s['observation']), ('unavailable', None))

    def test_index_fresh_at_the_threshold_and_stale_one_day_later(self):
        self.assertEqual(self.index([obs('O1', date='2026-08-16')])['state'], 'fresh')
        s = self.index([obs('O1', date='2026-08-15')])
        self.assertEqual((s['state'], s['age_days']), ('stale', 46))

    def test_a_conflicting_observation_is_held_and_never_the_latest(self):
        s = self.index([obs('O1', date='2026-09-15', value='10930'), obs('O1', date='2026-09-15', value='99999')])
        self.assertEqual((s['state'], s['held_records']), ('unavailable', 1))

    def test_the_latest_observation_on_or_before_the_as_of_day_decides(self):
        s = self.index([obs('O1', date='2026-03-01'), obs('O2', date='2026-09-15'), obs('O3', date='2026-10-15')])
        self.assertEqual((s['state'], s['observation']['date'], s['observation']['value_scaled'], s['observation']['kind']), ('fresh', '2026-09-15', 10930, 'index'))

    def test_an_index_observation_is_labelled_as_what_it_is_not_as_a_price(self):
        s = self.index([obs('O1', date='2026-09-15')])
        self.assertEqual((s['observation']['kind'], s['observation']['unit']), ('index', 'index_points_x100'))
        self.assertIn('SYNTHETIC', s['observation']['source_label'])

    def test_fx_state_from_the_conversion_age(self):
        conv = {'status': 'converted', 'from_currency': 'USD', 'rate_age_days': 30, 'rate_source_ref': 'fx_rate/x'}
        self.assertEqual(FR.fx_state(conv, self.TH)['state'], 'fresh')
        self.assertEqual(FR.fx_state(dict(conv, rate_age_days=31), self.TH)['state'], 'stale')
        self.assertEqual(FR.fx_state(dict(conv, rate_age_days=None), self.TH)['state'], 'fresh')                      # same currency
        self.assertEqual(FR.fx_state({'status': 'not_converted', 'from_currency': 'USD', 'why': 'none'}, self.TH)['state'], 'unavailable')

    def test_qualification_orders_current_qualified_historical_only(self):
        s = lambda *states: [{'state': x} for x in states]
        self.assertEqual(FR.qualification(s('current', 'fresh')), 'current')
        self.assertEqual(FR.qualification(s('current', 'stale')), 'qualified')
        self.assertEqual(FR.qualification(s('unavailable')), 'qualified')
        self.assertEqual(FR.qualification(s('stale', 'expired')), 'historical_only')
        self.assertEqual(FR.qualification(s('future')), 'historical_only')
        self.assertEqual(FR.qualification([]), 'current')

    def test_limitations_name_every_state_that_is_not_current(self):
        st = [{'subject': 'supplier_quote/Q-1', 'state': 'expired', 'days_to_expiry': -92, 'valid_until': '2026-06-30'}, {'subject': 'fx/USD', 'state': 'stale', 'age_days': 151, 'threshold_days': 30},
              {'subject': 'market_observation/O', 'state': 'unavailable'}, {'subject': 'x', 'state': 'current'}]
        out = FR.limitations(st)
        self.assertEqual(len(out), 3)
        self.assertIn('expired 92 days', out[0])
        self.assertIn('151 days old against a limit of 30', out[1])
        self.assertIn('unavailable', out[2])


class TestEvents(unittest.TestCase):
    def ev(self, **kw):
        a = dict(etype='quote_issued', subject='supplier_quote/Q-1', observed_at='2026-09-10T09:00:00Z', effective_from='2026-09-10', sources=[('supplier_quote/Q-1', 1)])
        a.update(kw)
        return EV.make(**a)

    def test_an_event_has_observation_time_effective_period_sources_and_identifiers(self):
        e = self.ev(effective_to='2026-10-31', project='PRJ-1', material='MAT-STEEL', supplier='SUP-1', detail={'class': 'comparable'})
        self.assertEqual((e['event_version'], e['type'], e['observed_at'], e['effective_from'], e['effective_to']), ('apg-event-1', 'quote_issued', '2026-09-10T09:00:00Z', '2026-09-10', '2026-10-31'))
        self.assertEqual((e['project'], e['material'], e['supplier']), ('PRJ-1', 'MAT-STEEL', 'SUP-1'))
        self.assertEqual(e['sources'], [{'ref': 'supplier_quote/Q-1', 'revision': 1}])
        self.assertTrue(e['event_id'].startswith('EV-'))
        self.assertTrue(EV.validate(e))

    def test_the_identity_is_the_content_so_the_same_event_has_the_same_id_and_a_change_changes_it(self):
        self.assertEqual(self.ev()['event_id'], self.ev()['event_id'])
        self.assertNotEqual(self.ev()['event_id'], self.ev(effective_from='2026-09-11')['event_id'])
        self.assertNotEqual(self.ev()['event_id'], self.ev(sources=[('supplier_quote/Q-1', 2)])['event_id'])

    def test_an_event_without_the_required_fields_is_refused(self):
        for kw in (dict(etype='surprise'), dict(subject=''), dict(observed_at='yesterday'), dict(effective_from='soon'), dict(effective_to='2026-09-01'), dict(sources=[]),
                   dict(sources=[('noslash', 1)]), dict(project='')):
            with self.assertRaises(EV.EventError, msg=str(kw)):
                self.ev(**kw)

    def test_a_tampered_event_fails_validation(self):
        e = self.ev()
        e['effective_from'] = '2026-01-01'
        with self.assertRaises(EV.EventError):
            EV.validate(e)

    def test_sources_are_sorted_so_their_order_does_not_change_the_event(self):
        a = self.ev(sources=[('b/1', 1), ('a/1', 2)])
        b = self.ev(sources=[('a/1', 2), ('b/1', 1)])
        self.assertEqual(a['event_id'], b['event_id'])


if __name__ == '__main__':
    unittest.main()
