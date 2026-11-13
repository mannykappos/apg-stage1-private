# M15: the 100 entities checked against the locked blueprint's data requirements (2026-11-13)

Builder work (Claude), BUILDER-EXECUTED: NOT INDEPENDENT. This is a step before formal approval of change request APG-CR-DSR (cascade impact assessment, section 10, M15).

## Method, and what it does not cover

- I listed every heading in Sections 00 to 17: 438 in total. I set aside the 182 that carry no data need: purpose, acceptance criteria, implementation and audit instructions, lock records, and Sections 14 to 17, which govern the build, tests and operations rather than data.
- For each of the remaining 256 headings, I asked whether it requires APG to hold a kind of data. Where it does, I checked that an entity in revision 4's register (`ENTITY_REGISTER.csv`) carries it.
- I read every data list in those headings in full and checked each item against the register's entities and their required field groups. These are: S03 §2, §3, §8 to §10; S04 §2; S05 §4; S07 §3; S08 §4, §5, §13; S09 §3; S11 §3, §5; S12 §12.4, §12.5, §12.8 to §12.10; S13 §13.3, §13.5; and S02's workflows A to H.
- I then searched the register for the terms each candidate gap would use.
- **Limit:** this works at heading level, plus the data lists, read item by item. I did not read each of the 2,712 RTM rows one at a time, so a data need stated only in a single sentence outside those lists could still be missed. The cascade impact assessment's dependents table (1,342 locked items) was read separately, for knock-on effects of the change.

## Result

Most data needs map to a register entity. I found two missing entities and four smaller gaps. None affects the first data release: no current rule or figure reads these data, so by the release rule they all sit in "later". They are added so the register is complete, which was the owner's direction ("make sure it's 100%").

| # | Gap | Locked source | Proposed register change | Release |
| --- | --- | --- | --- | --- |
| 1 | **Material movements and stock**: quantities installed or consumed, returned, damaged, wasted, held as usable stock, and moved between projects | S03 §8.2 ("consumed/installed, returned, damaged, wasted and remaining usable stock … connected by documented movements"); S02 workflow D step 25; S08 §13; S04 §2 ("stock, substitutions … material movements"); PG-MP-AC-01, PG-MP-AC-14 | New entity E100, **Material movement and stock**: material, project, movement type, quantity and unit, date, location, condition, verified or estimated, source. Ways in: template, entry screen, site capture. | later (the inventory, waste and surplus insight of S08 §13 is not built) |
| 2 | **Cash-flow forecast**: dated, time-phased inflows and outflows at project and business level, with as-of date, horizon and qualification | S12 §12.5; S12 §12.3 (scheduled and forecast receipts and payments) | New entity E101, **Cash-flow forecast** (APG calculates it from the receivable, payable, claim, schedule, retention, security and payroll records), stored with its calculation run. | later (the cash-flow forecast is not built) |
| 3 | **Material substitutions** and their approval | S03 §8.4; S08 §4 ("approved substitutions"); S04 §2 | Field group added to E27 (specification requirement): approved equivalents and substitutions, with who approved and when. | later |
| 4 | The head contract's **pricing basis** (schedule of rates, bill of quantities or lump sum), **milestones** and **defects liability period** | S11 §3; S03 §10.3 ("applicable defect liability or maintenance period") | Field groups added to E08 (head contract). | release B (claims and certificates) |
| 5 | **Owned plant and equipment use** (not only hired plant) | S02 §2.1 equipment and logistics ("plant utilisation … idle-resource costs"); S06 §4 ("idle equipment, duplicated hire") | Field group added to E64 (plant hire), renamed **Plant and equipment use (hired or owned)**. | later |
| 6 | **Ledger journals and account balances** (posted journals, reconciled cash balances, cashbook) | S04 §2 (accounting: "journals and relevant account balances"); S12 §12.4 ("reconciled cash balances, cashbook entries") | Field groups added to E73 (bank transaction: the account and its reconciled balance) and to E96 (financial record: the posted journal reference). | later |

**Linked to the owner's decision of today on question 2:** the builder's own budget breakdown (stages, trades, areas) uses E98 (work package) and E38 (budget line). E38 gains the part (stage, trade or area) each line belongs to, and the costs that carry an extra's reference gain the part too (Appendix C of the assessment).

## What happens next

These changes go into the register (revision 4's `build_entities.py`) when the assessment is finalised with GPT's findings. The supply plan and the counts that follow from them are regenerated then: the entity count goes from 100 to 102, and release placements and field counts change.
