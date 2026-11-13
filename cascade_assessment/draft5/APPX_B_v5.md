**The two locked obligations, now in the definition (M06).**
- **A currency** (S03 §11.1: "every monetary value must have an explicit currency"). Today the event has none and assumes the project's; the definition adds `currency`, which must equal the currency of the pool it moves.
- **The associated contract** (S03 §10.1: "associated contract and project"). Today the event moves a project-level pool with no contract link; the definition adds `contract_ref`, and the pool is kept per contract and project. For a project with one head contract, the pool is the same as today's.

Both are design changes for the build that brings retention events into the intake (first release, item 4); today's code changes then, under that build's own change request.

**The states, mapped to S03 §13's illustrative retention lifecycle** ("Withheld → Release Claimed → Under Review → Approved → Released / Disputed"):

| S03 §13 | The event's state | Note |
| --- | --- | --- |
| Withheld | withheld | money held back from a payment |
| Release Claimed | claimed | a release has been claimed |
| Under Review | claimed | no separate state: a claimed release is under review until it is approved or disputed; views label it "release claimed, under review" |
| Approved | approved | needs the retention approver role; approval is not release (S03 §13: "A retention is not released merely because release was requested or approved") |
| Released | released | needs the retention approver role and evidence |
| Disputed | disputed | from claimed or approved; it goes back to claimed or approved when settled |
| (none) | received | an extra step after Released: the money is in the bank, matched to a stored bank transaction of exactly the amount; S03 §13's rule that status needs evidence |

**Tests (PG-DS-AC-17, C18):**
- an event without a currency, with a currency other than its pool's, or without its contract is rejected with a reason;
- two contracts in one project keep separate pools;
- each state shows its S03 §13 label;
- "approved" does not count as released, and "received" needs its matching bank transaction;
- synthetic fixtures only: one project with two contracts in AUD, and an event in another currency.
