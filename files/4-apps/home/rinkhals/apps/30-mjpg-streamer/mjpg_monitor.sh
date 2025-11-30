. /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))
APP_LOG=$RINKHALS_LOGS/app-mjpg-streamer.log

# Configuration for dual-mode operation
LOW_RES="640x480"       # For AI features (spaghetti detection, etc.)
HIGH_RES="1280x720"     # For active viewing
LOW_RES_FPS=10          # Lower FPS for AI monitoring
HIGH_RES_FPS=15         # Higher FPS for viewing
JPEG_QUALITY=70         # Balance between quality and memory

# Track current mode
current_mode="low"      # Start in low-res mode

get_printer_state() {
    curl -s "http://127.0.0.1:7125/printer/objects/query?print_stats" | jq -r ".result.status.print_stats.state" 2> /dev/null
}

get_cameras() {
    echo $(v4l2-ctl --list-devices 2>/dev/null | grep '/dev/video' | sort 2> /dev/null)
}

check_active_clients() {
    # Check if anyone is actively streaming from port 8080+
    # Returns 0 (true) if clients found, 1 (false) if no clients
    # Note: Using netstat instead of lsof because BusyBox lsof doesn't support -sTCP:ESTABLISHED properly
    for port in 8080 8081 8082; do
        if netstat -tn 2>/dev/null | grep -q ":$port.*ESTABLISHED"; then
            return 0  # Clients found
        fi
    done
    return 1  # No clients
}

start_mjpg_streamer_with_mode() {
    local camera=$1
    local port=$2
    local mode=$3

    if [ "$mode" = "high" ]; then
        RESOLUTION=$HIGH_RES
        FPS=$HIGH_RES_FPS
        echo "Starting mjpg_streamer in HIGH mode ($HIGH_RES @ ${HIGH_RES_FPS} FPS) on port $port" >> $APP_LOG
    else
        RESOLUTION=$LOW_RES
        FPS=$LOW_RES_FPS
        echo "Starting mjpg_streamer in LOW mode ($LOW_RES @ ${LOW_RES_FPS} FPS) on port $port" >> $APP_LOG
    fi

    mjpg_streamer -i "/usr/lib/mjpg-streamer/input_uvc.so -d $camera -r $RESOLUTION -f $FPS -q $JPEG_QUALITY -n" \
        -o "/usr/lib/mjpg-streamer/output_http.so -p $port -w /usr/share/mjpg-streamer/www" \
        >> $APP_LOG 2>&1 &
}

restart_mjpg_streamer() {
    local force_mode=$1  # Optional: "low" or "high" to force a specific mode
    local mode  # Local variable for the mode to use in this restart

    cd $APP_ROOT

    echo "Killing mjpg_streamer processes" >> $APP_LOG
    kill_by_name mjpg_streamer
    sleep 2

    CAMERAS=$(ls /dev/v4l/by-id/*-index0 2> /dev/null)
    INDEX=0

    APP_JSON=$(cat $APP_ROOT/app.json)
    APP_JSON=$(echo $APP_JSON | jq ".properties = {}")

    # Determine mode: use forced mode or check for clients
    if [ -z "$force_mode" ]; then
        if check_active_clients; then
            mode="high"
        else
            mode="low"
        fi
    else
        mode=$force_mode
    fi

    for CAMERA in $CAMERAS; do
        echo "Found camera $CAMERA" >> $APP_LOG

        # List camera resolutions (with fallback if v4l2-ctl not available)
        RESOLUTIONS=$(v4l2-ctl -w -d $CAMERA --list-formats-ext 2>/dev/null | sed -n '/MJPG/,$p' | sed '/Index/,$d' | grep Size | awk '{print $3}' | sort -ruV)
        if [ "$RESOLUTIONS" = "" ]; then
            echo "v4l2-ctl not available or no MJPG resolutions found, using defaults" >> $APP_LOG
            RESOLUTIONS="1920x1080 1280x720 640x480"
        fi
        echo "Camera $INDEX resolutions: $(echo $RESOLUTIONS)" >> $APP_LOG

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

        # Check user preference
        USER_RESOLUTION=$(get_app_property 30-mjpg-streamer camera_$INDEX)
        if [ "$USER_RESOLUTION" = "Disabled" ] || [ "$USER_RESOLUTION" = "Anycubic" ]; then
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

        # Start in appropriate mode
        start_mjpg_streamer_with_mode "$CAMERA" "$PORT" "$mode"

        wait_for_port $PORT
        INDEX=$(($INDEX + 1))
    done

    # Update global current_mode after successful restart
    current_mode=$mode

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

previous_cameras=$(get_cameras)
restart_mjpg_streamer "low"  # Start in low-res mode

# Main monitoring loop with timeout system
check_counter=0
high_mode_start_time=0      # Unix timestamp when HIGH mode was started
HIGH_MODE_TIMEOUT=300       # 5 minutes in seconds
previous_client_count=0     # Track client count to detect new connections

echo "Main loop started - will switch to HIGH mode on demand, auto-downgrade after 5min" >> $APP_LOG

while [ 1 ]; do
    # Check for camera changes
    current_cameras=$(get_cameras)
    if [ "$current_cameras" != "$previous_cameras" ]; then
        previous_cameras="$current_cameras"
        echo "Camera changed, restarting mjpg-streamer..." >> $APP_LOG
        restart_mjpg_streamer
    fi

    # Check for active clients every 10 seconds
    check_counter=$((check_counter + 1))
    if [ $check_counter -ge 2 ]; then  # 2 * 5s = 10s
        check_counter=0

        # Count active clients
        client_count=$(netstat -tn 2>/dev/null | grep -c ":8080.*ESTABLISHED")

        # Determine desired mode based on clients and timeout
        if [ "$client_count" -gt 0 ]; then
            # Clients are active
            current_time=$(date +%s)

            if [ "$current_mode" = "low" ]; then
                # Switch to HIGH mode and start timer
                desired_mode="high"
                high_mode_start_time=$current_time
                previous_client_count=$client_count
                echo "Switching to HIGH mode ($client_count clients connected)" >> $APP_LOG
            elif [ "$current_mode" = "high" ]; then
                # Already in HIGH mode - check timeout and new clients
                elapsed=$((current_time - high_mode_start_time))

                # Reset timer if new clients joined (refresh/new tab)
                if [ "$client_count" -gt "$previous_client_count" ]; then
                    echo "New clients detected ($previous_client_count → $client_count), resetting HIGH mode timer" >> $APP_LOG
                    high_mode_start_time=$current_time
                    previous_client_count=$client_count
                fi

                # Force downgrade to LOW after 5 minutes
                if [ "$elapsed" -gt "$HIGH_MODE_TIMEOUT" ]; then
                    desired_mode="low"
                    echo "HIGH mode timeout reached (${elapsed}s), forcing downgrade to LOW mode" >> $APP_LOG
                else
                    desired_mode="high"
                fi
            fi
        else
            # No clients - switch to LOW mode
            desired_mode="low"
            if [ "$current_mode" = "high" ]; then
                echo "No clients detected, switching to LOW mode" >> $APP_LOG
            fi
        fi

        # Switch mode if needed
        if [ "$current_mode" != "$desired_mode" ]; then
            restart_mjpg_streamer "$desired_mode"
        fi
    fi

    sleep 5
done
