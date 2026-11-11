#!/usr/bin/env python3
"""APG-M10 sabotage: each case breaks one promise of the prototype on a PRIVATE COPY of this package and runs the one check that should catch it.  A case passes only if that check
FAILS on the broken copy (and the same check passes on an unbroken copy first: the control).  Nothing in this package is changed.  Synthetic data only.
Usage: python3 -I tools/sabotage_m10.py [--list] [--only K01,K02]     Needs Node and Playwright for the U cases (see ui_tests/run_ui_tests.js)."""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = 'tests_m10.test_m10_viewmodel.'
VM, JS, CSS = 'apg_ui/viewmodel.py', 'ui/app.js', 'ui/app.css'

# (id, what is broken, file, old text, new text, check: ('py', test id) or ('ui', test group))
CASES = [
    ('V01', 'a provisional figure is shown as authoritative', VM, "num((fig.get('value') or {}).get('cents'), fig['state'], 'figure', ev)",
     "num((fig.get('value') or {}).get('cents'), 'authoritative' if fig['state'] == 'provisional' else fig['state'], 'figure', ev)",
     ('py', T + 'TestEveryAmountIsAnApgValueWithItsEvidence.test_every_project_figure_equals_a_fresh_apg_calculation_in_value_and_state')),
    ('V02', 'a figure that cannot be assessed is shown as zero', VM, "num((fig.get('value') or {}).get('cents'), fig['state'], 'figure', ev)",
     "num(0 if fig['state'] == 'cannot_assess' else (fig.get('value') or {}).get('cents'), fig['state'], 'figure', ev)",
     ('py', T + 'TestEveryAmountIsAnApgValueWithItsEvidence.test_a_figure_that_cannot_be_assessed_has_no_value_and_says_why')),
    ('V03', 'an unestimated net benefit is shown as an amount', VM, "num(net.get('cents'), None, 'estimate', ev) if net.get('status') == 'estimated' else num(None, None, 'none', ev)",
     "num(net.get('cents') or mag.get('cents'), None, 'estimate', ev)",
     ('py', T + 'TestNoEstimateIsARealisedSaving.test_an_estimated_net_benefit_is_shown_only_when_apg_estimated_it_and_is_labelled_estimate')),
    ('V04', 'the port is asked about the project but tenant-level grants are assumed', VM, "        where = scope.get('project') if scope.get('level') == 'project' else TENANT\n        return action in self.g.get((ctx.tenant_id, ctx.user_id, where), ())",
     "        where = scope.get('project') if scope.get('level') == 'project' else TENANT\n        return True if where == TENANT and action == 'view' else action in self.g.get((ctx.tenant_id, ctx.user_id, where), ())",
     ('py', T + 'TestWhatEachPersonMaySee.test_the_project_manager_sees_only_prj_001_and_no_builder_wide_material')),
    ('V05', 'the request carries a digest other than the one present() gave', VM, "'digest': tk['digest'],", "'digest': tk['digest'][::-1],",
     ('py', T + 'TestApprovals.test_the_request_the_screen_would_send_is_exactly_the_token_present_gave')),
    ('V06', 'a scenario total is labelled as an estimate of a saving', VM, "'landed_total': num(x.get('landed_total_cents'), None, 'scenario', ev)", "'landed_total': num(x.get('landed_total_cents'), None, 'saving', ev)",
     ('py', T + 'TestNoEstimateIsARealisedSaving.test_scenarios_never_change_the_forecast_and_are_labelled_scenario')),
    ('V07', 'the stored data file is edited by hand', 'ui/data/views.js', 'window.APG_VIEWS = {', 'window.APG_VIEWS = {"edited": 1, ',
     ('py', T + 'TestTheStoredFileIsTheBuild.test_ui_data_views_js_equals_a_fresh_build_byte_for_byte')),
    ('V08', 'the screen code calls the network', JS, "  function onApprove(form) {", "  function onApprove(form) {\n    fetch('approve');",
     ('py', T + 'TestThePagesSendNothing.test_the_prototype_code_has_no_network_call_and_loads_only_local_files')),
    ('U01', 'a figure that cannot be assessed is drawn as $0', JS, "      if (st === 'cannot_assess') {", "      if (st === 'cannot_assess') { return '<button type=\"button\" class=\"num\" data-state=\"cannot_assess\"' + ev + '>$0</button>';",
     ('ui', 'amounts')),
    ('U02', 'the provisional mark is dropped', JS, "    if (st === 'provisional') mark = '<span class=\"mark\">provisional</span>';", "    if (st === 'provisional') mark = '';", ('ui', 'ledger')),
    ('U03', 'the ledger gains a total row', JS, "'</tbody><tfoot><tr><td colspan=\"' + (FIGCOLS.length + 3) + '\">No totals.",
     "'<tr><th scope=\"row\">Total</th></tr></tbody><tfoot><tr><td colspan=\"' + (FIGCOLS.length + 3) + '\">No totals.", ('ui', 'ledger')),
    ('U04', 'an amount is drawn as plain text, not as a link to its evidence', JS, "    var shown = count ? INT.format(n.cents) : dollars(n.cents);",
     "    var shown = count ? INT.format(n.cents) : dollars(n.cents);\n    if (!count && st === 'authoritative') return '<span>' + esc(shown) + '</span>';", ('ui', 'amounts')),
    ('U05', 'the approval form shows a digest other than the token', JS, "'<dt>Evidence digest</dt><dd data-k=\"digest\" class=\"code\">' + esc(rq.digest)",
     "'<dt>Evidence digest</dt><dd data-k=\"digest\" class=\"code\">' + esc(rq.digest.slice(1))", ('ui', 'approvals')),
    ('U06', 'Escape no longer closes the evidence drawer', JS, "    if (ev.key === 'Escape') { ev.preventDefault(); closeDrawer(); return; }", "    if (ev.key === 'Escape') { return; }", ('ui', 'drawer')),
    ('U07', 'secondary text loses its contrast', CSS, "  --ink-2: #4a5553;", "  --ink-2: #b4bab8;", ('ui', 'screens')),
    ('U08', 'a screen claims a saving', JS, "'<h1>Buy-timing for '", "'<p>Saving achieved this month.</p><h1>Buy-timing for '", ('ui', 'savings')),
    ('U09', 'the project manager is shown the whole ledger', JS, "    V = M.views[r.view];", "    V = M.views[r.view].person.user === 'pat' ? M.views[M.meta.order[0]] : M.views[r.view];", ('ui', 'access')),
    ('U11', 'a finding row shows its amount without the evidence button behind it', JS, "'</span></summary><div class=\"body\"><dl><dt>Amount</dt><dd>' + num(f.amount, f.kind + ' on ' + f.subject)",
     "'</span></summary><div class=\"body\"><dl><dt>Amount</dt><dd>' + amountText(f.amount)", ('ui', 'amounts')),
    ('U10', 'the page is wider than a phone', CSS, "main { padding: var(--s6) var(--s6) var(--s7); min-width: 0; }", "main { padding: var(--s6) var(--s6) var(--s7); min-width: 900px; }", ('ui', 'mobile')),
]


