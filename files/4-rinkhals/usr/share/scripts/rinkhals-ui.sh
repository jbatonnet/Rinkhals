kill_by_name() {
    PIDS=`ps | grep "$1" | grep -v grep | awk '{print $1}'`

    for PID in `echo "$PIDS"`; do
        CMDLINE=`cat /proc/$PID/cmdline` 2>/dev/null

        echo "Killing $PID ($CMDLINE)"
        kill -9 $PID
    done
}

# Run this script again so we run async
if [ "$1" == "" ]; then
    echo "Re-running async..."
    $0 async &
    exit 0
fi

# Find where we are
cd $(dirname $0)/../../..
RINKHALS_ROOT=$(pwd)

echo
echo "-- Rinkhals UI --"
echo "Root: $RINKHALS_ROOT"
echo

kill_by_name rinkhals-ui.py
python $RINKHALS_ROOT/usr/share/scripts/rinkhals-ui.py

echo "Done!"
