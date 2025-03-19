source /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PIDS=$(get_by_name moonraker.py)

    if [ "$PIDS" == "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        report_status $APP_STATUS_STARTED
    fi
}
start() {
    stop
    
    cd $APP_ROOT

    # Create Python venv
    python -m venv --without-pip .
    . bin/activate

    HOME=/userdata/app/gk python ./moonraker/moonraker/moonraker.py >> $RINKHALS_ROOT/logs/app-moonraker.log 2>&1 &

    PID=$(get_by_name moonraker-proxy.py)
    if [ "$PID" = "" ]; then
        socat TCP-LISTEN:7125,reuseaddr,fork TCP:localhost:7126 &> /dev/null &
    fi
}
stop() {
    kill_by_name moonraker.py

    PID=$(get_by_port 7125)
    if [ "$PID" != "" ]; then
        CMDLINE=$(get_command_line $PID)
        if [ "$(echo $CMDLINE | grep socat)" != "" ]; then
            kill -9 $PID
        fi
    fi
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
