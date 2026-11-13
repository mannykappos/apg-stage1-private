#!/bin/bash
# Fix 6 focused checks: the new and changed test classes, on Python 3.13 and 3.12, one at a time.  BUILDER-EXECUTED: NOT INDEPENDENT.
cd "$(dirname "$0")/../work"
O=../focus6
for py in /usr/bin/python3.13 /usr/bin/python3.12; do v=$(basename $py)
  for spec in "test_no_timeout_kill AM6Supervision P2SubprocessUnits" \
              "test_mutation_timeout AM6MutationToolGaps AM6LeafInterrupts P2MutationFamily" \
              "test_runner_zero_work PinnedCounts AM6AttributionAndSignals AM6FindingThirteenProbes AM6RunEndAndCounts P2FaultRunners P2CaseRunners P2NoResultSupervisors P2GuardedImports AM5CR02 AM5AttributionTable" \
              "test_exec_env AM6FirstChain AM5SecondChain E7ChildIsolationM10Halves"; do
    set -- $spec; f=$1; shift
    echo "$(date '+%H:%M:%S') start $v $f" >> $O/progress.txt
    timeout 7000 $py -I -S tests_tools/$f.py "$@" > $O/${v}_$f.log 2>&1; rc=$?
    echo "$(date '+%H:%M:%S') end $v $f rc=$rc $(grep -E '^(Ran|OK|FAILED)' $O/${v}_$f.log | tr '\n' ' ')" >> $O/progress.txt
  done
done
echo "$(date '+%H:%M:%S') FOCUS6 DONE" >> $O/progress.txt
