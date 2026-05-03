# shellcheck source=../../../../../3-rinkhals/tools.sh
source /useremain/rinkhals/.current/tools.sh

APP_ROOT=$(dirname "$(realpath "$0")")
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
    # shellcheck disable=SC2019,SC2018 # (use only latin chars, others will be replaced with hyphens)
    HOSTNAME=$(echo "$HOSTNAME" | tr 'A-Z' 'a-z' | sed 's/[^a-z0-9-]/-/g; s/^-*//; s/-*$//' | head -c 63)

    # Final guard: if sanitization produced an empty string, use a fallback
    if [ -z "$HOSTNAME" ]; then
        HOSTNAME="kobra"
    fi

    echo "$HOSTNAME"
}

status() {
    PIDS=$(get_by_name mdns_responder.py; get_by_name dhcp_watchdog.sh)

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

    # Propagate hostname via DHCP if enabled.
    # K3SysUi may (re)spawn udhcpc without the hostname flag at any time,
    # so we run a watchdog that replaces rogue instances.
    DHCP_ENABLED=$(get_app_property $APP_NAME dhcp_hostname)
    if [ "$DHCP_ENABLED" = "True" ]; then
        cd "$APP_ROOT" || exit 1
        sh dhcp_watchdog.sh "$HOSTNAME" >> $RINKHALS_LOGS/app-hostname-dns-dhcp.log 2>&1 &
        log "Started udhcpc watchdog to propagate hostname via DHCP"
    fi

    # Start mDNS responder
    mkdir -p $RINKHALS_LOGS
    cd "$APP_ROOT" || exit 1
    python3 mdns_responder.py "$HOSTNAME" >> $RINKHALS_LOGS/app-hostname-dns-mdns.log 2>&1 &
    log "Started mDNS responder to propagate hostname via mDNS"
}

stop() {
    kill_by_name mdns_responder.py
    log "Stopped mDNS responder"
    kill_by_name dhcp_watchdog.sh
    log "Stopped udhcpc watchdog"
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
