export RINKHALS_ROOT=$(realpath /useremain/rinkhals/.current)
export RINKHALS_VERSION=$(cat $RINKHALS_ROOT/.version)
export RINKHALS_HOME=/useremain/home/rinkhals

msleep() {
    usleep $(($1 * 1000))
}
beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}
log() {
    echo "${*}"

    mkdir -p $RINKHALS_ROOT/logs
    echo "$(date): ${*}" >> $RINKHALS_ROOT/logs/rinkhals.log
}
quit() {
    exit 1
}

get_command_line() {
    PID=$1

    CMDLINE=$(cat /proc/$PID/cmdline)
    CMDLINE=$(echo $CMDLINE | head -c 80)

    echo $CMDLINE
}

get_by_name() {
    ps | grep "$1" | grep -v grep | awk '{print $1}'
}
wait_for_name() {
    DELAY=250
    TOTAL=0

    while [ 1 ]; do
        PIDS=$(get_by_name $1)
        if [ "$PIDS" != "" ]; then
            return
        fi

        if [ "$TOTAL" -gt 30000 ]; then
            log "/!\ Timeout waiting for $1 to start"
            quit
        fi

        msleep $DELAY

        TOTAL=$(( $TOTAL + $DELAY ))
    done
}
assert_by_name() {
    PIDS=$(get_by_name $1)

    if [ "$PIDS" == "" ]; then
        log "/!\ $1 should be running but it's not"
        quit
    fi
}
kill_by_name() {
    PIDS=$(get_by_name $1)

    for PID in $(echo "$PIDS"); do
        CMDLINE=$(get_command_line $PID)

        log "Killing $PID ($CMDLINE)"
        kill -9 $PID
    done
}

get_by_port() {
    XPORT=$(printf "%04X" ${*})
    INODE=$(cat /proc/net/tcp | grep 00000000:$XPORT | awk '/.*:.*:.*/{print $10;}')

    if [[ "$INODE" != "" ]]; then
        PID=$(ls -l /proc/*/fd/* 2> /dev/null | grep "socket:\[$INODE\]" | awk -F'/' '{print $3}')
        echo $PID
    fi
}
wait_for_port() {
    DELAY=250
    TOTAL=0

    while [ 1 ]; do
        PID=$(get_by_port $1)
        if [ "$PID" != "" ]; then
            return
        fi

        if [ "$TOTAL" -gt 30000 ]; then
            log "/!\ Timeout waiting for port $1 to open"
            quit
        fi

        msleep $DELAY

        TOTAL=$(( $TOTAL + $DELAY ))
    done
}
assert_by_port() {
    PID=$(get_by_port $1)

    if [ "$PID" == "" ]; then
        log "/!\ $1 should be open but it's not"
        quit
    fi
}
kill_by_port() {
    PID=$(get_by_port $1)

    if [[ "$PID" != "" ]]; then
        CMDLINE=$(get_command_line $PID)

        log "Killing $PID ($CMDLINE)"
        kill -9 $PID
    fi
}
