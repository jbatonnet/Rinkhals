source /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname $(realpath $0))
APP_NAME="10-hostname-dns"

resolve_hostname() {
    HOSTNAME=$(get_app_property $APP_NAME hostname)

    if [ -z "$HOSTNAME" ]; then
        MODEL="$KOBRA_MODEL_CODE"
        SUFFIX=$(printf '%s' "$KOBRA_DEVICE_ID" | tail -c 4)

        if [ -n "$MODEL" ]; then
            HOSTNAME="kobra-${MODEL}"
        else
            HOSTNAME="kobra"
        fi

        if [ -n "$SUFFIX" ]; then
            HOSTNAME="${HOSTNAME}-${SUFFIX}"
        fi
    fi

    # Sanitize: lowercase, replace invalid chars with hyphens, trim leading/trailing hyphens
    HOSTNAME=$(echo "$HOSTNAME" | tr 'A-Z' 'a-z' | sed 's/[^a-z0-9-]/-/g; s/^-*//; s/-*$//' | head -c 63)

    # Final guard: if sanitization produced an empty string, use a fallback
    if [ -z "$HOSTNAME" ]; then
        HOSTNAME="kobra"
    fi

    echo "$HOSTNAME"
}

status() {
    PIDS=$(get_by_name mdns_responder.py)

    if [ "$PIDS" = "" ]; then
        report_status $APP_STATUS_STOPPED
    else
        report_status $APP_STATUS_STARTED "$PIDS"
    fi
}

start() {
    stop

    HOSTNAME=$(resolve_hostname)
    log "Setting hostname to: $HOSTNAME"

    # Set system hostname
    if hostname "$HOSTNAME"; then
        echo "$HOSTNAME" > /etc/hostname
    else
        log "/!\ Failed to set hostname to $HOSTNAME"
    fi

    # Propagate hostname via DHCP if enabled
    DHCP_ENABLED=$(get_app_property $APP_NAME dhcp_hostname)
    if [ "$DHCP_ENABLED" = "True" ]; then
        # Restart each udhcpc instance with -H so the router registers the hostname
        for UDHCPC_PID in $(get_by_name udhcpc); do
            UDHCPC_IFACE=$(cat /proc/$UDHCPC_PID/cmdline 2>/dev/null | tr '\0' '\n' | grep -A1 -- '^-i$' | tail -1)
            if [ -n "$UDHCPC_IFACE" ]; then
                kill $UDHCPC_PID
                udhcpc -i "$UDHCPC_IFACE" -H "$HOSTNAME" -b &
            fi
        done

    fi

    # Start mDNS responder
    mkdir -p $RINKHALS_LOGS
    cd $APP_ROOT
    python3 mdns_responder.py "$HOSTNAME" >> $RINKHALS_LOGS/app-hostname-dns.log 2>&1 &
}

stop() {
    kill_by_name mdns_responder.py
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
