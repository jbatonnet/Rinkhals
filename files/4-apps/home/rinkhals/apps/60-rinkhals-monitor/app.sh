. /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PID=$(cat /tmp/rinkhals/monitor.pid 2> /dev/null)
    if [ "$PID" == "" ]; then
        report_status $APP_STATUS_STOPPED
        return
    fi

    PS=$(ps | grep $PID | grep -v grep)
    if [ "$PS" == "" ]; then
        report_status $APP_STATUS_STOPPED
        return
    fi

    report_status $APP_STATUS_STARTED $PID
}
start() {
    stop
    cd $APP_ROOT

    mkdir -p /tmp/rinkhals

    chmod +x ./rinkhals-monitor
    env GOMEMLIMIT=10MiB GOGC=20 GODEBUG=madvdontneed=1 ./rinkhals-monitor > /dev/null 2>&1 &
    PID=$!
    if [ "$?" == 0 ]; then
        echo $PID > /tmp/rinkhals/monitor.pid
    fi
}
stop() {
    PID=$(cat /tmp/rinkhals/monitor.pid 2> /dev/null)
    kill_by_id $PID
    rm /tmp/rinkhals/monitor.pid 2> /dev/null
    kill_by_name rinkhals-monitor
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
