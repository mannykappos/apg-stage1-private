# Re-check of draft 5 (RECHECK_DRAFT5.md): N-1, N-2, N-7, n-1, n-2, n-4 and owner items 29 and 30, on cia_data.py.
# Builder tool, BUILDER-EXECUTED: NOT INDEPENDENT.  (Run once, on cia_data_v5c.py's content.)
s = open('cia_data.py').read()
def rep(o, n):
    global s
    assert s.count(o) == 1, (s.count(o), o[:80]); s = s.replace(o, n)
# N-1: only dismissal changes in S00 §00.3
rep("'Track whether an exposure was prevented, mitigated, realised, dismissed or remains unresolved, with who decided and when, the reason where one is given, and evidence.'",
    "'Track whether an exposure was prevented, mitigated, realised, dismissed or remains unresolved, with reasons and evidence; for a dismissal, who dismissed it and when are recorded, and the reason where one is given.'")
# N-7 (owner item 29): authorised per kind of record
rep("An authorised person is a person with the permission to approve; a user who may only capture or view does not count. Where the builder has two or more authorised people, the person who entered a record cannot approve it. Where the builder has exactly one authorised person (the one-person exception), that person may approve:",
    "An authorised person, for a kind of record, is a person with the permission to approve that kind of record (for a keyed value, to confirm it); a user who may only capture or view does not count. Where two or more people are authorised for a kind of record, the person who entered a record of that kind cannot approve it. Where exactly one person is authorised for a kind of record listed here (the one-person exception), that person may approve records of that kind:")
rep("Records approved under the exception keep their marker; once there are two or more authorised people, every new record or change follows the two-person rule.",
    "Records approved under the exception keep their marker; once a second person is authorised for a kind of record, every new record or change of that kind follows the two-person rule, and the exception continues for the other kinds. Every approval, also under the exception, records a short reason (Section 15 checkpoint D).")
# n-1: security cancellation stays outside
rep("deletion or correction of authoritative evidence), and no action outside Profit Guardian. Onboarding",
    "deletion or correction of authoritative evidence; security cancellation), and no action outside Profit Guardian. Onboarding")
# n-2: the criteria point to DS026's list
rep("and only within the exception\\'s limits (§18.3: never a purchase order, a contract or scope change, a claim or notice, a deletion of evidence, or an action outside Profit Guardian).",
    "and only within the exception\\'s limits: never the consequential actions §18.3 lists as outside it, nor any action outside Profit Guardian.")
i = s.find("'Tests show the one-person exception and its limits:"); j = s.find("',", i); ac15 = s[i:j]
print(ac15[-700:])
open('cia_data.py', 'w').write(s); print('patched part 1')
# --- part 2 (run separately): PG-DS-AC-15 (n-2, N-7, item 30), N-2 (deferment returns on its date), n-4
s = open('cia_data.py').read()
rep("adding a second authorised person ends it for every new record or change, and records already approved keep their marker; with two or more authorised people the person who entered a record cannot approve it; every approval is recorded with its own permission, rationale and audit event; the exception never lets that person approve a purchase order, a contract or scope change, a claim or notice, or a deletion of evidence.",
    "adding a second person authorised for a kind of record ends the exception for new records and changes of that kind only (a bookkeeper who may confirm keyed values ends it for keyed values, not for settings or the budget), and records already approved keep their marker; where two or more people are authorised for a kind, the person who entered a record of that kind cannot approve it; every approval, also under the exception, is recorded with its own permission, a short reason, the risks considered and its audit event, and cannot be saved without the reason; the exception never lets that person take any consequential action §18.3 lists as outside it, nor any action outside Profit Guardian.")
rep("raised again only when something material changes; a deferment is recorded the same way;",
    "raised again only when something material changes; a deferment is recorded the same way, and a deferred finding is raised again on the date the person chose, or sooner if something material changes;")
rep("under §9.1\\'s re-notification rules. A deferment is recorded in the same way.",
    "under §9.1\\'s re-notification rules. A deferment is recorded in the same way; a deferred finding is raised again on the date the person chose (§6: next review date), or sooner if something material changes.")
rep("Where the builder breaks it down both ways (by stage and by trade), each breakdown",
    "Where the builder breaks it down in more than one way (for example by stage and by trade), each breakdown")
open('cia_data.py', 'w').write(s); print('patched part 2')
# --- part 3 (run separately): N-6 dependents
s = open('cia_data.py').read()
rep("    ('C22', '13', ['13.8'],",
    "    ('C22', '13', ['APG-S13-C0149'], 'checkpoint A: a defect is never verified or closed only because someone reports it complete; ignoring a finding does not close it'),\n"
    "    ('C22', '06', ['APG-S06-L0166'], 'the test that dismissed findings keep their evidence and can reopen (PG-DS-AC-16)'),\n"
    "    ('C04', '06', ['PG-AI-AC-14'], 'consequential actions cannot bypass human approval: the one-person exception never covers them'),\n"
    "    ('C04', '12', ['APG-S12-C0090', 'APG-S12-C0126', 'APG-S12-L0137', 'APG-S12-L0161'], 'retention and security release and cancellation need authorised human approval and an audit trail: a one-person builder approves his own retention steps, marked, with a reason; security cancellation stays outside the exception'),\n"
    "    ('C22', '13', ['13.8'],")
open('cia_data.py', 'w').write(s); print('patched part 3')
