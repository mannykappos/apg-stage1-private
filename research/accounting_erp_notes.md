# Accounting / ERP survey notes (retrieved 2026-10-13)

About 36 fetches were used (slightly over the ~30 guide). WebSearch returns titles/URLs only, so search results were never used as evidence.

## Unreachable or unreadable (JS-rendered shells; no workaround attempted)
- developer.xero.com documentation pages (accounting overview, OAuth limits, webhooks overview): only headings returned. Xero limits came from developer.xero.com/pricing and the FAQ page instead; per-minute and concurrent limits remain unconfirmed.
- developer.intuit.com (QuickBooks webhooks, rest-api-features): "Compiling..." shell only. All QBO facts are secondary (unified.to).
- developer.sage.com Intacct OAuth page: empty shell.
- Business Central v2.0 resource list page: fetch error. Webhook entity list is from the v1.0 page.
- myob.lithium.com redirected to community.myob.com (followed once to the redirect target).

## Not covered
TechnologyOne, Deltek, Foundation, Sage 300/Jobpac API, Procore-adjacent tools: only a TechnologyOne search was run; nothing indicated builder use, so no fetch spent. No evidence either way is asserted.

## Weak evidence (grade B or C rows)
- Xero: AU construction evidence is the vendor's own marketing page only. Endpoint list is partial (spec truncated at 100,000 chars). Sandbox/demo company and AU data region unconfirmed.
- MYOB Business: rate limit figures come from a community post by MYOB staff (about five years old; staff said portal display was wrong) and a secondary blog. Auth scopes, no-webhooks, no-sandbox, 2-key limit and 29s timeout are from apideck (secondary).
- MYOB Advanced: only index/navigation pages read; evidence is a 2020 launch article.
- QBO, NetSuite, Sage Intacct, SAP B1: API facts rest on third-party blogs (unified.to, knowledgelib, apideck). Treat as C.
- NetSuite TBA phase-out from 2027.1 and "SOAP deprecation around 2028" are secondary claims.
- Sage Intacct overage currency not stated.
- Jobpac: no vendor API documentation found; AU evidence from one review site and one vendor partner page. Agave and insightsoftware are listed as third-party routes only.

## Gaps across all systems
Export/report options, AU data region, retentions, and job-costing budget-vs-actual via API are unconfirmed for essentially every system. Customer-admin approval is confirmed only for MYOB (secondary) and implied for NetSuite (secondary).
