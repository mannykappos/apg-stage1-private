#!/bin/bash
# Step 5.1 (AM5-6 step 1): T, W and M on Python 3.13, then on Python 3.12, one job at a time, on the row 68 freeze (freeze5; be0c27b was abandoned).
# Resumable: a finished job has marks/<job>.done; a partial job's folder is moved to interrupted/ and the job rerun.
# BUILDER-EXECUTED: NOT INDEPENDENT.
set -u
R=/tmp/claude-0/-home-claude/9c1f68fa-600c-55a6-9aff-0843afa2c30f/scratchpad/recovery
EV=$R/ev5; BT=$R/btools; ZIP=$R/freeze5/a/APG-M11-S1.zip
mkdir -p $EV/run_sets $EV/marks $EV/interrupted
P=$EV/progress51.txt
now() { TZ=Australia/Melbourne date '+%Y-%m-%dT%H:%M:%S%z'; }
for job in py313_T py313_W py313_M py312_T py312_W py312_M; do
  [ -e $EV/marks/$job.done ] && continue
  py=/usr/bin/python${job:2:1}.${job:3:2}; set_=${job#*_}; out=$EV/run_sets/$job
  if [ -e $out ]; then mv $out $EV/interrupted/${job}_$(date +%s); echo "$(now) moved partial $job to interrupted/" >> $P; fi
  echo "$(now) start $job $($py -V 2>&1) free=$(df -BG --output=avail $EV | tail -1)" >> $P
  $py -I $BT/run_index_s1.py $ZIP $py $out --only $set_ > $EV/run_sets/$job.console.txt 2>&1; rc=$?
  echo "$(now) end $job rc=$rc $(tail -1 $EV/run_sets/$job.console.txt)" >> $P
  if [ $set_ = W ]; then $py -I -S $BT/check_wrapper_logs_s1.py $out > $out/wrapper_check.txt 2>&1; echo "$(now) wrapper_check rc=$? $(tail -1 $out/wrapper_check.txt)" >> $P; fi
  if [ $set_ = M ]; then $py -I -S $BT/check_m8_log_s1.py $out > $out/m8_check.txt 2>&1; echo "$(now) m8_check rc=$? $(tail -1 $out/m8_check.txt)" >> $P; fi
  rm -rf $out/x/APG-M11-S1/__pycache__ 2>/dev/null
  [ $rc -eq 0 ] || { echo "$(now) STOP: $job rc=$rc" >> $P; exit 1; }
  touch $EV/marks/$job.done
done
echo "$(now) STEP51 DONE" >> $P
