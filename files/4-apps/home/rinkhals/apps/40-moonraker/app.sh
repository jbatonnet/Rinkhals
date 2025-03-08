source /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PIDS=$(get_by_name moonraker.sh)

    if [ "$PIDS" == "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        report_status $APP_STATUS_STARTED
    fi
}
start() {
    stop
    
    cd $APP_ROOT
    chmod +x moonraker.sh
    ./moonraker.sh &
}
stop() {
    kill_by_name moonraker.py
    kill_by_name moonraker-proxy.py
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
