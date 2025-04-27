source /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PIDS=$(get_by_name drm-vncserver)

    if [ "$PIDS" == "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        report_status $APP_STATUS_STARTED "$PIDS"
    fi
}

start() {
    kill_by_name drm-vncserver

    VNC_PORT=5900
    WEB_PORT=5800
    #TODO Add touch calibration and rotation for KS1
    drm-vncserver -n Rinkhals -t /dev/input/event0 -c 25,460,235,25 -r 270 -F 5 -w $APP_ROOT/novnc >> $RINKHALS_ROOT/logs/app-drm-vncserver.log 2>&1 &
    wait_for_port $VNC_PORT
    wait_for_port $WEB_PORT
}

stop() {
    kill_by_name drm-vncserver
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
