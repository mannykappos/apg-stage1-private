"""The signal contract (Blueprint Section 06 sections 6 to 8): every rule of the contract has a test that breaks exactly that rule and requires the specific refusal.  After each alteration the
identity and the material-change digest are recomputed, so the refusal can only come from the rule under test (not from the identity or digest check that comes later)."""
import copy
import unittest
from . import _path                                         # noqa: F401
from apg.det import signal as S

RULE = {'id': 'DET-X', 'version': 1, 'params': {'tolerance_bps': 500}}
SCOPE = {'level': 'project', 'project': 'PRJ-001'}


def sig(interp='forecast_exposure', quant=None, evid=None, strength='strong', **kw):
    q = quant or S.quantified(100, 'basis text', 'calc/ref', ['an assumption'], label='estimate')
    ev = evid if evid is not None else [S.evidence('ap_invoice/INV-1', 1, 'source')]
    return S.make(RULE, SCOPE, 'subject-1', 'cost_commitments', 'a_subtype', interp, ev, 'observed text', 'expected text', 'reason text', q, strength, **kw)


def refresh(s):
    try:
        s['identity'] = S.identity_of(s['rule']['id'], s['scope'], s['subject'])
        s['state_digest'] = S.state_digest(s)
    except (KeyError, TypeError):
        pass
    return s