def run_check(root, check):
    kind, what = check
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    if kind == 'py':
        r = subprocess.run([sys.executable, '-B', '-W', 'ignore', '-m', 'unittest', what], cwd=root, capture_output=True, text=True, env=env, timeout=1800)
    else:
        r = subprocess.run(['node', os.path.join(root, 'ui_tests', 'run_ui_tests.js'), '--only', what], cwd=root, capture_output=True, text=True, env=env, timeout=1800)
    return r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1:]


def private_copy():
    d = tempfile.mkdtemp(prefix='apg_m10_sab_')
    dst = os.path.join(d, 'APG_M10')
    keep = ('apg', 'apg_ui', 'apg_auif', 'auif_m8', 'builder_zero', 'mkt_data', 'ui', 'ui_tests', 'tests_m10', 'third_party', 'tools', 'data', 'reference', 'import_templates',
            'ingest_templates', 'fin_templates', 'det_templates', 'mkt_templates', 'catalogue')
    os.makedirs(dst)
    for k in keep:
        if os.path.isdir(os.path.join(ROOT, k)):
            shutil.copytree(os.path.join(ROOT, k), os.path.join(dst, k), ignore=shutil.ignore_patterns('__pycache__'))
    return d, dst


def main():
    a = sys.argv[1:]
    if '--list' in a:
        for c in CASES:
            print(c[0], c[1], '->', c[5][1])
        return 0
    want = set(a[a.index('--only') + 1].split(',')) if '--only' in a else None
    d, dst = private_copy()
    try:
        controls, caught = {}, []
        for cid, what, f, old, new, check in CASES:
            if want and cid not in want:
                continue
            if check not in controls:
                controls[check] = run_check(dst, check)
                print('control %-6s %s: %s' % (check[0], check[1].split('.')[-1], 'passes on the unbroken copy' if controls[check][0] else 'FAILS ON THE UNBROKEN COPY %s' % controls[check][1]), flush=True)
            p = os.path.join(dst, f)
            text = open(p, encoding='utf-8').read()
            if text.count(old) != 1:
                print('ERROR %s: the text to break was found %d times in %s' % (cid, text.count(old), f))
                caught.append((cid, False))
                continue
            open(p, 'w', encoding='utf-8').write(text.replace(old, new))
            try:
                ok, tail = run_check(dst, check)
            finally:
                open(p, 'w', encoding='utf-8').write(text)
            good = controls[check][0] and not ok
            caught.append((cid, good))
            print('%s %s %s (%s) %s' % ('CAUGHT' if good else 'MISSED', cid, what, check[1].split('.')[-1], '' if good else tail), flush=True)
        n = sum(1 for _, g in caught if g)
        print('\nsabotage %d  caught %d' % (len(caught), n))
        return 0 if n == len(caught) else 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
