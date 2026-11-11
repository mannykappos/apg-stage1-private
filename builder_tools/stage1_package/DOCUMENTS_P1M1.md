P1-M1's fix is in the D14 run-record tools, not in the successor (build authorisation §2 (C1)). It is kept as its own diff, `d14/p1m1/P1-M1.diff` (SHA-256 `f93d5e34dd7e7e26ff03379a775aae91abded8ebf368f7e293190412cfa0e58c`), and the erratum (DP-7.1 (a)) is recorded beside the issued P1 pack, not inside it.

| File | Before (as authorised) | After |
|---|---|---|
| `d14/runs_p1/tools/d14_p1_check.py` | `b3d1c9d72ea8248537dc28849e13359619915fe9257e8c5146d34dd4a72c9330` | `fba6769ea13b6295accd53dfec111d99d659f9c2cefdee90fcede63b714b8392` |
| `d14/runs_p2/tools/d14_p2_check.py` | `5484b619b59aee78083c00cd4ea87c71fb0430be6e2fb99d648c066e24edc3a6` | `986e004ad0df95b44180c855c651e3d989fe9cd8b1fd2183606024f2dd84f8ff` |
| `d14/tools_tests/test_d14_record_postgresql.py` | (new) | in the package |

The test fails against the before copies and passes against the after copies and against the files as they now stand: `evidence/p1m1/test_before.txt` (exit 1, 4 failures), `test_after.txt` (exit 0), `test_current.txt` (exit 0), with the earlier per-Python results in `d14/p1m1/RESULTS.txt` (3.12 and 3.13: before 1, after 0). The P2 checker's fin-corpus gate is still 55 (finding 5, section 8): P1-M1 changed only its `postgresql` rule.
