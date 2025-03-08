source /useremain/rinkhals/.current/tools.sh

EXAMPLE_ROOT=$(dirname $(realpath $0))

status() {
    mkdir -p /tmp/app-example
    STATUS=$(cat /tmp/app-example/.status 2> /dev/null)

    if [ "$STATUS" == "1" ]; then
        report_status $APP_STATUS_STARTED
    else
        report_status $APP_STATUS_STOPPED
    fi
}
start() {
    mkdir -p /tmp/app-example
    echo 1 > /tmp/app-example/.status
    log "Started example app $EXAMPLE_VERSION from $EXAMPLE_ROOT"
}
stop() {
    mkdir -p /tmp/app-example
    echo 0 > /tmp/app-example/.status
    log "Stopped example app"
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
