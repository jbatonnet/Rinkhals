. /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

status() {
    PIDS=$(get_by_name moonraker.py)

    if [ "$PIDS" == "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        report_status $APP_STATUS_STARTED "$PIDS"
    fi
}
start() {
    stop

    cd $APP_ROOT

    chmod +x moonraker.sh
    ./moonraker.sh &
}
debug() {
    stop

    cd $APP_ROOT
    
    python -m venv --without-pip .
    . bin/activate

    cp -rf kobra.py moonraker/moonraker/components/kobra.py
    cp -rf mmu_ace.py moonraker/moonraker/components/mmu_ace.py
    python /opt/rinkhals/scripts/process-cfg.py moonraker.conf > /userdata/app/gk/printer_data/config/moonraker.generated.conf
    TMPDIR=/useremain/tmp HOME=/userdata/app/gk python ./moonraker/moonraker/moonraker.py -c /userdata/app/gk/printer_data/config/moonraker.generated.conf $@
}
stop() {
    kill_by_name moonraker.py
}

case "$1" in
    status)
        status
        ;;
    start)
        start
        ;;
    debug)
        shift
        debug $@
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {status|start|debug|stop}" >&2
        exit 1
        ;;
esac
