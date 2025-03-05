kill_by_name() {
    PIDS=`ps | grep "$1" | grep -v grep | awk '{print $1}'`

    for PID in `echo "$PIDS"`; do
        CMDLINE=`cat /proc/$PID/cmdline` 2>/dev/null

        echo "Killing $PID ($CMDLINE)"
        kill -9 $PID
    done
}

# Find where we are
cd $(dirname $0)/../../..
RINKHALS_ROOT=$(pwd)

echo
echo "-- Rinkhals UI --"
echo "Root: $RINKHALS_ROOT"
echo

# Add icon overlay while Python is loading
/ac_lib/lib/third_bin/ffmpeg -f fbdev -i /dev/fb0 -i $RINKHALS_ROOT/opt/rinkhals/ui/icon.bmp -frames:v 1 -filter_complex "[0:v] drawbox=x=0:y=0:w=iw-24:h=ih:t=fill:color=black [page]; [page][1:v] overlay=208:104" -pix_fmt bgra -f fbdev /dev/fb0 1>/dev/null 2>/dev/null &

# Start Python UI
kill_by_name rinkhals-ui.py
python $RINKHALS_ROOT/opt/rinkhals/ui/rinkhals-ui.py >> $RINKHALS_ROOT/logs/rinkhals-ui.log 2>&1

echo "Done!"
