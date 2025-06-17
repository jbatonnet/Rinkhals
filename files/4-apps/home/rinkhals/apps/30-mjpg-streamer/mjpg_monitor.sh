. /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))

get_printer_state() {
    curl -s "http://127.0.0.1:7125/printer/objects/query?print_stats" | jq -r ".result.status.print_stats.state" 2> /dev/null
}
get_cameras() {
    echo $(v4l2-ctl --list-devices 2>/dev/null | grep '/dev/video' | sort 2> /dev/null)
}

printer_state=$(get_printer_state)
previous_cameras=$(get_cameras)

while [ 1 ]; do
    printer_state=$(get_printer_state)

    # Exit monitor if printer is busy or Moonraker doesn't respond
    if [ "$printer_state" != "standby" ] && [ "$printer_state" != "complete" ]; then
        sleep 10
        continue
    fi

    current_cameras=$(get_cameras)

    if [ "$current_cameras" != "$previous_cameras" ]; then
        echo "Camera changed, restarting mjpg-streamer app..." >> $APP_LOG

        cd $APP_ROOT
        ./app.sh start &
        previous_cameras="$current_cameras"
    fi

    sleep 5
done