class TestContract(unittest.TestCase):
    def bad(self, change, pattern, base=None):
        s = copy.deepcopy(base or sig())
        change(s)
        refresh(s)
        with self.assertRaisesRegex(S.SignalError, pattern):
            S.validate_signal(s)

    def test_a_well_formed_signal_is_accepted_and_an_unquantified_one_too(self):
        self.assertTrue(S.validate_signal(sig()))
        self.assertTrue(S.validate_signal(sig(quant=S.unquantified('no defensible amount'))))
        self.assertTrue(S.validate_signal(sig(quant=S.quantified(100, 'b', 'c', incremental_cents=40, net_cents=60, label='record'))))

    def test_something_that_is_not_a_signal_or_has_another_version_is_refused(self):
        for bad in (None, 'text', [1], 5):
            with self.assertRaisesRegex(S.SignalError, 'signal version'):
                S.validate_signal(bad)
        self.bad(lambda s: s.update(signal_version='apg-signal-0'), 'signal version')

    def test_the_rule_must_be_identified_by_a_text_id_a_whole_number_version_and_its_parameters(self):
        for change in (lambda s: s['rule'].update(id=''), lambda s: s['rule'].update(id=5), lambda s: s['rule'].update(version=0), lambda s: s['rule'].update(version=True),
                       lambda s: s['rule'].update(version='1'), lambda s: s['rule'].update(params=[])):
            self.bad(change, 'rule identification')

    def test_the_scope_must_be_a_project_with_its_name_or_the_tenant(self):
        self.bad(lambda s: s['scope'].update(level='galaxy'), 'scope')
        self.bad(lambda s: s['scope'].update(project=''), 'scope')
        self.bad(lambda s: s['scope'].pop('project'), 'scope')
        t = S.make(RULE, {'level': 'tenant', 'project': None}, 'q', 'suppliers_compliance', 'a', 'compliance_risk', [S.evidence('supplier_compliance/S-1', 1)], 'o', 'e', 'r', S.unquantified('none'), 'weak')
        self.assertTrue(S.validate_signal(t))

    def test_the_family_and_the_subtype_and_the_interpretation_must_be_known(self):
        self.bad(lambda s: s['taxonomy'].update(family='misc'), 'taxonomy')
        self.bad(lambda s: s['taxonomy'].update(subtype=''), 'taxonomy')
        self.bad(lambda s: s.update(interpretation='windfall'), 'interpretation')

    def test_a_signal_must_rest_on_stored_records_that_are_named_properly(self):
        self.bad(lambda s: s.update(evidence=[]), 'at least one stored record')
        self.bad(lambda s: s['evidence'][0].update(ref=5), 'evidence reference')
        self.bad(lambda s: s['evidence'][0].update(ref='no-slash'), 'evidence reference')
        self.bad(lambda s: s['evidence'][0].update(role=''), 'evidence reference')

    def test_the_explanation_needs_what_was_seen_what_was_expected_and_why(self):
        for k in ('observed', 'expected', 'reason'):
            self.bad(lambda s, k=k: s['explanation'].update({k: ''}), 'explanation needs')
            self.bad(lambda s, k=k: s['explanation'].update({k: '   '}), 'explanation needs')
            self.bad(lambda s, k=k: s['explanation'].update({k: 5}), 'explanation needs')
            self.bad(lambda s, k=k: s['explanation'].pop(k), 'explanation needs')

    def test_a_quantified_signal_needs_a_whole_number_amount_a_basis_a_calculation_and_a_known_label(self):
        for v in ('5', True, 5.0, None):
            self.bad(lambda s, v=v: s['quantification'].update(gross_cents=v), 'whole-number gross')
        for k in ('incremental_cents', 'net_cents'):
            for v in ('5', True):
                self.bad(lambda s, k=k, v=v: s['quantification'].update({k: v}), k)
        self.bad(lambda s: s['quantification'].update(basis=''), 'names its basis')
        self.bad(lambda s: s['quantification'].update(calculation_ref=''), 'names its basis')
        self.bad(lambda s: s['quantification'].update(label='guess'), 'amount label')

    def test_an_unquantified_signal_says_why_and_carries_no_amount(self):
        base = sig(quant=S.unquantified('no counterfactual'))
        self.bad(lambda s: s['quantification'].update(reason=''), 'says why', base)
        self.bad(lambda s: s['quantification'].update(reason='  '), 'says why', base)
        self.bad(lambda s: s['quantification'].update(gross_cents=5), 'says why', base)
        self.bad(lambda s: s['quantification'].update(status='maybe'), 'quantification status', base)

    def test_a_data_quality_operational_or_compliance_signal_never_carries_a_financial_figure(self):
        for interp in S.NO_FINANCIAL_CLAIM:
            self.bad(lambda s, i=interp: s.update(interpretation=i), 'does not carry a financial figure', sig(quant=S.quantified(100, 'b', 'c', label='figure')))
            self.assertTrue(S.validate_signal(sig(interp, quant=S.quantified(100, 'b', 'c', label='record'))))        # a recorded amount is allowed
            self.assertTrue(S.validate_signal(sig(interp, quant=S.quantified(100, 'b', 'c', label='estimate'))))
            self.assertTrue(S.validate_signal(sig(interp, quant=S.unquantified('why'))))

    def test_only_an_amount_from_a_stored_calculation_can_be_called_an_actual_loss(self):
        self.assertTrue(S.validate_signal(sig('actual_loss', quant=S.quantified(100, 'b', 'c', label='figure'))))
        for q in (S.quantified(100, 'b', 'c', label='estimate'), S.quantified(100, 'b', 'c', label='record'), S.unquantified('why')):
            s = copy.deepcopy(sig(quant=q))
            s['interpretation'] = 'actual_loss'
            refresh(s)
            with self.assertRaisesRegex(S.SignalError, 'actual loss'):
                S.validate_signal(s)

    def test_the_evidence_strength_and_the_severity_must_be_valid(self):
        self.bad(lambda s: s['confidence'].update(evidence_strength='certain'), 'evidence strength')
        self.bad(lambda s: s['priority'].update(severity=''), 'severity')
        self.bad(lambda s: s['priority'].update(severity=None), 'severity')
        for sev in ('unrated', 'low', 'high'):
            s = copy.deepcopy(sig())
            s['priority']['severity'] = sev
            refresh(s)
            self.assertTrue(S.validate_signal(s))

    def test_the_identity_and_the_digest_must_match_the_content(self):
        s = copy.deepcopy(sig())
        s['identity'] = 'FND-0000'
        with self.assertRaisesRegex(S.SignalError, 'identity does not match'):
            S.validate_signal(s)
        s = copy.deepcopy(sig())
        s['state_digest'] = '0' * 24
        with self.assertRaisesRegex(S.SignalError, 'state digest does not match'):
            S.validate_signal(s)
        s = copy.deepcopy(sig())
        s['subject'] = 'another'
        with self.assertRaisesRegex(S.SignalError, 'identity does not match'):
            S.validate_signal(s)

    def test_floats_and_non_json_content_are_refused(self):
        s = copy.deepcopy(sig())
        s['extra'] = {'x': 1.5}
        refresh(s)
        with self.assertRaises(Exception):
            S.validate_signal(s)


