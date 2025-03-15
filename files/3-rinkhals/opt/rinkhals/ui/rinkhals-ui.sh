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
if [ "$KOBRA_MODEL_CODE" = "KS1" ]; then
    SCALE="0.75"
    ROTATION="0"
    FILTER="[0:v] drawbox=x=0:y=0:w=iw:h=ih:t=fill:c=black"
else
    SCALE="0.5"
    ROTATION="PI/2"
    FILTER="[0:v] drawbox=x=0:y=0:w=iw-24:h=ih:t=fill:c=black"
fi

FILTER="$FILTER [1a]; [1:v] rotate=a=${ROTATION} [1b]; [1b] scale=w=iw*${SCALE}:h=ih*${SCALE} [1c]; [1a][1c] overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2"
/ac_lib/lib/third_bin/ffmpeg -f fbdev -i /dev/fb0 -i $RINKHALS_ROOT/opt/rinkhals/ui/icon.bmp -frames:v 1 -filter_complex "$FILTER" -pix_fmt bgra -f fbdev /dev/fb0 1>/dev/null 2>/dev/null &

# Start Python UI
kill_by_name rinkhals-ui.py
python $RINKHALS_ROOT/opt/rinkhals/ui/rinkhals-ui.py | tee -a $RINKHALS_ROOT/logs/rinkhals-ui.log 2>&1

echo "Done!"
