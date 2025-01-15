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

# Add icon overlay while Python is loading
usleep 100000
/ac_lib/lib/third_bin/ffmpeg -f fbdev -i /dev/fb0 -frames:v 1 -y /tmp/framebuffer.bmp 1>/dev/null 2>/dev/null
/ac_lib/lib/third_bin/ffmpeg -i /tmp/framebuffer.bmp -i $RINKHALS_ROOT/opt/rinkhals/ui/icon.bmp -filter_complex "[0:v][1:v] overlay=208:104" -pix_fmt bgra -f fbdev /dev/fb0 1>/dev/null 2>/dev/null

# Start Python UI
kill_by_name rinkhals-ui.py
python $RINKHALS_ROOT/opt/rinkhals/ui/rinkhals-ui.py

echo "Done!"
