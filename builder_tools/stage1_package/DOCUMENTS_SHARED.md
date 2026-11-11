
**The Part A shared items** (§4.2 last point: no Part B entry added). Stage 1 touches four of them:
- `tools/m3_mutants.py`, `tools/m8_mutants.py`, `tools/run_m8_tests.py`: byte-identical to M10 (frozen-file comparison, section 5); stage 1 added the successors `tools/m3_mutants_s1.py`, `tools/m8_mutants_s1.py`, `tools/run_m8_tests_s1.py` instead (DP-1.2 (B)). The diff of each is empty.
- `tools/expected_counts.json`: new in stage 1 (M10 has no such file), so its diff is the whole file, in the ZIP. Every one of its 86 change records names a stage 1 cause (stage 1 build, F-55, M8-T, M-1, W-1, W-1A, W-1B, and v79 to v86 for the refusal fix of section 9, mistake 1 (c), which re-pinned eight wrappers' tool hashes); none names Part B, and its sections hold only stage 1 successors' pins.
The fifth shared item of the D1 table, `tests/test_ingest_boundaries.py`, is not among stage 1's rows and is unchanged.
