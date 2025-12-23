. /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PID=$(cat /tmp/rinkhals/fluidd.pid 2> /dev/null)
    if [ "$PID" == "" ]; then
        report_status $APP_STATUS_STOPPED
        return
    fi

    PS=$(ps | grep $PID)
    if [ "$PS" == "" ]; then
        report_status $APP_STATUS_STOPPED
        return
    fi

    report_status $APP_STATUS_STARTED $PID
}
start() {
    stop

    mkdir -p /useremain/tmp
    
    sed "s#\./#$APP_ROOT/#g" $APP_ROOT/lighttpd.conf > $APP_ROOT/lighttpd.conf.tmp
    lighttpd -D -f $APP_ROOT/lighttpd.conf.tmp &> /dev/null &
    PID=$!
    if [ "$?" == 0 ]; then
        echo $PID > /tmp/rinkhals/fluidd.pid
    fi

    socat TCP-LISTEN:80,reuseaddr,fork TCP:localhost:4408 &> /dev/null &
    PID=$!
    if [ "$?" == 0 ]; then
        echo $PID > /tmp/rinkhals/fluidd-80.pid
    fi
}
stop() {
    PID=$(cat /tmp/rinkhals/fluidd.pid 2> /dev/null)
    kill_by_id $PID
    rm /tmp/rinkhals/fluidd.pid 2> /dev/null

    PID=$(cat /tmp/rinkhals/fluidd-80.pid 2> /dev/null)
    kill_by_id $PID
    rm /tmp/rinkhals/fluidd-80.pid 2> /dev/null
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
