source /useremain/rinkhals/.current/tools.sh

APPLICATION_INSIGHTS_KEY="3eb435a3-4533-4a1b-bac1-b019d9a46d43"

status() {
    report_status $APP_STATUS_STOPPED
}
start() {
    TIMESTAMP=$(TZ=UTC date +"%Y-%m-%dT%H:%M:%SZ")

    TELEMETRY_DOCUMENT=$(cat <<EOF
{
    "name": "AppEvents",
    "time": "$TIMESTAMP",
    "iKey": "$APPLICATION_INSIGHTS_KEY",
    "tags": {
        "ai.application.ver": "$RINKHALS_VERSION"
    },
    "data": {
        "baseType": "EventData",
        "baseData": {
            "name": "Rinkhals.Started"
        }
    }
}
EOF
)

    echo $TELEMETRY_DOCUMENT | curl -k -d@- https://dc.services.visualstudio.com/v2/track > /dev/null 2>&1
}
stop() {
    exit 0
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
