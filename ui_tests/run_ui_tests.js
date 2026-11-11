#!/usr/bin/env node
/* APG-M10 browser tests of the prototype screens (ui/index.html), in headless Chromium through Playwright, with axe-core (vendored, ui_tests/vendor/axe.min.js) for
   accessibility. Synthetic data only. The page is opened from the file system: no server, no network; any request that is not a local file fails the run.
   Usage: node ui_tests/run_ui_tests.js [--shots DIR] [--only NAME]
   Needs the npm package "playwright" (found by require, or set PLAYWRIGHT_MODULE to its folder) and a Chromium it can launch. Exit 0 only if every check passed. */
'use strict';
const path = require('path');
const fs = require('fs');
let pw;
try { pw = require(process.env.PLAYWRIGHT_MODULE || 'playwright'); } catch (e) { pw = require('/opt/npm-tools/node_modules/playwright'); }
const ROOT = path.resolve(__dirname, '..');
const PAGE = 'file://' + path.join(ROOT, 'ui', 'index.html');
const AXE = fs.readFileSync(path.join(__dirname, 'vendor', 'axe.min.js'), 'utf8');
const args = process.argv.slice(2);
const SHOTS = args.includes('--shots') ? path.resolve(args[args.indexOf('--shots') + 1]) : null;
const ONLY = args.includes('--only') ? args[args.indexOf('--only') + 1] : null;
const DATA = (() => { const t = fs.readFileSync(path.join(ROOT, 'ui', 'data', 'views.js'), 'utf8'); return JSON.parse(t.slice(t.indexOf('= ') + 2).trim().replace(/;$/, '')); })();
const VIEWS = DATA.meta.order;
const SCREENS = ['portfolio', 'project', 'health', 'imports', 'approvals', 'materials'];
const AUD0 = new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0, minimumFractionDigits: 0 });
const dollars = c => AUD0.format(Math.round(c / 100));
const results = [];
function check(name, ok, detail) { results.push([name, !!ok, detail]); console.log((ok ? 'PASS ' : 'FAIL ') + name + (ok || detail === undefined ? '' : '  ' + JSON.stringify(detail).slice(0, 400))); }

async function open(browser, view, screen, opts) {
  opts = opts || {};
  const ctx = await browser.newContext({ viewport: opts.viewport || { width: 1360, height: 900 }, colorScheme: opts.dark ? 'dark' : 'light', deviceScaleFactor: opts.dsf || 1 });
  const page = await ctx.newPage();
  const problems = [];
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') problems.push(m.type() + ': ' + m.text()); });
  page.on('pageerror', e => problems.push('pageerror: ' + e));
  page.on('request', r => { if (!r.url().startsWith('file://')) problems.push('request: ' + r.url()); });
  await page.goto(PAGE + '#/' + view + '/' + screen + (opts.arg ? '/' + opts.arg : ''));
  await page.waitForSelector('.screen[data-screen="' + screen + '"]');
  await page.evaluate(() => document.fonts.ready);
  return { page, ctx, problems };
}
async function axe(page) {
  await page.addScriptTag({ content: AXE });
  return page.evaluate(async () => {
    const r = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'] }, resultTypes: ['violations'], preload: false });
    return r.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, first: v.nodes[0] && v.nodes[0].target.join(' ') }));
  });
}
async function shot(page, name, full) { if (SHOTS) { fs.mkdirSync(SHOTS, { recursive: true }); await page.screenshot({ path: path.join(SHOTS, name + '.png'), fullPage: full !== false }); } }

