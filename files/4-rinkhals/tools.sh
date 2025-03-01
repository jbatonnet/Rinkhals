export RINKHALS_ROOT=$(realpath /useremain/rinkhals/.current)
export RINKHALS_VERSION=$(cat $RINKHALS_ROOT/.version)
export RINKHALS_HOME=/useremain/home/rinkhals

export KOBRA_MODEL=$(cat /userdata/app/gk/printer.cfg | grep device_type | awk -F':' '{print $2}' | xargs)
export KOBRA_VERSION=$(cat /useremain/dev/version)

if [ "$KOBRA_MODEL" == "Anycubic Kobra 2 Pro" ]; then
    export KOBRA_MODEL_CODE=K2P
elif [ "$KOBRA_MODEL" == "Anycubic Kobra 3" ]; then
    export KOBRA_MODEL_CODE=K3
elif [ "$KOBRA_MODEL" == "Anycubic Kobra S1" ]; then
    export KOBRA_MODEL_CODE=KS1
fi

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

check_compatibility() {
    if [ "$KOBRA_MODEL_CODE" == "K2P" ]; then
        if [ "$KOBRA_VERSION" != "3.1.2.3" ]; then
            log "Your printer has firmware $KOBRA_VERSION. This Rinkhals version is only compatible with firmware 3.1.2.3 on the Kobra 2 Pro, stopping installation"
            quit
        fi
    elif [ "$KOBRA_MODEL_CODE" == "K3" ]; then
        if [ "$KOBRA_VERSION" != "2.3.5.3" ]; then
            log "Your printer has firmware $KOBRA_VERSION. This Rinkhals version is only compatible with firmware 2.3.5.3 on the Kobra 3, stopping installation"
            quit
        fi
    elif [ "$KOBRA_MODEL_CODE" == "KS1" ]; then
        if [ "$KOBRA_VERSION" != "2.4.6.6" ] && [ "$KOBRA_VERSION" != "2.4.8.3" ]; then
            log "Your printer has firmware $KOBRA_VERSION. This Rinkhals version is only compatible with firmwares 2.4.6.6 and 2.4.8.3 on the Kobra S1, stopping installation"
            quit
        fi
    else
        log "Your printer's model is not recognized, exiting"
        quit
    fi
}

install_swu() {
    SWU_FILE=$1

    echo "> Extracting $SWU_FILE ..."

    mkdir -p /useremain/update_swu
    rm -rf /useremain/update_swu/*

    cd /useremain/update_swu

    unzip -P U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w= $SWU_FILE -d /useremain
    tar -xzf /useremain/update_swu/setup.tar.gz -C /useremain/update_swu

    echo "> Running update.sh ..."

    chmod +x update.sh
    ./update.sh
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
    TOTAL=${2:-30000}

    while [ 1 ]; do
        PIDS=$(get_by_name $1)
        if [ "$PIDS" != "" ]; then
            return
        fi

        if [ "$TOTAL" -gt 30000 ]; then
            if [ "$3" != "" ]; then
                log "$3"
            else
                log "/!\ Timeout waiting for $1 to start"
            fi

            quit
        fi

        msleep $DELAY
        TOTAL=$(( $TOTAL - $DELAY ))
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
    TOTAL=${2:-30000}

    while [ 1 ]; do
        PID=$(get_by_port $1)
        if [ "$PID" != "" ]; then
            return
        fi

        if [ "$TOTAL" -lt 0 ]; then
            if [ "$3" != "" ]; then
                log "$3"
            else
                log "/!\ Timeout waiting for port $1 to open"
            fi

            quit
        fi

        msleep $DELAY
        TOTAL=$(( $TOTAL - $DELAY ))
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

wait_for_socket() {
    DELAY=250
    TOTAL=${2:-30000}

    while [ 1 ]; do
        timeout -t 1 socat $1 $1 2> /dev/null
        if [ "$?" -gt 127 ]; then
            return
        fi

        if [ "$TOTAL" -lt 0 ]; then
            if [ "$3" != "" ]; then
                log "$3"
            else
                log "/!\ Timeout waiting for socket $1 to listen"
            fi

            quit
        fi

        msleep $DELAY
        TOTAL=$(( $TOTAL - $DELAY ))
    done
}

export APP_STATUS_STARTED=started
export APP_STATUS_STOPPED=stopped

report_status() {
    APP_STATUS=$1
    APP_PIDS=$2

    echo "Status: $APP_STATUS"
    echo "PIDs: $APP_PIDS"
}
