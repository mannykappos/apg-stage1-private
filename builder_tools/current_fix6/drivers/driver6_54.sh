#!/bin/bash
# Step 5.4 (AM5-6 step 4) on the fix 6 freeze (freeze6), one job at a time: historical (both Pythons); static (frozen comparison,
# route_scan, route_children, the 2C demonstration on both Pythons); the audits, started with env -i and five names from a fresh
# extraction (outside services, process-API reach); the child-start scan; the row 68 scan of every process start in tests_tools.
# The names check is made at packaging (amendment 5 Appendix A part 2).  Resumable: marks/<job>.done.  A tool's non-zero exit stops.
# Fix 6: also the row 6 demonstration of the audit's P.2 stop (a planted secret-bearing name; the tool must exit 3, name only).
# BUILDER-EXECUTED: NOT INDEPENDENT.
set -u
R=/tmp/claude-0/-home-claude/<SESSION-ID>/scratchpad/recovery
EV=$R/ev6; BT=$R/btools; NEW=$R/freeze6/a/APG-M11-S1.zip; M10=$R/in/APG_M10_CODE_AND_DATA.zip; EXCL=$R/w1b/W1_EXCLUSION_LIST_v3.csv
PY3=/usr/bin/python3.13
mkdir -p $EV/marks $EV/static $EV/audit_final; P=$EV/progress54.txt
now() { TZ=Australia/Melbourne date '+%Y-%m-%dT%H:%M:%S%z'; }
freegb() { df -BG --output=avail $EV | tail -1 | tr -dc 0-9; }
job() {   # job NAME CONSOLE COMMAND...
  local name=$1 con=$2; shift 2
  [ -e $EV/marks/$name.done ] && return 0
  if [ "$(freegb)" -lt 10 ]; then echo "$(now) STOP before $name: free $(freegb) GB below the 10 GB floor" >> $P; exit 1; fi
  echo "$(now) start $name free=$(freegb)G" >> $P
  "$@" > $con 2>&1; local rc=$?
  echo "$(now) end $name rc=$rc $(tail -1 $con)" >> $P
  [ $rc -eq 0 ] || { echo "$(now) STOP: $name rc=$rc" >> $P; exit 1; }
  touch $EV/marks/$name.done
}
for v in 313 312; do py=/usr/bin/python${v:0:1}.${v:1}; out=$EV/historical_py$v
  [ -e $EV/marks/historical_$v.done ] || rm -rf $out
  job historical_$v $EV/historical_py$v.console.txt $py -I $BT/historical_m10_s1.py $M10 $EXCL $py $out
done
job frozen_compare $EV/static/frozen_compare.txt $PY3 -I $BT/frozen_compare_s1.py $M10 $NEW $EV/static/frozen_compare.csv
job route_scan     $EV/static/route_scan.txt $PY3 -I $BT/route_scan_s1.py $NEW $EV/static/route_scan.csv
job route_children $EV/static/route_children.console.txt $PY3 -I -S $BT/route_children_s1.py $NEW $EV/static/route_children.txt
for v in 313 312; do py=/usr/bin/python${v:0:1}.${v:1}
  job case_inventory_limit_$v $EV/static/case_inventory_limit_py$v.console.txt $py -I -S $BT/case_inventory_limit_s1.py $NEW $py $EV/static/case_inventory_limit_py$v.txt
done
X=$EV/audit_x
if [ ! -e $EV/marks/audits.done ]; then
  rm -rf $X; mkdir -p $X; (cd $X && unzip -q $NEW)
  E5="env -i PATH=/usr/bin:/bin TMPDIR=$X LANG=C.UTF-8 LC_ALL=C.UTF-8 TZ=UTC"
  job outside_services  $EV/audit_final/outside_services.console.txt $E5 $PY3 -I -S $BT/audit_outside_services_s1.py $X/APG-M11-S1 $EV/audit_final/outside_services.txt
  job secret_stop_demo  $EV/audit_final/secret_stop_demo.console.txt bash -c '$0 "$@"; test $? -eq 3' $E5 $PY3 -I -S $BT/audit_outside_services_s1.py $X/APG-M11-S1 $EV/audit_final/secret_stop_demo.txt --demo-planted-secret
  job process_api_reach $EV/audit_final/process_api_reach.console.txt $E5 $PY3 -I -S $BT/audit_process_api_reach_s1.py $X/APG-M11-S1 $EV/audit_final/process_api_reach.txt
  job child_start_scan  $EV/audit_final/child_start_scan.console.txt $PY3 -I -S $BT/child_start_scan_s1.py $X/APG-M11-S1 $EV/audit_final/child_start_scan.txt
  job tset_start_scan   $EV/audit_final/tset_start_scan.console.txt $PY3 -I -S $BT/tset_start_scan_s1.py $X/APG-M11-S1 $EV/audit_final/tset_start_scan.txt
  touch $EV/marks/audits.done; rm -rf $X
fi
echo "$(now) STEP54 DONE" >> $P