const TESTS = {
  /* Every screen of every view renders, with no console error, no request leaving the machine, and no axe violation, in light and in dark. */
  async screens(b) {
    for (const v of VIEWS) for (const s of SCREENS) for (const dark of [false, true]) {
      const { page, ctx, problems } = await open(b, v, s, { dark });
      const viol = await axe(page);
      check(`screen ${v} ${s} ${dark ? 'dark' : 'light'}: renders with no console error or outside request`, problems.length === 0, problems);
      check(`screen ${v} ${s} ${dark ? 'dark' : 'light'}: no axe violation`, viol.length === 0, viol);
      if (!dark || v === VIEWS[0]) await shot(page, `${v}__${s}${dark ? '__dark' : ''}`);
      await ctx.close();
    }
  },
  /* Every amount on every screen is a button that names an evidence entry of this view, and a missing value is never drawn as a number. */
  async amounts(b) {
    for (const v of VIEWS) for (const s of SCREENS) {
      const { page, ctx } = await open(b, v, s);
      const r = await page.evaluate(view => {
        const ev = window.APG_VIEWS.views[view].evidence;
        const bad = [], nums = document.querySelectorAll('.num');
        nums.forEach(n => {
          if (n.tagName !== 'BUTTON') bad.push('not a button: ' + n.outerHTML.slice(0, 80));
          const id = n.getAttribute('data-ev');
          if (!id || !ev[id]) bad.push('no evidence: ' + n.textContent);
          const st = n.getAttribute('data-state');
          if ((st === 'cannot_assess' || st === 'none') && /\d/.test(n.textContent)) bad.push('a missing value shows a digit: ' + n.textContent);
          if (n.getAttribute('data-label') === 'estimate' && !/estimate/.test(n.textContent) && !n.closest('td') ) bad.push('estimate without its mark: ' + n.textContent);
        });
        const loose = [];
        document.querySelectorAll('.screen td, .screen th, .screen dd, .screen li, .screen .cell .v, .screen .lede, .screen p').forEach(el => {
          if (el.closest('summary') || el.closest('pre') || el.closest('.drawer')) return;
          const c = el.cloneNode(true);
          c.querySelectorAll('button.num, summary').forEach(x => x.remove());
          if (/\$\s?\d/.test(c.textContent)) loose.push(c.textContent.trim().slice(0, 60));
        });
        document.querySelectorAll('summary .sum-amt').forEach(sa => {             /* a summary may not hold a button: its amount must be repeated as a button in the row */
          const txt = sa.textContent.split(' ')[0];
          const inRow = Array.from(sa.closest('details').querySelectorAll('.body button.num')).some(x => x.textContent.startsWith(txt));
          if (!inRow) loose.push('summary amount with no evidence button in its row: ' + txt);
        });
        return { n: nums.length, bad, loose };
      }, v);
      check(`amounts ${v} ${s}: every amount opens its evidence; no missing value drawn as a number`, r.bad.length === 0, r.bad.slice(0, 5));
      check(`amounts ${v} ${s}: no dollar amount outside an evidence button`, r.loose.length === 0, r.loose.slice(0, 5));
      await ctx.close();
    }
  },
  /* The portfolio ledger shows exactly the APG values of the data file, whole dollars, with each figure's standing. */
  async ledger(b) {
    for (const v of VIEWS) {
      const { page, ctx } = await open(b, v, 'portfolio');
      const cells = await page.$$eval('tbody tr', rows => rows.map(r => Array.from(r.querySelectorAll('td button.num')).map(x => ({ state: x.getAttribute('data-state'), text: x.textContent, ev: x.getAttribute('data-ev') }))));
      const want = DATA.views[v].projects.map(p => [p.contract_value].concat(['recognised_margin', 'forecast_final_margin', 'cost_to_complete', 'cash_adjusted_margin', 'retention_withheld'].map(k => p.figures[k])));
      const bad = [];
      want.forEach((row, i) => row.forEach((f, j) => {
        const c = (cells[i] || [])[j];
        if (!c) { bad.push(['missing', i, j]); return; }
        if (c.ev !== f.ev) bad.push(['evidence', i, j]);
        if (f.cents === null) { if (!/Cannot assess/.test(c.text)) bad.push(['should say cannot assess', i, j, c.text]); }
        else if (!c.text.startsWith(dollars(f.cents))) bad.push(['value', i, j, c.text, dollars(f.cents)]);
        if ((f.state || 'none') !== c.state && !(f.state === undefined && c.state === 'none')) bad.push(['state', i, j, c.state, f.state]);
        if (f.state === 'provisional' && !/provisional/.test(c.text)) bad.push(['no provisional mark', i, j]);
      }));
      check(`ledger ${v}: every cell is the APG value, rounded to the dollar, with its state and evidence`, bad.length === 0, bad);
      const t = await page.evaluate(() => { const tb = document.querySelector('section[aria-labelledby="h-ledger"] table');
        return { rows: tb.querySelectorAll('tbody tr').length, cols: tb.querySelectorAll('thead th').length,
                 total: Array.from(tb.querySelectorAll('th, td')).filter(c => !c.closest('tfoot') && /^\s*(grand\s+)?(sub)?totals?\b/i.test(c.textContent)).length }; });
      check(`ledger ${v}: one row per visible project and no total row or column`, t.rows === DATA.views[v].projects.length && t.cols === 8 && t.total === 0, t);
      await ctx.close();
    }
  },
  /* Words: no screen claims a saving; every sentence that mentions one denies it. */
  async savings(b) {
    for (const v of VIEWS) for (const s of SCREENS) {
      const { page, ctx } = await open(b, v, s);
      const text = await page.evaluate(() => document.body.innerText);
      const hits = text.split(/(?<=[.;:!?])\s+|\n/).filter(x => /\bsav(ed|ing|ings)\b|\brealis(ed|e)\b/i.test(x) && !/\b(no|not|never|nothing|until|only after|counts as realised only)\b/i.test(x));
      check(`words ${v} ${s}: no sentence claims a saving or a realised amount`, hits.length === 0, hits);
      await ctx.close();
    }
  },
  /* The evidence drawer: opens from a click or the keyboard, shows the entry, traps focus, closes with Escape and returns focus. */
  async drawer(b) {
    const { page, ctx, problems } = await open(b, VIEWS[0], 'portfolio');
    const btn = page.locator('button.num.cannot_assess').first();
    await btn.focus();
    await page.keyboard.press('Enter');
    await page.waitForSelector('.drawer');
    const r = await page.evaluate(() => ({ title: document.getElementById('ev-title').textContent, focus: document.activeElement.id, text: document.querySelector('.drawer').innerText }));
    check('drawer: opens from the keyboard and moves focus to its title', r.focus === 'ev-title', r);
    check('drawer: a figure that cannot be assessed shows its reasons and no value', /No value: Cannot assess/.test(r.text) && /Reasons APG gave/.test(r.text) && /A_DEFINED_COMPONENT_CANNOT_BE_ASSESSED/.test(r.text), r.text.slice(0, 300));
    await shot(page, 'evidence_drawer_cannot_assess', false);
    for (let i = 0; i < 40; i++) await page.keyboard.press('Tab');
    const inside = await page.evaluate(() => !!document.activeElement.closest('.drawer'));
    check('drawer: Tab keeps focus inside the open drawer', inside);
    await page.keyboard.press('Escape');
    const back = await page.evaluate(() => ({ open: !!document.querySelector('.drawer'), cls: document.activeElement.className }));
    check('drawer: Escape closes it and returns focus to the amount', !back.open && /num/.test(back.cls), back);
    await page.locator('tbody tr').nth(1).locator('td').nth(2).locator('button.num').click();
    const t2 = await page.locator('.drawer').innerText();
    const f = DATA.views[VIEWS[0]].projects[1].figures.forecast_final_margin;
    check('drawer: a provisional figure shows its exact cents and its reasons', t2.includes(new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', minimumFractionDigits: 2 }).format(f.cents / 100)) && /COMPONENT_PROVISIONAL/.test(t2), t2.slice(0, 200));
    await shot(page, 'evidence_drawer_provisional', false);
    check('drawer: no console error', problems.length === 0, problems);
    await ctx.close();
  },
  /* Approvals: the screen shows exactly the token present() gave, refuses without a rationale, and sends nothing. */
  async approvals(b) {
    const v = VIEWS[0];
    const { page, ctx, problems } = await open(b, v, 'approvals');
    const forms = await page.$$eval('form.approve', fs => fs.map(f => ({ i: +f.getAttribute('data-i'), version: f.querySelector('[data-k=version]').textContent, digest: f.querySelector('[data-k=digest]').textContent, proposal: f.querySelector('[data-k=proposal]').textContent })));
    const want = DATA.views[v].approvals.map((a, i) => [i, a]).filter(x => x[1].present.can_approve);
    check('approvals: one form per proposal this person can approve', forms.length === want.length && forms.length === 2, forms);
    const bad = forms.filter(f => { const a = DATA.views[v].approvals[f.i]; return String(a.token.version) !== f.version || a.token.digest !== f.digest || a.token.proposal !== f.proposal; });
    check('approvals: the version, digest and proposal shown are exactly the token present() gave', bad.length === 0, bad);
    const form = page.locator('form.approve').first();
    await form.locator('button[type=submit]').click();
    const err = await form.locator('.msg').innerText();
    check('approvals: approving without a rationale is refused on the screen', /Write why you approve it first/.test(err), err);
    await form.locator('textarea').fill('Synthetic test rationale');
    await form.locator('button[type=submit]').click();
    const msg = await form.locator('.msg').innerText();
    const a0 = DATA.views[v].approvals[forms[0].i];
    check('approvals: the prototype says nothing was sent and shows the exact request', /Not sent/.test(msg) && msg.includes(a0.token.digest) && msg.includes(a0.token.proposal) && msg.includes('Synthetic test rationale'), msg.slice(0, 300));
    await shot(page, 'approvals_after_prototype_submit');
    check('approvals: no request left the machine and no console error', problems.length === 0, problems);
    const done = await page.locator('[data-approval]').filter({ hasText: 'Approved by' }).count();
    check('approvals: the approved action says it is still in force', done === 1 && /Still in force/.test(await page.locator('[data-approval]').filter({ hasText: 'Approved by' }).innerText()));
    await ctx.close();
    const pm = await open(b, 'zero_one-project-manager', 'approvals');
    const pmText = await pm.page.locator('main').innerText();
    check('approvals: the project manager sees the proposal but no approve form', (await pm.page.locator('form.approve').count()) === 0 && /You can see this proposal/.test(pmText), pmText.slice(0, 200));
    await pm.ctx.close();
  },
  /* Access: the project manager's screens hold no other project and no builder-wide material; one builder never shows the other. */
  async access(b) {
    for (const s of SCREENS) {
      const { page, ctx } = await open(b, 'zero_one-project-manager', s);
      const html = await page.content();
      check(`access project manager ${s}: no PRJ-002 or PRJ-003 anywhere in the page`, !/PRJ-00[23]/.test(html));
      if (s === 'health' || s === 'imports') check(`access project manager ${s}: says the screen is not shown and why`, /has no builder-wide access/.test(await page.locator('main').innerText()));
      await ctx.close();
      const z2 = await open(b, 'zero_two-director', s);
      check(`access zero_two ${s}: nothing of zero_one`, !/zero_one|Builder Zero One/.test(await z2.page.locator('main').innerText()));
      await z2.ctx.close();
    }
  },
  /* Data health: the connected route of zero_two cannot be assessed, with the eight empty record types; it is never shown as a figure. */
  async health(b) {
    const { page, ctx } = await open(b, 'zero_two-director', 'health');
    const t = await page.locator('main').innerText();
    const rows = await page.locator('text=SOURCE_EMPTY').count();
    check('health zero_two: the connected-systems route says Cannot assess', /Cannot assess/.test(t) && /CF-53/.test(t), t.slice(0, 300));
    check('health zero_two: the eight empty record types are listed with their code', rows === 8, rows);
    await ctx.close();
    const z1 = await open(b, VIEWS[0], 'health');
    check('health zero_one: both routes can be assessed', /Both import routes can be assessed/.test(await z1.page.locator('h1').innerText()));
    await z1.ctx.close();
  },
  /* Materials: scenarios are labelled scenario, an excluded offer is shown with why, and no scenario is presented as a recommendation. */
  async materials(b) {
    const { page, ctx } = await open(b, VIEWS[0], 'materials');
    const t = await page.locator('main').innerText();
    check('materials: says scenarios are not recommendations and nothing is chosen', /Scenarios to compare, not recommendations/.test(t) && /No quote is chosen/.test(t));
    check('materials: the excluded concrete quote is shown with why', /Q-0003/.test(t) && /32 offered against 40 required/.test(t));
    const unl = await page.$$eval('button.num[data-label]', bs => bs.filter(b => b.closest('table') && /Scenario/.test(b.closest('table').innerText.slice(0, 40)) && !['scenario', 'estimate'].includes(b.getAttribute('data-label'))).length);
    check('materials: every amount in a scenario table is labelled scenario or estimate', unl === 0, unl);
    await ctx.close();
    const z2 = await open(b, 'zero_two-director', 'materials');
    check('materials zero_two: no market data is said plainly, nothing invented', /No market data has been received/.test(await z2.page.locator('h1').innerText()));
    await z2.ctx.close();
  },
  /* Phone width: no screen scrolls sideways (wide tables scroll inside their own frame). */
  async mobile(b) {
    for (const s of SCREENS) {
      const { page, ctx } = await open(b, VIEWS[0], s, { viewport: { width: 390, height: 844 }, dsf: 2 });
      const w = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth }));
      check(`mobile ${s}: no sideways page scroll at 390 px`, w.sw <= w.iw, w);
      if (s === 'portfolio' || s === 'approvals') await shot(page, `mobile__${s}`, false);
      await ctx.close();
    }
  },
  /* Keyboard: the skip link comes first and moves to the screen without changing the route. */
  async keyboard(b) {
    const { page, ctx } = await open(b, VIEWS[0], 'project', { arg: 'PRJ-002' });
    await page.keyboard.press('Tab');
    const first = await page.evaluate(() => document.activeElement.className);
    await page.keyboard.press('Enter');
    const r = await page.evaluate(() => ({ focus: document.activeElement.id, hash: location.hash }));
    check('keyboard: the skip link is first and moves focus to the screen without changing the route', first === 'skip' && r.focus === 'main' && /project\/PRJ-002$/.test(r.hash), [first, r]);
    await ctx.close();
  }
};

(async () => {
  const browser = await pw.chromium.launch();
  try {
    for (const [name, fn] of Object.entries(TESTS)) {
      if (ONLY && ONLY !== name) continue;
      try { await fn(browser); } catch (e) { check(name + ': ran to the end', false, String(e && e.stack || e)); }
    }
  } finally { await browser.close(); }
  const failed = results.filter(r => !r[1]);
  console.log('\nchecks ' + results.length + '  failed ' + failed.length + (failed.length ? '\nFAILED: ' + JSON.stringify(failed.map(f => f[0])) : ''));
  process.exit(failed.length ? 1 : 0);
})();
