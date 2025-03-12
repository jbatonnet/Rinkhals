source /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PIDS=$(get_by_name moonraker-proxy.py)

    if [ "$PIDS" == "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        report_status $APP_STATUS_STARTED
    fi
}
start() {
    kill_by_port 7125

    cd $APP_ROOT
    python ./moonraker-proxy.py >> $RINKHALS_ROOT/logs/app-moonraker.log 2>&1 &
}
stop() {
    kill_by_name moonraker-proxy.py

    socat TCP-LISTEN:7125,reuseaddr,fork TCP:localhost:7126 &> /dev/null &
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
