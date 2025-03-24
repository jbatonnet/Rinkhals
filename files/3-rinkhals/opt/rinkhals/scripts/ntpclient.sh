export TZ=UTC

LEASE_FILE="/useremain/home/rinkhals/dhcp.lease"
NTP_SERVER="pool.ntp.org"

/sbin/udhcpc -i wlan0 > /dev/null 2>&1

if [ -f "$LEASE_FILE" ]; then
    LEASE_NTP=$(grep "NTP-Server:" "$LEASE_FILE" | awk '{print $2}')
    
    if [ -n "$LEASE_NTP" ] && [ "$LEASE_NTP" != "NONE" ]; then
        NTP_SERVER="$LEASE_NTP"
    fi
fi

while true; do
    timeout -t 5 sh -c "ntpclient -s -h $NTP_SERVER" > /dev/null 2>&1

    YEAR=$(date +%Y)
    if [ "$YEAR" -ne "1970" ]; then
        break
    fi

    sleep 5
done
