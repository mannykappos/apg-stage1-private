# Notes: labour, plant hire, bank data (retrieved 2026-10-13)

## Unreachable or blocked
- developer.procore.com: blocked by robots.txt. Procore docs were read via procore.github.io, which developers.procore.com links to.
- cdr.gov.au/business: blocked by robots.txt. Other cdr.gov.au PDFs and fact sheets were readable.
- ACCC CDR page, MYOB getting-started page, Fieldwire getting-started page, employmenthero.com/au construction page, xero.com/au construction page and Xero Central bank-feeds article: fetch errors or no content.
- Xero developer pages (payroll overview, timesheets, rate limits) returned only headings, not bodies. Xero timesheet field detail is therefore unconfirmed. The figures 60/min, 5000/day and 5 concurrent come from developer.xero.com/faq/limits. The oauth2/limits page headings mention 1,000 and 5,000 daily calls and an uncertified-app limit; I could not read them, so the current figures per tier are uncertain.

## Weak evidence
- Construction usage for Xero and Deputy rests on one vendor-published case study (Kingdom Projects, Melbourne). Xero's own construction-trades marketplace category was seen only as a search-result title.
- Coates "My Coates Hire" rests on one trade-press excerpt that was undated and cut off. The Coates homepage shows no portal or API information.
- The Access Group equipment page is vendor marketing and names no Australian customer.
- Procore "cost codes for timesheets" endpoint comes from a third-party listing (withone.ai), not Procore docs.
- No AU construction usage evidence was found for MYOB, Employment Hero (AU), Procore, Tanda or Fieldwire. Searches were not exhaustive.

## Uncertain or not covered
- Data region, sandbox, webhooks and fees are unconfirmed for most systems.
- Fieldwire: no evidence it stores labour hours.
- MYOB payroll endpoint list is dated October 2021 and does not state which MYOB product it applies to.
- Employment Hero PKCE became mandatory on 2026-09-30, so anything built against older token flows will fail.
- CDR: the accreditation guidelines read are v5 (8 Aug 2024) and may be superseded. The Consumer Data Standards (API technical specification) and the bank transaction field list were not fetched, so transaction entities are unconfirmed. Bank feeds via accounting software (Xero, MYOB) are unconfirmed.
- The CDR representative route seems to bar serving a customer as a CDR business consumer (business consumer fact sheet). Have this interpretation checked by a CDR lawyer before relying on it.
- Fetch count exceeded the ~30 target (about 45 calls including searches).
