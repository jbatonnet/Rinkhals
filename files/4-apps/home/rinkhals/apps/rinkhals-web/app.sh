. /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PID=$(cat /tmp/rinkhals-web.pid 2> /dev/null)
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
        echo $PID > /tmp/rinkhals-web.pid
    fi
}
debug() {
    stop

    mkdir -p /useremain/tmp
    
    sed "s#\./#$APP_ROOT/#g" $APP_ROOT/lighttpd.conf > $APP_ROOT/lighttpd.conf.tmp
    DEBUG=True lighttpd -D -f $APP_ROOT/lighttpd.conf.tmp
}
stop() {
    PID=$(cat /tmp/rinkhals-web.pid 2> /dev/null)
    kill_by_id $PID
    rm /tmp/rinkhals-web.pid 2> /dev/null
}

case "$1" in
    status)
        status
        ;;
    start)
        start
        ;;
    debug)
        debug
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {status|start|debug|stop}" >&2
        exit 1
        ;;
esac
