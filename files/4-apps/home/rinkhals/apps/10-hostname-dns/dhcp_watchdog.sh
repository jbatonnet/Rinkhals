# Watchdog that ensures all udhcpc instances have the hostname flag set.
# K3SysUi may (re)spawn udhcpc without -x hostname: at any time,
# so this script periodically checks and replaces rogue instances.

# shellcheck source=../../../../../3-rinkhals/tools.sh
source /useremain/rinkhals/.current/tools.sh

HOSTNAME="$1"
CHECK_INTERVAL=30

if [ -z "$HOSTNAME" ]; then
    log "dhcp_watchdog: no hostname provided"
    exit 1
fi

log "dhcp_watchdog: started, monitoring for hostname '$HOSTNAME'"

while true; do
    sleep $CHECK_INTERVAL

    REPLACED_IFACES=""
    for UDHCPC_PID in $(get_by_name udhcpc); do
        CMDLINE=$(cat "/proc/$UDHCPC_PID/cmdline" 2>/dev/null | tr '\0' ' ')

        # Skip instances that already have the hostname flag
        if echo "$CMDLINE" | grep -q -- "-x hostname:$HOSTNAME"; then
            continue
        fi

        # Extract interface from this rogue instance
        IFACE=$(cat "/proc/$UDHCPC_PID/cmdline" 2>/dev/null | tr '\0' '\n' | grep -A1 -- '^-i$' | tail -1)
        if [ -z "$IFACE" ]; then
            continue
        fi

        log "dhcp_watchdog: killing rogue udhcpc PID $UDHCPC_PID on $IFACE"
        kill "$UDHCPC_PID"

        # Only spawn one replacement per interface per cycle
        if ! echo "$REPLACED_IFACES" | grep -q "$IFACE"; then
            log "dhcp_watchdog: starting udhcpc on $IFACE with hostname $HOSTNAME"
            # Use -b -i order to match K3SysUi's expected format,
            # so it can manage the lifecycle on WiFi reconnects
            udhcpc -b -i "$IFACE" -x hostname:"$HOSTNAME" &
            REPLACED_IFACES="$REPLACED_IFACES $IFACE"
        fi
    done
done
