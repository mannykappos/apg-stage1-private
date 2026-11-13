# Data Readiness Change Request, revision 4.1: the entity register completed against every requirement row (M15)

Nov 13, 2026 · Claude (builder) for Emmanuel (product owner) · BUILDER-EXECUTED: NOT INDEPENDENT, with the agent checks marked INDEPENDENT READ-ONLY (agent)

This addendum changes one register of revision 4: the entity register (`ENTITY_REGISTER.csv`). Everything else in revision 4 stands. It is design only: no build is authorised.

## Why

Revision 4 listed 100 entities. Its next steps, and the cascade impact assessment (matter M15), required the register to be checked against every row of the Master RTM before it can become an annex of Section 03 (S03 DS009).

**A mistake, disclosed (mistake 61).** Claude first checked at heading level, and reported 2 missing entities and 4 field gaps. That was badly incomplete. Four independent agents then read all 2,712 RTM rows, one at a time (`m15rtm/out/`):
- 649 rows were carried by the register;
- 52 were carried only by the heading-level fixes;
- 1,581 needed no data;
- 430 needed data the register did not carry.

## What changed

- **114 entities, up from 100.**
    - 14 new: E100 to E113.
    - Seven of the new ones are class P, held by the Anchor platform, to be confirmed in discovery (owner record item 22): the audit event, the data classification and retention policy, the background job and external action record, the incident, the operational record, the AI interaction record (only if APG keeps AI context) and identity and access.
- **Field groups added to 47 existing entities**, one change each, marked [R41-xx] in the register's "required field groups" column.
    - The largest are on the finding (E84), the recommendation (E86), the outcome and benefit lifecycle (E88), the provenance fields on every record (E01), the source registry (E02), the source authority register (E03) and the security instrument (E78).
- **The budget part.** The budget line (E38) carries its part of the job (stage, trade or area), from the owner's answer to question 2 (owner record item 16).
- **Where to find each change.** `M15_REGISTER_CHANGES.csv` lists every change with the agent findings it closes; the data is in `register_rev41.py`.
- **Statuses:** 6 covered, 51 partial, 57 missing.
    - Five entities move from covered to partial (E27, E28, E35, E38, E84), because they gain field groups APG does not hold today.
    - The E64 plant hire entity is renamed "Plant and equipment use (hired or owned)".

## What did not change

- **Release placements.** No rule or figure in the current code reads any added field. The field-coverage report regenerated on revision 4.1 is unchanged: 170 field pairs checked, no gap. So every change sits in "later", and the first data release is unchanged.
- **The other registers.** The rule input contracts and the systems survey are unchanged. The supply-route list changes only in E64's new name. The paths chart counts more not-built paths, because of the new entities.

## The data supply design's counts

The data supply design (draft 7) still counts revision 4's 100 entities in its supply plan and figures. Those counts are superseded by this register's 114. The 14 new entities (E100 to E113) are later-release scope, and each has its supply path here. (Added after GPT's targeted confirmation of the cascade impact assessment, draft 5, finding S4. Draft 7 itself is not edited.)

## Checks

1. **First re-check** of all 482 flagged rows by a fresh agent (`m15recheck/out/`): 401 carried, 81 still gaps. It also flagged:
    - field groups thinner than the fixes they claim;
    - E05 mixing a platform-held part into a builder entity, now split out as E113;
    - E102's double role.
2. **Claude widened the changes and added E113**, plus field groups on E09, E13 and E16.
3. **A scoped second re-check** of those 81 rows by a fresh agent (`m15recheck2/out/`): 67 carried, 14 still gaps. Six of the 14 were the quality-improvement baseline fields of S13 s13.6, which E44 lacked.
4. **Claude closed the 14.** Each named field is now in the register, checked by the builder row by row (BUILDER-EXECUTED: NOT INDEPENDENT). E05 now keeps only the tenant: its users and roles are recorded on E113.
5. **No further agent round.** The fixes are named fields, checked against the 14 rows. To avoid a loop of re-checks, GPT's targeted confirmation of draft 5 covers this register.

## For discovery

E102, the platform audit event, also has to carry APG's own financial-state transitions: claims, certification, collection, retention release and security return. Discovery must confirm that the platform audit log can hold the business state before and after each change, with its evidence. If it cannot, that history is an APG record.
