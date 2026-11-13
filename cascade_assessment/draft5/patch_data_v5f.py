# GPT's targeted confirmation of draft 5 (GPT_REVIEW_DRAFT5.md): S1 and S2 on cia_data.py.  Builder tool, BUILDER-EXECUTED: NOT INDEPENDENT.
s = open('cia_data.py').read()
def rep(o, n):
    global s
    assert s.count(o) == 1, (s.count(o), o[:80]); s = s.replace(o, n)
# S1: the material triggers are §9.1's three
rep("it is raised again only when something material changes, under §9.1\\'s re-notification rules.",
    "it is raised again only when something material changes, that is, on any of §9.1\\'s triggers: material new evidence, a meaningful status transition or an approved escalation condition.")
rep("it is raised again only when something material changes; a deferment",
    "it is raised again only when something material changes (any of Section 06 §9.1\\'s triggers: material new evidence, a meaningful status transition or an approved escalation condition); a deferment")
# S2: §14's review considers the evidence and any reason given
rep("Dismissing or deferring a finding never closes, verifies or changes the record it is about (Section 13 §13.8).",
    "Dismissing or deferring a finding never closes, verifies or changes the record it is about (Section 13 §13.8). Where a dismissal is reviewed (§14: a dismissal is not automatically proof of a false positive), the reviewer considers the evidence and any reason given.")
open('cia_data.py', 'w').write(s); print('patched')
