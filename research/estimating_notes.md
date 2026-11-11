# Estimating class survey notes (retrieved 2026-10-13)

Covered: CostX, Buildxact, Procore, Autodesk Takeoff, RIB Candy, Rawlinsons, Cordell Estimator, Bluebeam. Not covered: STACK (no search or fetch made), PlanSwift and other tools. No evidence gathered on spreadsheets-as-the-norm; do not assume.

## Unreachable or unusable sources
- aps.autodesk.com Takeoff tutorial and reference pages: fetch returned only a title and empty Request/Response headings (JS-rendered). Takeoff API auth, scopes, rate limits, region and fields are therefore unconfirmed.
- developers.procore.com documentation pages: fetch returned navigation only. procore.github.io mirror gave the rate-limit page; the OAuth and environments pages gave only a menu or an error. Procore auth grant types come from menu labels, not page text.
- developers.procore.com environments-and-base-urls (content path): fetch error.
- github.com Takeoff Postman EndpointList: blocked by robots.txt.
- Vendor search results for CostX, Rawlinsons and Cordell were thin. No CostX developer docs were found.

## Weak or secondary evidence
- Buildxact API: only a third-party directory (apitracker.io) lists API features. No vendor docs found; marked unconfirmed. Vendor site is residential-focused.
- Candy: Capterra listing only (secondary). The AU "usage" is just availability.
- CostX: REST/OData API claim is from a vendor marketing page, not developer docs. AIQS page is sponsored content and not AU-specific. The Brisbane Airport reference is a single testimonial.
- Rawlinsons: single promotional secondary article. The EBSCO partnership appeared only as a search-result title and was not fetched.
- Cordell: vendor claims only. Search showed a separate "Construction API" product at CoreLogic/Cotality that was not investigated.
- Procore AU evidence is an owner-developer (PDG) plus a mention of builder Probuild, not a builder's own estimating use. Procore Estimating in Australia is unconfirmed. A search result showed an en-au Procore Estimating tutorial page marked "not fully launched in your preferred locale"; not fetched. The "Estimating Bid Board" endpoint comes from a third-party site (withone.ai).
- Procore zones: the FAQ lists US/UK/EU application zones only; file-storage location list (possible AU) was not read.
- Autodesk Takeoff API existence and deprecation dates rest on an APS blog post (node/4021, dated 22 Jul 2026) plus search-result URLs and a Postman repo landing page.

## Confidence grading
Only Bluebeam is graded A (vendor developer page read). Others B or C. Grading is per row, not per field.

## Suggested follow-ups
Procore file-storage regions page, Procore Estimating API reference, Autodesk Takeoff API docs via a browser-capable tool, CostX OData API docs (request from RIB), STACK API docs, Cotality Construction API.
