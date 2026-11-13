#!/bin/bash
# Fix 6: the full evidence on the fix 6 freeze in AM5-6 order (5.1, then 5.2 and 5.3, then 5.4), one job at a time, 10 GB floor (in each
# part).  Each part is resumable (marks/<job>.done).  A part that stops ends this driver.  BUILDER-EXECUTED: NOT INDEPENDENT.
D=$(dirname "$0")
bash $D/driver6_51.sh || exit 1
grep -q "STEP51 DONE" $D/progress51.txt || exit 1
bash $D/driver6_523.sh || exit 1
grep -q "STEP53 DONE" $D/progress523.txt || exit 1
bash $D/driver6_54.sh || exit 1
grep -q "STEP54 DONE" $D/progress54.txt || exit 1
echo "$(TZ=Australia/Melbourne date '+%Y-%m-%dT%H:%M:%S%z') FIX6 EVIDENCE DONE" >> $D/progress6.txt
