source /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PID=$(cat /tmp/rinkhals-fluidd.pid 2> /dev/null)
    if [ "$PID" == "" ]; then
        report_status $APP_STATUS_STOPPED
        return
    fi

    PS=$(ps | grep $PID)
    if [ "$PS" == "" ]; then
        report_status $APP_STATUS_STOPPED
        return
    fi

    report_status $APP_STATUS_STARTED
}
start() {
    lighttpd -f $APP_ROOT/lighttpd.conf &
    PID=$!
    echo $PID > /tmp/rinkhals-fluidd.pid

    # socat TCP-LISTEN:80,fork TCP:127.0.0.1:4409 &
}
stop() {
    PID=$(cat /tmp/rinkhals-fluidd.pid 2> /dev/null)

    if [ "$PID" != "" ]; then
        kill -9 $PID
    fi

    rm /tmp/rinkhals-fluidd.pid
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
