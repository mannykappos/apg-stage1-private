# Brief: focused re-check of the entity register, revision 4.1, against the rows the first M15 row-level check flagged

You are a fresh, independent agent. Label your work **INDEPENDENT READ-ONLY (agent)**. This is design work: nothing is built.

Anchor Profit Guardian's locked blueprint (Sections 00 to 18) has a requirements matrix of 2,712 rows. A first independent check read every row and found 430 rows whose data the entity register (revision 4, 100 entities) did not carry, plus 52 rows carried only by proposed fixes. The builder has now written revision 4.1 of the register (113 entities). It adds field groups to existing entities and 13 new entities. Each change has an ID R41-xx and lists which first-check fixes it consolidates.

The owner decided that records probably held by the Anchor platform underneath APG (audit log, identity and access, background jobs, incidents, operations records, data classification and retention policy) are listed, marked "held by the Anchor platform, to be confirmed in discovery" (class P). A row carried by such an entity counts as carried.

## Inputs (under `<WORKSPACE>/scratchpad/m15recheck/in/`)
- `ROWS_TO_RECHECK.csv`: the 482 rows (430 GAP and 52 COVERED-BY-PROPOSED), with the first check's verdict, the data it named, its note, and the requirement text.
- `ENTITY_REGISTER_REV41.csv`: the revised register (column "required field groups" holds each entity's field groups; revision 4.1 additions are marked [R41-xx]).
- `M15_REGISTER_CHANGES.csv` and `register_rev41.py`: the changes and what each consolidates.
- `Section_00.txt` to `Section_18.txt`: the locked sections, for context.

## What to do
For every row of ROWS_TO_RECHECK.csv, decide whether revision 4.1 now carries the data the requirement needs:
- `CARRIED`: name the entity and the [R41-xx] change or the existing field group that carries it.
- `STILL-GAP`: say exactly what is still missing, and the smallest fix.
- `NOT-A-DATA-NEED`: only if you are sure the first check was wrong that the row needs APG to hold data; say why.

Be strict: a field group must actually carry what the requirement names. Do not count vague wording as carrying a specific field.

## Output
1. `out/RECHECK.csv` with columns: requirement_id, verdict, entity, change, note. Every row of the input, in order.
2. `out/RECHECK_SUMMARY.md`: counts by verdict; every STILL-GAP with its row, the missing data and the fix; anything in revision 4.1 you think is wrong (an R41 change that does not say what it claims, a wrong class, a platform marking that seems wrong); rows you could not judge.

Read-only: write only under `m15recheck/out/`. No network. Short `python3 -I -S` scripts to read files or check your row count are fine, but read each row yourself. When done, reply with the counts and the STILL-GAP rows only.
