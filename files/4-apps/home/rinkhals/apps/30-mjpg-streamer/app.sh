. /useremain/rinkhals/.current/tools.sh

export APP_ROOT=$(dirname $(realpath $0))
export APP_LOG=$RINKHALS_LOGS/app-mjpg-streamer.log

status() {
    PIDS=$(get_by_name mjpg_monitor)

    if [ "$PIDS" = "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        PIDS=$(get_by_name mjpg_streamer)
        report_status $APP_STATUS_STARTED "$PIDS"
    fi
}
start() {
    cd $APP_ROOT
    echo "Starting mjpg_streamer app" >> $APP_LOG

    PIDS=$(get_by_name mjpg_monitor)
    if [ "$PIDS" = "" ]; then
        chmod +x ./mjpg_monitor.sh
        ./mjpg_monitor.sh >> $APP_LOG 2>&1 &
    fi
}
debug() {
    kill_by_name mjpg_monitor

    cd $APP_ROOT

    chmod +x ./mjpg_monitor.sh
    ./mjpg_monitor.sh
}
stop() {
    kill_by_name gkcam
    kill_by_name mjpg_streamer
    kill_by_name mjpg_monitor
    sleep 1

    cd /userdata/app/gk

    LD_LIBRARY_PATH=/userdata/app/gk:$LD_LIBRARY_PATH \
        ./gkcam >> $RINKHALS_LOGS/gkcam.log 2>&1 &
}

case "$1" in
    status)
        status
        ;;
    start)
        start
        ;;
    debug)
        shift
        debug $@
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {status|start|stop}" >&2
        exit 1
        ;;
esac