class TestBuildingBlocks(unittest.TestCase):
    def test_evidence_carries_a_reconciliation_state_and_a_note_only_when_given(self):
        self.assertEqual(S.evidence('a/1', 2), {'ref': 'a/1', 'revision': 2, 'role': 'source'})
        self.assertEqual(S.evidence('a/1', 2, 'basis', 'authoritative', 'why'), {'ref': 'a/1', 'revision': 2, 'role': 'basis', 'reconciliation': 'authoritative', 'note': 'why'})
        self.assertEqual(S.evidence('a/1', 2, recon='held'), {'ref': 'a/1', 'revision': 2, 'role': 'source', 'reconciliation': 'held'})
        self.assertEqual(S.evidence('a/1', 2, note='n'), {'ref': 'a/1', 'revision': 2, 'role': 'source', 'note': 'n'})

    def test_evidence_is_sorted_by_reference_then_revision_with_no_revision_first_then_role(self):
        ev = [S.evidence('a/1', 3), S.evidence('a/1', None), S.evidence('a/1', 1), S.evidence('a/0', 9), S.evidence('a/1', 1, 'basis')]
        s = sig(evid=ev)
        self.assertEqual([(e['ref'], e['revision'], e['role']) for e in s['evidence']], [('a/0', 9, 'source'), ('a/1', None, 'source'), ('a/1', 1, 'basis'), ('a/1', 1, 'source'), ('a/1', 3, 'source')])

    def test_the_digest_changes_with_what_is_material_and_not_with_the_amount(self):
        a = sig()
        b = sig(quant=S.quantified(999, 'basis text', 'calc/ref', ['an assumption'], label='estimate'))
        self.assertEqual(a['state_digest'], b['state_digest'])                     # a drifting amount is not a material change
        c = sig(evid=[S.evidence('ap_invoice/INV-1', 2)])
        self.assertNotEqual(a['state_digest'], c['state_digest'])                  # a new revision of the evidence is
        d = sig(strength='weak')
        self.assertNotEqual(a['state_digest'], d['state_digest'])
        e = sig(limits=['a limit'])
        self.assertNotEqual(a['state_digest'], e['state_digest'])
        f = sig(urgency={'time_sensitive': True, 'date': '2026-10-01', 'basis': 'b'})
        self.assertNotEqual(a['state_digest'], f['state_digest'])
        self.assertNotEqual(a['state_digest'], S.with_severity(a, 'high')['state_digest'])
        self.assertNotEqual(a['state_digest'], sig(quant=S.unquantified('why'))['state_digest'])

    def test_the_identity_depends_on_rule_scope_and_subject_only(self):
        a = S.identity_of('DET-X', SCOPE, 's')
        self.assertEqual(a, S.identity_of('DET-X', dict(SCOPE), 's'))
        self.assertNotEqual(a, S.identity_of('DET-Y', SCOPE, 's'))
        self.assertNotEqual(a, S.identity_of('DET-X', {'level': 'project', 'project': 'PRJ-002'}, 's'))
        self.assertNotEqual(a, S.identity_of('DET-X', SCOPE, 't'))
        self.assertTrue(a.startswith('FND-') and len(a) == 24)


if __name__ == '__main__':
    unittest.main()
