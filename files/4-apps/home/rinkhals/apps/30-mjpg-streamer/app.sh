source /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PIDS=$(get_by_name mjpg_streamer)

    if [ "$PIDS" = "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        report_status $APP_STATUS_STARTED "$PIDS"
    fi
}
start() {
    kill_by_name mjpg_streamer

    CAMERAS=$(ls /dev/v4l/by-id/*-index0 2> /dev/null)
    if [ "$CAMERAS" = "" ]; then
        log "No camera found. mjpg-streamer will not start"
        return
    fi

    kill_by_name gkcam
    sleep 1

    RESOLUTION=$(get_app_property 30-mjpg-streamer resolution)
    if [ "$RESOLUTION" != "" ]; then
        RESOLUTION="-r $RESOLUTION"
    else
        RESOLUTION=""
    fi

    PORT=8080
    for CAMERA in $CAMERAS; do
        #log "Starting mjpg-streamer for $CAMERA on port $PORT"
        mjpg_streamer -i "/usr/lib/mjpg-streamer/input_uvc.so -d $CAMERA $RESOLUTION -n" -o "/usr/lib/mjpg-streamer/output_http.so -p $PORT -w /usr/share/mjpg-streamer/www" >> $RINKHALS_ROOT/logs/app-mjpg-streamer.log 2>&1 &
        wait_for_port $PORT
        PORT=$(($PORT + 1))
    done
}
stop() {
    kill_by_name gkcam
    kill_by_name mjpg_streamer
    sleep 1

    cd /userdata/app/gk

    LD_LIBRARY_PATH=/userdata/app/gk:$LD_LIBRARY_PATH \
        ./gkcam &> $RINKHALS_ROOT/logs/gkcam.log &
}

case "$1" in
    status)
        status
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {status|start|stop}" >&2
        exit 1
        ;;
esac