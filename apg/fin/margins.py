"""Recognised margin and margin percentages.  Blueprint: Section 03 sections 5.1 and 6.3; Section 05 sections 5, 6, 12; PG-PC-AC-01, 14, 15.

  Recognised margin = recognised revenue - recognised cost, at the forecast date, where recognised cost is the actual cost to that date and recognised revenue is the secured
  revenue earned in proportion to cost incurred ('cost_to_cost': secured revenue x actual cost / forecast final cost, exact integers, rounded once).  The policy's
  recognition_method is the only thing that selects this (CR-02 A5); with none configured there is no figure.  Cash received is never used.
  Because the proportion rests on a forecast final cost, the figure is only as good as that forecast: when the forecast is provisional the recognised margin is too, and says
  so.  A zero or negative revenue or forecast cost gives 'cannot be assessed' for the percentage, never a zero or an error."""
from . import policy as P
from .figure import FigureBuilder, CANT
from .fmath import bps_of, round_div
from .forecast import build_forecast


def build_recognised(F, project, as_of):
    pol = F.policy
    b = FigureBuilder('recognised_margin', 'recognised', 'fin.recognised_margin', 1, {'project': project}, as_of, pol)
    if pol is None:
        return b.cannot('POLICY_NOT_PINNED')
    if pol.get('recognition_method') is None:
        return b.cannot('RECOGNITION_METHOD_NOT_CONFIGURED', P.OPEN_DECISIONS['recognition_method'])
    fc = build_forecast(F, project, as_of)
    b.child('forecast_basis', fc)
    c = fc['classified']
    if fc['state'] == CANT or c.get('ffc_cents') is None:
        return b.cannot('FORECAST_BASIS_CANNOT_BE_ASSESSED')
    revenue, actual, ffc = c['ffr_cents'], c['actual_cents'], c['ffc_cents']
    if ffc <= 0:
        return b.cannot('FORECAST_FINAL_COST_NOT_POSITIVE')
    if revenue <= 0:
        return b.cannot('REVENUE_NOT_POSITIVE')
    recognised_revenue = round_div(revenue * actual, ffc)
    b.classify('method', pol['recognition_method'])
    b.classify('recognised_revenue_cents', recognised_revenue)
    b.classify('recognised_cost_cents', actual)
    b.classify('percent_complete_bps', bps_of(actual, ffc))
    b.classify('recognised_at', c['forecast_date'])
    b.reason('PERCENT_COMPLETE_IS_COST_TO_COST_ON_THE_FORECAST_FINAL_COST')
    if fc['state'] != 'authoritative':
        b.reason('PERCENT_COMPLETE_RESTS_ON_A_FORECAST_THAT_IS_' + fc['state'].upper())
    b.limit('recognised at the forecast date; the policy and source data identify the progress-recognition basis; the system does not assert accounting-standard compliance')
    return b.finish(cents=recognised_revenue - actual)


def pct_figure(name, margin_fig, revenue_cents, denominator_label):
    """Margin as a percentage of revenue, in basis points.  Cannot be assessed when the margin cannot, or when the revenue is zero or negative."""
    b = FigureBuilder(name, margin_fig['view'], 'fin.margin_pct', 1, margin_fig['scope'], margin_fig['as_of'], {'version': margin_fig['policy']['version'], '_approved': margin_fig['policy']['approved']})
    b.child('margin', margin_fig)
    if margin_fig['value']['cents'] is None:
        return b.cannot('MARGIN_CANNOT_BE_ASSESSED')
    if revenue_cents is None:
        return b.cannot(denominator_label + '_UNKNOWN')
    bps = bps_of(margin_fig['value']['cents'], revenue_cents)
    if bps is None:
        return b.cannot('NOT_APPLICABLE_REVENUE_ZERO_OR_NEGATIVE')
    return b.finish(bps=bps)
