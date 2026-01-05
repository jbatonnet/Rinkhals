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

    case "$KOBRA_MODEL_CODE" in
        KS1)
            ROTATION=180
            MIN_X=0
            MAX_X=800
            MIN_Y=0
            MAX_Y=480
            # Average CPU is 15-20% with 3 FPS
            FPS=3
            ;;
        KS1M)
            ROTATION=180
            MIN_X=0
            MAX_X=800
            MIN_Y=0
            MAX_Y=480
            # Average CPU is 15-20% with 3 FPS
            FPS=3
            ;;
        K3M)
            ROTATION=90
            MIN_X=25
            MAX_X=460
            MIN_Y=235
            MAX_Y=25
            # Average CPU is 10% with 5 FPS
            FPS=5
            ;;
        *)
            ROTATION=270
            MIN_X=25
            MAX_X=460
            MIN_Y=235
            MAX_Y=25
            # Average CPU is 10% with 5 FPS
            FPS=5
            ;;
    esac

    drm-vncserver -n Rinkhals -t /dev/input/event0 -c $MIN_X,$MAX_X,$MIN_Y,$MAX_Y -r $ROTATION -F $FPS -w $APP_ROOT/novnc >> $RINKHALS_LOGS/app-drm-vncserver.log 2>&1 &
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
