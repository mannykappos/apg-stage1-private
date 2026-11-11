"""The assessment entry point for the AUIF path: the gate FIRST, then the financial core and detection, then the gate again.

When the gate says cannot_assess, the answer is {'status': 'cannot_assess', 'reasons': [...], 'figures': None, 'signals': None}: no figure is computed, and no earlier
figure is returned in its place.  Earlier stored calculations stay where they always were (repro records, each with the as-of date and the exact revisions it pinned); this
function never presents one of them as current.  If anything the gate reads changes while the figures are computed, the result is withdrawn the same way (CHANGED_DURING_RUN).
Nothing here changes how a figure is computed: the calculations are the existing ones (apg.fin.calc_records.run_calc, apg.det.detect.run_project)."""
from apg.det import detect as D
from apg.fin import calc_records as C
from . import gate as G

FIGURES = (('actual_cost', 'fin.actual_cost', None), ('commitments', 'fin.commitments', None), ('revenue', 'fin.revenue', None), ('forecast', 'fin.forecast', None),
           ('recognised_margin', 'fin.recognised_margin', None), ('cash_adjusted', 'fin.cash_adjusted', None), ('retention', 'fin.cash_position', {'what': 'retention'}),
           ('security', 'fin.cash_position', {'what': 'security'}), ('retention_carrying', 'fin.cash_position', {'what': 'retention_carrying'}))


def _refused(scoped, project, as_of, now, reasons):
    scoped.log('auif.assessment', str(project), 'cannot_assess', reason=reasons[0]['code'], detail={'codes': sorted({r['code'] for r in reasons})[:20]})
    return {'status': G.CANNOT, 'project': project, 'as_of': as_of, 'checked_at': now, 'reasons': reasons, 'figures': None, 'signals': None, 'run_keys': []}


def run_assessment(scoped, clock, expected, project, as_of, fin_policy_version, det_policy_version, module=None):
    now = clock.now()
    g = G.assessment_status(scoped, expected, module)
    if g['status'] != G.CAN:
        return _refused(scoped, project, as_of, now, g['reasons'])
    reg, figures, keys = C.fin_registry(), {}, []
    for name, fid, extra in FIGURES:
        rec = C.run_calc(scoped, reg, clock, fid, project, as_of, fin_policy_version, extra)
        figures[name], _ = rec['result'], keys.append(rec['run_key'])
    det = D.run_project(scoped, D.det_registry(), clock, project, as_of, fin_policy_version, det_policy_version)
    keys.append(det['run_key'])
    g2 = G.assessment_status(scoped, expected, module)
    if g2 != g:
        return _refused(scoped, project, as_of, now, g2['reasons'] or [{'code': 'CHANGED_DURING_RUN', 'scope': '-', 'detail': 'what the gate reads changed while the figures were computed'}])
    return {'status': 'assessed', 'project': project, 'as_of': as_of, 'checked_at': now, 'reasons': [], 'figures': figures, 'signals': det['result']['signals'],
            'rule_runs': det['result']['rule_runs'], 'run_keys': keys}
