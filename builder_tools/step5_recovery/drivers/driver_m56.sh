#!/bin/bash
# Mistake 56 re-run: the four recorded-totals jobs (b6tot, k2tot, both Pythons) with the corrected label; same job() and floor as driver523.
#   2: golden, pairs, b6 and k2 (old side e4531a35, owner 2026-11-11 22:47) and the recorded-totals checks, on 3.13 then 3.12
#   3: m2 on 3.13 then 3.12: the --list literal (AM5-1 A (i)), the five harness slices (AM5-2), the successor as written, AM5-3 B's
#      one-worker run, the comparison with the AM4-1 and AM5-3 A1 allowances
# Resumable: marks/<job>.done.  Any result not as expected stops the driver (paper H).  Disk: below 10 GB free the running job is
# stopped and the driver stops (the authorisation's floor).          BUILDER-EXECUTED: NOT INDEPENDENT.
set -u
R=/tmp/claude-0/-home-claude/<SESSION-ID>/scratchpad/recovery
EV=$R/ev5; BT=$R/btools; NEW=$R/freeze5/a/APG-M11-S1.zip; OLD=$R/e4531a35/APG-M11-S1.zip; M10=$R/in/APG_M10_CODE_AND_DATA.zip
REC=$R/pack/APG_D14_PASS2_AM5_REVIEW_PACK/04_evidence
mkdir -p $EV/marks; P=$EV/progress523.txt; W=$EV/disk_watch523.txt
now() { TZ=Australia/Melbourne date '+%Y-%m-%dT%H:%M:%S%z'; }
freegb() { df -BG --output=avail $EV | tail -1 | tr -dc 0-9; }

job() {   # job NAME PY OUTDIR COMMAND...
  local name=$1 py=$2 out=$3; shift 3
  [ -e $EV/marks/$name.done ] && return 0
  mkdir -p $out
  if [ "$(freegb)" -lt 10 ]; then echo "$(now) STOP before $name: free $(freegb) GB below the 10 GB floor" >> $P; exit 1; fi
  echo "$(now) start $name free=$(freegb)G" >> $P
  "$@" > $out/$name.console.txt 2>&1 &
  local pid=$! low=0 n=0
  while kill -0 $pid 2>/dev/null; do
    sleep 10; n=$((n+1)); f=$(freegb)
    [ $((n % 12)) -eq 0 ] && echo "$(now) $name free=${f}G" >> $W
    if [ "$f" -lt 10 ]; then low=1; pkill -TERM -P $pid; kill -TERM $pid; fi
  done
  wait $pid; local rc=$?
  echo "$(now) end $name rc=$rc $(grep -E '^(RESULT|AM5-3 B|m10 --list)' $out/$name.console.txt | tail -1)" >> $P
  if [ $low = 1 ]; then echo "$(now) STOP: $name stopped at the 10 GB floor" >> $P; exit 1; fi
  if [ $rc -ne 0 ]; then echo "$(now) STOP: $name rc=$rc (not as expected; paper H)" >> $P; exit 1; fi
  touch $EV/marks/$name.done
}

for v in 313 312; do
  py=/usr/bin/python${v:0:1}.${v:1}; out=$EV/compare_py$v
  job b6tot_$v  $py $out $py -I -S $BT/recorded_totals_s1.py b6 $out/b6.txt $REC/compare_py$v/b6.txt $out/b6_recorded_totals.txt
  job k2tot_$v  $py $out $py -I -S $BT/recorded_totals_s1.py k2 $out/k2.txt $REC/compare_py$v/k2.txt $out/k2_recorded_totals.txt
done
echo "$(now) M56 TOTALS RERUN DONE" >> $P
