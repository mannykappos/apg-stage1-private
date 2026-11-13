# Final narrow check of draft 5 (FINAL_CHECK_DRAFT5.md): F-1 on cia_data.py.  Builder tool, BUILDER-EXECUTED: NOT INDEPENDENT.
s = open('cia_data.py').read()
def rep(o, n):
    global s
    assert s.count(o) == 1, (s.count(o), o[:80]); s = s.replace(o, n)
rep("with two or more authorised people, never by the person who entered them; with exactly one, by that person,",
    "with two or more people authorised to approve setup answers, never by the person who entered them; with exactly one, by that person,")
rep("a builder with exactly one authorised person confirms the values he keyed himself",
    "where exactly one person is authorised to confirm keyed values, that person confirms the values he keyed himself")
rep("(a builder with exactly one authorised person); no other",
    "(exactly one person authorised for that kind of record); no other")
open('cia_data.py', 'w').write(s); print('patched')
