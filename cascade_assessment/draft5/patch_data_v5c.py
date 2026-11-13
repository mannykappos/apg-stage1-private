# Draft-5 check minors m-2, m-5, m-6, m-7, m-8, m-9 on cia_data.py.  Builder tool, BUILDER-EXECUTED: NOT INDEPENDENT.
# Note: part 5 first wrote an unescaped apostrophe into cia_data.py, which broke build_cia.py; it was escaped by hand (sed) and rebuilt.
s = open('cia_data.py').read()
def rep(o, n):
    global s
    assert s.count(o) == 1, (s.count(o), o[:80]); s = s.replace(o, n)
# m-2
rep("'Rule thresholds and windows ship with defaults approved by the product owner;",
    "'Rule thresholds and windows ship with defaults approved by the product owner (the financial severity levels of §8 are not among them: they have no default, and the builder sets them, DS002);")
# m-5
rep("'A retention event (Section 03 §10.1) carries its currency and its associated contract as well as its project; an event with no currency, a currency other than its pool\\'s, or no contract is rejected with a reason; retention pools are kept per contract and project.",
    "'A retention event (Section 03 §10.1) carries its currency and its associated contract as well as its project; an event with no currency, a currency other than its pool\\'s, or no contract is rejected with a reason; retention pools are kept per contract and project. Each state shows its Section 03 §13 label; \"approved\" does not count as released; and \"received\" needs its matching bank transaction.")
# m-8
rep("'Show the approved budget (§3.3) and the authoritative forecast\\'s final cost and final margin (§5.1) first.",
    "'Show the approved budget (§3.3) and the authoritative forecast\\'s final cost and final margin (§5.1) first, the forecast figures labelled as forecasts (Section 03 §5).")
# m-7
rep("with a sample export from each, to confirm the systems survey of the data readiness change request.",
    "with a sample export from each, to confirm the systems survey of the data readiness change request, including whether each system holds the budget broken down by stage, trade or area (Section 05 §3.3).")
# m-9 and m-6
rep("The builder decides what to do, and may ignore (dismiss) any finding in one tap;",
    "The builder decides what to do: a person whose role permits it (role-based permissions, Section 15 §15.4) may ignore (dismiss) any finding in one tap;")
rep("it is raised again only when something material changes, under §9.1\\'s re-notification rules.",
    "it is raised again only when something material changes, under §9.1\\'s re-notification rules. Acceptance criterion PG-DS-AC-16 tests this (it is kept with this change request\\'s other criteria in Section 04 §19).")
open('cia_data.py', 'w').write(s); print('patched')
# --- second part (run separately, after the first): S-1, S-3, S-5, S-6, S-7 remnants found while writing CHECK5_FIXES_CIA.md
s = open('cia_data.py').read()
rep("Preparing and approving stay separated as Section 02 §3.1 and PG-FR-025 require,",
    "Preparing and approving stay separated where Section 02 §3.1 and PG-FR-025 require it,")
rep("It is a setting, approved as other settings are (Section 04 §18.3).', 'C11')",
    "Where the builder breaks it down both ways (by stage and by trade), each breakdown adds up to the whole-job approved budget on its own. The structure of the breakdown (which parts exist and how costs map to them) is a setting, approved as other settings are (Section 04 §18.3); the amount of each part is part of the approved budget baseline (§3.3) and is approved as the budget and its changes are. Under the one-person exception (Section 04 §18.3), that person approves both, marked.', 'C11')")
rep("Dismissal/deferment of material findings must record who dismissed or deferred it and when,",
    "Dismissal/deferment of a material finding must record who dismissed or deferred it and when,")
rep("    ('C04', '15', ['15.4', '15.11'],",
    "    ('C04', '15', ['APG-S15-C0193', 'APG-S15-L0094'], 'checkpoint D (explicit authority, recorded reasons, traceable outcomes) and approval events: met by the approval record with its rationale and audit event'),\n    ('C04', '15', ['15.4', '15.11'],")
open('cia_data.py', 'w').write(s); print('patched 2')
# --- third part (run separately): S-8's sentence and item 24 in S06 DS006
s = open('cia_data.py').read()
rep("under §9.1\\'s re-notification rules. Acceptance criterion PG-DS-AC-16",
    "under §9.1\\'s re-notification rules. A deferment is recorded in the same way. Dismissing or deferring a finding never closes, verifies or changes the record it is about (Section 13 §13.8). Acceptance criterion PG-DS-AC-16")
open('cia_data.py', 'w').write(s); print('patched 3')
# --- fourth part (run separately): PG-DS-AC-16 carries deferment and the unchanged record
s = open('cia_data.py').read()
rep("it is raised again only when something material changes. Shown by tests.",
    "it is raised again only when something material changes; a deferment is recorded the same way; the record the finding is about (a defect, say) is not closed or changed by it. Shown by tests.")
open('cia_data.py', 'w').write(s); print('patched 4')
# --- fifth part (run separately): PG-DS-AC-05 points to the exception's limits (B-1)
s = open('cia_data.py').read()
rep("on the setting and on every figure, finding and report that uses it (§18.3).",
    "on the setting and on every figure, finding and report that uses it, and only within the exception\'s limits (§18.3: never a purchase order, a contract or scope change, a claim or notice, a deletion of evidence, or an action outside Profit Guardian).")
open('cia_data.py', 'w').write(s); print('patched 5')
