# Project management / document control survey notes (retrieved 2026-10-13)

Coverage: 7 systems - Procore, Oracle Aconex, Autodesk Construction Cloud, Trimble Vista (Vista API), Trimble ProjectSight, Fieldwire, Dalux. About 35 fetches used.

## Unreachable or unusable pages
- Autodesk Platform Services docs (aps.autodesk.com, all ACC, cost, BIM 360 pages): returned only a title and empty Request/Response headings (JavaScript-rendered). No ACC API fact is confirmed; the ACC row is almost entirely "unconfirmed".
- Procore API reference pages (developers.procore.com/reference/...): content not rendered. Procore cost entities (budgets, commitments, change orders, invoices, RFIs) are therefore unconfirmed from official docs.
- developers.procore.com/documentation/content/handling-procore-regions and procore.github.io regions page: fetch error. Procore AU data region unconfirmed.
- ProjectSight API page redirected to help.trimble.com/projectsight; not followed.
- Vista API Authentication page not read, so Vista auth unconfirmed.
- Aconex Cost API endpoint list and throttling article not read.

## Weak evidence
- AU usage for Procore (PDG Corp / Probuild) and Aconex (John Holland) comes from vendor-published customer stories; not independent.
- ACC usage evidence is Hansen Yuncken and BIM 360 (a predecessor), via a trade-news article. It does not name ACC or Autodesk Build.
- Procore object list (projects, vendors, punch_items, timecard_entries, etc.) comes from Ampersand, a third-party connector vendor (grade B). It lists only selected examples.
- Procore sandbox URL (sandbox.procore.com) is from Ampersand; the official intro page confirms a Developer Sandbox exists but gave no URL.
- Fieldwire "by Hilti" ownership is from a G2 result title only.
- The Procore support page listing Australia under Asia Pacific concerns marketplace-app available regions, not data hosting. Do not treat it as AU residency.

## No evidence found
- AU commercial usage: Dalux, Fieldwire (only AU-localised marketing site), Trimble Vista, Trimble ProjectSight. Searches were limited and absence here is not proof of non-use.
- Autodesk University "105 Victoria Street" (Skanska, Forma) is a UK project and was excluded.

## Dates and flags
- Dalux legacy company API keys expired 2026-02-28 per Dalux; integrations must now use API identities.
- Aconex plans to retire Integration IDs (Basic Auth) towards the beginning of 2027.

## Not covered
Webhooks, export options and AU data regions are largely unconfirmed for ACC, Fieldwire, Dalux, ProjectSight and Aconex. Other candidates (e.g. Hammertech, Cm3, Buildertrend, Trimble Connect) were not surveyed.
