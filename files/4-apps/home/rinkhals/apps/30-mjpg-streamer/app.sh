. /useremain/rinkhals/.current/tools.sh

export APP_ROOT=$(dirname $(realpath $0))
export APP_LOG=$RINKHALS_LOGS/app-mjpg-streamer.log

status() {
    PIDS=$(get_by_name mjpg_streamer)

    if [ "$PIDS" = "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        report_status $APP_STATUS_STARTED "$PIDS"
    fi
}
start() {
    cd $APP_ROOT
    echo "Starting mjpg_streamer app" >> $APP_LOG

    PIDS=$(get_by_name mjpg_monitor)
    if [ "$PIDS" = "" ]; then
        chmod +x ./mjpg_monitor.sh
        ./mjpg_monitor.sh >> $APP_LOG 2>&1 &
    fi

    echo "Killing mjpg_streamer processes" >> $APP_LOG
    kill_by_name mjpg_streamer
    sleep 2

    CAMERAS=$(ls /dev/v4l/by-id/*-index0 2> /dev/null)
    INDEX=0
    
    APP_JSON=$(cat $APP_ROOT/app.json)
    APP_JSON=$(echo $APP_JSON | jq ".properties = {}")

    for CAMERA in $CAMERAS; do
        echo "Found camera $CAMERA" >> $APP_LOG

        # List camera resolutions
        RESOLUTIONS=$(v4l2-ctl -w -d $CAMERA --list-formats-ext | sed -n '/MJPG/,$p' | sed '/Index/,$d' | grep Size | awk '{print $3}' | sort -ruV)
        echo "Camera $INDEX resolutions: $(echo $RESOLUTIONS)" >> $APP_LOG
        if [ "$RESOLUTIONS" = "" ]; then
            echo "No resolution found, skipping..." >> $APP_LOG
            continue
        fi

        # Update the JSON accordingly
        APP_JSON=$(echo $APP_JSON | jq ".properties.camera_$INDEX.display = \"Camera $INDEX\"")
        APP_JSON=$(echo $APP_JSON | jq ".properties.camera_$INDEX.type = \"enum\"")
        APP_JSON=$(echo $APP_JSON | jq ".properties.camera_$INDEX.default = \"default\"")

        RESOLUTIONS_JSON=$(echo $RESOLUTIONS | sed 's/ /","/g')
        DISABLED_RESOLUTION="Disabled"
        if [ "$INDEX" = "0" ]; then
            DISABLED_RESOLUTION="Anycubic"
        fi
        APP_JSON=$(echo $APP_JSON | jq ".properties.camera_$INDEX.options = [\"$DISABLED_RESOLUTION\",\"$RESOLUTIONS_JSON\"]")

        if echo "$RESOLUTIONS" | grep -q "1280x720"; then
            DEFAULT_RESOLUTION="1280x720"
        else
            DEFAULT_RESOLUTION="640x480"
        fi

        APP_JSON=$(echo $APP_JSON | jq ".properties.camera_$INDEX.default = \"$DEFAULT_RESOLUTION\"")
        echo $APP_JSON > $APP_ROOT/app.json

        # Start mjpg-streamer
        RESOLUTION=$(get_app_property 30-mjpg-streamer camera_$INDEX)
        if [ "$RESOLUTION" = "Disabled" ] || [ "$RESOLUTION" = "Anycubic" ]; then
            echo "Camera $INDEX is disabled, skipping..." >> $APP_LOG

            INDEX=$(($INDEX + 1))
            continue
        fi
        if [ "$INDEX" = "0" ]; then
            echo "Killing gkcam for camera $INDEX" >> $APP_LOG

            kill_by_name gkcam
            sleep 2
        fi

        PORT=$((8080 + $INDEX))

        if [ "$RESOLUTION" = "" ]; then
            mjpg_streamer -i "/usr/lib/mjpg-streamer/input_uvc.so -d $CAMERA -n" -o "/usr/lib/mjpg-streamer/output_http.so -p $PORT -w /usr/share/mjpg-streamer/www" >> $APP_LOG 2>&1 &
        else
            mjpg_streamer -i "/usr/lib/mjpg-streamer/input_uvc.so -d $CAMERA -r $RESOLUTION -n" -o "/usr/lib/mjpg-streamer/output_http.so -p $PORT -w /usr/share/mjpg-streamer/www" >> $APP_LOG 2>&1 &
        fi

        #wait_for_port $PORT
        INDEX=$(($INDEX + 1))
    done

    PIDS=$(get_by_name mjpg_streamer)
    if [ "$PIDS" = "" ]; then
        PIDS=$(get_by_name gkcam)
        if [ "$PIDS" = "" ]; then
            echo "No mjpg-streamer, starting gkcam..." >> $APP_LOG
            sleep 2

            cd /userdata/app/gk
            ./gkcam >> $RINKHALS_LOGS/gkcam.log 2>&1 &
        fi
    fi
}
stop() {
    kill_by_name gkcam
    kill_by_name mjpg_streamer
    kill_by_name mjpg_monitor
    sleep 1

    cd /userdata/app/gk

    LD_LIBRARY_PATH=/userdata/app/gk:$LD_LIBRARY_PATH \
        ./gkcam >> $RINKHALS_LOGS/gkcam.log 2>&1 &
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