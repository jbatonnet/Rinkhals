source /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PIDS=$(get_by_name mjpg_streamer)

    if [ "$PIDS" == "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        report_status $APP_STATUS_STARTED
    fi
}
start() {
    if [ ! -e /dev/video10 ]; then
        log "Webcam /dev/video10 not found. mjpg-streamer will not start"
        return
    fi

    kill_by_name mjpg_streamer
    kill_by_name gkcam
    sleep 1

    mjpg_streamer -i "/usr/lib/mjpg-streamer/input_uvc.so -d /dev/video10 -n" -o "/usr/lib/mjpg-streamer/output_http.so -w /usr/share/mjpg-streamer/www" >> $RINKHALS_ROOT/logs/app-mjpg-streamer.log 2>&1 &
    wait_for_port 8080
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