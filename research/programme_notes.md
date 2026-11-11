# Programme / scheduling survey notes (retrieved 2026-10-13)

## Unreachable or failed fetches
- elecosoft.com/?p=26822 (Asta vs MS Project/P6/Excel comparison) redirected to eleco.com/software-comparison-webinar; not followed, so no Excel evidence.
- Microsoft Learn Task Elements (current path) returned an error; the archived Project 2007 schema pages were used instead.
- Smartsheet rate-limiting guide (developers.smartsheet.com) failed twice; the figure comes from a smartsheet.com article (secondary).
- Seymour Whyte careers page (494498) returned empty; the VINCI-hosted copy was used.
- Procore API reference page returned only navigation; no schedule endpoints were confirmed.
- Techcommunity Project Online article returned metadata only (date confirmed, successors not).

## Weak or partial evidence
- Australian usage evidence is mostly job ads and one vendor-published case study. None is Victorian commercial-building-specific except Seymour Whyte (civil, Victoria; P6) and Kapitol (pipeline includes Victoria; Asta, vendor-promoted article). No market-share data was sought or found.
- Built ad is Sydney. Abergeldie (Synchro) is NSW civil.
- P6 REST: the endpoint list was truncated at 100,000 of 102,518 characters, and WBS, relationship and resource-assignment endpoints were not seen (likely exist, unconfirmed). Authentication session handling after login is unconfirmed.
- Oracle documents conflict on XER baselines: the P6 Professional page says XER does not support baselines (export/import); the P6 EPPM XER import page describes baseline import. Check against the customer's version.
- Microsoft: only archived 2007 schema was read, so current MSPDI additions are unconfirmed. Planner Premium as Project Online successor rests on a secondary source (epcgroup.net); the Microsoft Lifecycle page confirms only the retirement date of 2026-09-30. The Dataverse schedule API page covers Project Operations; applicability to Planner Premium is not stated.
- Asta Vision API: authentication, webhooks and rate limits not stated on the page read. The extra-cost status is stated by Elecosoft.
- Smartsheet: entity coverage (rows, dependencies, baselines) not confirmed; usage by Australian builders: no evidence found.
- Procore: only the file-import path was confirmed; Schedule tool API is unconfirmed.
- Synchro: almost nothing technical confirmed (confidence C). Spreadsheets row is a placeholder (C).

## Not researched (fetch budget)
Webhooks for all tools, sandbox/trial availability, pricing, and Australian data residency for Oracle, Microsoft, Elecosoft and Procore.

## Confidence grading
Grades reflect the technical facts in each row (P6 A, Asta A, Microsoft B, Procore B, Smartsheet B, Synchro C, spreadsheets C). Usage evidence is B or weaker throughout.
