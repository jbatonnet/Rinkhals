export RINKHALS_ROOT=$(realpath /useremain/rinkhals/.current)
export RINKHALS_VERSION=$(cat $RINKHALS_ROOT/.version)
export RINKHALS_HOME=/useremain/home/rinkhals
export RINKHALS_LOGS=/tmp/rinkhals

export KOBRA_MODEL_ID=$(cat /userdata/app/gk/config/api.cfg | sed -nr 's/.*"modelId"\s*:\s*"([0-9]+)".*/\1/p')

if [ "$KOBRA_MODEL_ID" == "20021" ]; then
    export KOBRA_MODEL="Anycubic Kobra 2 Pro"
    export KOBRA_MODEL_CODE=K2P
elif [ "$KOBRA_MODEL_ID" == "20024" ]; then
    export KOBRA_MODEL="Anycubic Kobra 3"
    export KOBRA_MODEL_CODE=K3
elif [ "$KOBRA_MODEL_ID" == "20025" ]; then
    export KOBRA_MODEL="Anycubic Kobra S1"
    export KOBRA_MODEL_CODE=KS1
elif [ "$KOBRA_MODEL_ID" == "20026" ]; then
    export KOBRA_MODEL="Anycubic Kobra 3 Max"
    export KOBRA_MODEL_CODE=K3M
elif [ "$KOBRA_MODEL_ID" == "20027" ]; then
    export KOBRA_MODEL="Anycubic Kobra 3 V2"
    export KOBRA_MODEL_CODE=K3V2
elif [ "$KOBRA_MODEL_ID" == "20029" ]; then
    export KOBRA_MODEL="Anycubic Kobra S1 Max"
    export KOBRA_MODEL_CODE=KS1M
fi

export KOBRA_VERSION=$(cat /useremain/dev/version)
export KOBRA_DEVICE_ID=$(cat /useremain/dev/device_id 2> /dev/null)

export ORIGINAL_ROOT=/tmp/rinkhals/original

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

    mkdir -p $RINKHALS_LOGS
    echo "$(date): ${*}" >> $RINKHALS_LOGS/rinkhals.log
}
quit() {
    exit 1
}

check_compatibility() {
    if [ "$KOBRA_MODEL_CODE" != "K2P" ] && [ "$KOBRA_MODEL_CODE" == "K3" ] && [ "$KOBRA_MODEL_CODE" == "KS1" ] && [ "$KOBRA_MODEL_CODE" == "K3M" ]; then
        log "Your printer's model is not recognized, exiting"
        quit
    fi
}
is_supported_firmware() {
    SUPPORTED=0
    [ "$KOBRA_MODEL_CODE" = "KS1M" ] && [ "$KOBRA_VERSION" = "2.1.6" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "KS1" ] && [ "$KOBRA_VERSION" = "2.6.0.0" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "KS1" ] && [ "$KOBRA_VERSION" = "2.5.9.9" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "KS1" ] && [ "$KOBRA_VERSION" = "2.5.8.8" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "K3V2" ] && [ "$KOBRA_VERSION" = "1.1.0.4" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "K3V2" ] && [ "$KOBRA_VERSION" = "1.1.0.1" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "K3M" ] && [ "$KOBRA_VERSION" = "2.5.1.7" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "K3M" ] && [ "$KOBRA_VERSION" = "2.5.1.3" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "K3" ] && [ "$KOBRA_VERSION" = "2.4.5" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "K3" ] && [ "$KOBRA_VERSION" = "2.4.4.7" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "K2P" ] && [ "$KOBRA_VERSION" = "3.1.4" ] && SUPPORTED=1
    [ "$KOBRA_MODEL_CODE" = "K2P" ] && [ "$KOBRA_VERSION" = "3.1.2.3" ] && SUPPORTED=1
    echo $SUPPORTED
}

install_swu() {
    SWU_FILE=$(realpath $1)
    shift

    echo "> Extracting $SWU_FILE ..."

    mkdir -p /useremain/update_swu
    rm -rf /useremain/update_swu/*

    cd /useremain/update_swu

    unzip -P U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w= $SWU_FILE -d /useremain
    if [ -f /useremain/update_swu/setup.tar.gz ]; then
        tar -xzf /useremain/update_swu/setup.tar.gz -C /useremain/update_swu
    elif [ -f /useremain/update_swu/setup.tar ]; then
        tar -xf /useremain/update_swu/setup.tar -C /useremain/update_swu
    fi

    echo "> Running update.sh ..."

    chmod +x update.sh
    ./update.sh $@
}

get_command_line() {
    PID=$1

    CMDLINE=$(cat /proc/$PID/cmdline 2> /dev/null)
    CMDLINE=$(echo $CMDLINE | head -c 80)

    echo $CMDLINE
}
kill_by_id() {
    PID=$1
    SIGNAL=${2:-9}
    
    if [ "$PID" == "" ]; then
        return
    fi
    if [ ! -e /proc/$PID/cmdline ]; then
        return
    fi

    CMDLINE=$(get_command_line $PID)

    log "Killing $PID ($CMDLINE)"
    kill -$SIGNAL $PID
}

get_by_name() {
    echo $(ps | grep "$1" | grep -v grep | awk '{print $1}')
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
    SIGNAL=${2:-9}

    for PID in $(echo "$PIDS"); do
        kill_by_id $PID $SIGNAL
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
    SIGNAL=${2:-9}
    
    kill_by_id $PID $SIGNAL
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
    APP_LOG_PATH=$3

    echo "Status: $APP_STATUS"
    echo "PIDs: $APP_PIDS"
    echo "Log: $APP_LOG_PATH"
}
get_app_status() {
    APP=$1
    APP_ROOT=$(get_app_root $APP)

    if [ ! -f $APP_ROOT/app.sh ]; then
        return
    fi

    chmod +x $APP_ROOT/app.sh
    APP_STATUS=$($APP_ROOT/app.sh status | grep Status: | awk '{print $2}')

    echo $APP_STATUS
}
get_app_pids() {
    APP=$1
    APP_ROOT=$(get_app_root $APP)

    if [ ! -f $APP_ROOT/app.sh ]; then
        return
    fi

    chmod +x $APP_ROOT/app.sh
    APP_PIDS=$($APP_ROOT/app.sh status | grep PIDs: | awk '{$1=""; print $0}')

    echo $APP_PIDS
}
get_app_log() {
    APP=$1
    APP_ROOT=$(get_app_root $APP)

    if [ ! -f $APP_ROOT/app.sh ]; then
        return
    fi

    chmod +x $APP_ROOT/app.sh
    APP_PIDS=$($APP_ROOT/app.sh status | grep Log: | awk '{print $2}')

    echo $APP_PIDS
}

BUILTIN_APP_PATH=$RINKHALS_ROOT/home/rinkhals/apps
USER_APP_PATH=$RINKHALS_HOME/apps
TEMPORARY_APP_PATH=/tmp/rinkhals/apps

list_apps() {
    BUILTIN_APPS=$(find $BUILTIN_APP_PATH -type d -mindepth 1 -maxdepth 1 -exec basename {} \; 2> /dev/null)
    USER_APPS=$(find $USER_APP_PATH -type d -mindepth 1 -maxdepth 1 -exec basename {} \; 2> /dev/null)

    APPS=$(printf "$BUILTIN_APPS\n$USER_APPS" | sort -uV)
    echo $APPS
}
get_app_root() {
    APP=$1
    
    USER_APP_ROOT=$USER_APP_PATH/$APP
    BUILTIN_APP_ROOT=$BUILTIN_APP_PATH/$APP

    if [ -e "$USER_APP_ROOT" ]; then
        echo "$USER_APP_ROOT"
    else
        echo "$BUILTIN_APP_ROOT"
    fi
}
is_app_enabled() {
    app=$1
    app_root=$(get_app_root $app)

    if ([ -f $app_root/.enabled ] || [ -f $RINKHALS_HOME/apps/$app.enabled ]) && [ ! -f $app_root/.disabled ] && [ ! -f $RINKHALS_HOME/apps/$app.disabled ]; then
        echo 1
    else
        echo 0
    fi
}
enable_app() {
    app=$1
    app_root=$(get_app_root $app)

    if [ ! -d $RINKHALS_HOME/apps ]; then
        mkdir -p $RINKHALS_HOME/apps
    fi

    # If this is a built-in app, handle app.enabled / app.disabled
    if [[ "$app_root" == "$BUILTIN_APP_PATH*" ]]; then
        if [ -e $RINKHALS_HOME/apps/$app.disabled ]; then
            rm $RINKHALS_HOME/apps/$app.disabled
        fi
        if [ ! -e $app_root/.enabled ]; then
            touch $RINKHALS_HOME/apps/$app.enabled
        fi

    # If this is a user app, handle app/.enabled / app/.disabled
    else
        rm -f $RINKHALS_HOME/apps/$app.enabled
        rm -f $RINKHALS_HOME/apps/$app.disabled
        rm -f $RINKHALS_HOME/apps/$app/.disabled
        touch $RINKHALS_HOME/apps/$app/.enabled
    fi
}
disable_app() {
    app=$1
    app_root=$(get_app_root $app)

    if [ ! -d $RINKHALS_HOME/apps ]; then
        mkdir -p $RINKHALS_HOME/apps
    fi

    # If this is a built-in app, handle app.enabled / app.disabled
    if [[ "$app_root" == "$BUILTIN_APP_PATH*" ]]; then
        if [ -e $RINKHALS_HOME/apps/$app.enabled ]; then
            rm $RINKHALS_HOME/apps/$app.enabled
        fi
        touch $RINKHALS_HOME/apps/$app.disabled

    # If this is a user app, handle app/.enabled / app/.disabled
    else
        rm -f $RINKHALS_HOME/apps/$app.enabled
        rm -f $RINKHALS_HOME/apps/$app.disabled
        rm -f $RINKHALS_HOME/apps/$app/.enabled
        touch $RINKHALS_HOME/apps/$app/.disabled
    fi
}
start_app() {
    APP=$1
    TIMEOUT=${2:-60}

    APP_ROOT=$(get_app_root $APP)

    PWD=$(pwd)
    cd $APP_ROOT
    chmod +x $APP_ROOT/app.sh

    if [ "$TIMEOUT" = "" ]; then
        $APP_ROOT/app.sh start
    else
        timeout -t $TIMEOUT sh -c "$APP_ROOT/app.sh start"

        if [ "$?" != "0" ]; then
            log "/!\ Timeout while starting $APP ($APP_ROOT)"
            stop_app $APP
        fi
    fi

    cd $PWD
}
stop_app() {
    APP=$1
    APP_ROOT=$(get_app_root $APP)

    chmod +x $APP_ROOT/app.sh
    $APP_ROOT/app.sh stop
}

# list_app_properties() {
#     APP=$1
#     APP_ROOT=$(get_app_root $APP)

#     if [ ! -f $APP_ROOT/app.json ]; then
#         return
#     fi

#     cat $APP_ROOT/app.json | sed 's/\/\/.*//' | jq -r '.properties | keys[]'
# }
get_app_property() {
    APP=$1
    PROPERTY=$2

    CONFIG_PATH=$USER_APP_PATH/$APP.config
    TEMPORARY_CONFIG_PATH=$TEMPORARY_APP_PATH/$APP.config

    VALUE=$(cat $TEMPORARY_CONFIG_PATH 2>/dev/null | jq -r ".$PROPERTY")
    if [ "$VALUE" = "" ] || [ "$VALUE" = "null" ]; then
        VALUE=$(cat $CONFIG_PATH 2>/dev/null | jq -r ".$PROPERTY")
    fi
    if [ "$VALUE" = "null" ]; then
        VALUE=
    fi
    if [ "$VALUE" = "" ]; then
        APP_ROOT=$(get_app_root $APP)
        VALUE=$(cat $APP_ROOT/app.json 2>/dev/null | jq -r ".properties.$PROPERTY.default")
        if [ "$VALUE" = "null" ]; then
            VALUE=
        fi
    fi

    echo $VALUE
}
set_app_property() {
    APP=$1
    PROPERTY=$2
    VALUE=$3
    
    if [ ! -d $RINKHALS_HOME/apps ]; then
        mkdir -p $RINKHALS_HOME/apps
    fi

    CONFIG_PATH=$USER_APP_PATH/$APP.config
    CONFIG=$(cat $CONFIG_PATH 2>/dev/null)
    CONFIG=${CONFIG:-'{}'}

    echo $CONFIG | jq ".$PROPERTY = \"$VALUE\"" > $CONFIG_PATH
}
set_temporary_app_property() {
    APP=$1
    PROPERTY=$2
    VALUE=$3

    mkdir -p $TEMPORARY_APP_PATH

    TEMPORARY_CONFIG_PATH=$TEMPORARY_APP_PATH/$APP.config
    CONFIG=$(cat $TEMPORARY_CONFIG_PATH 2>/dev/null)
    CONFIG=${CONFIG:-'{}'}

    echo $CONFIG | jq ".$PROPERTY = \"$VALUE\"" > $TEMPORARY_CONFIG_PATH
}
remove_app_property() {
    APP=$1
    PROPERTY=$2
    
    if [ ! -d $RINKHALS_HOME/apps ]; then
        return
    fi

    CONFIG_PATH=$USER_APP_PATH/$APP.config
    CONFIG=$(cat $CONFIG_PATH 2>/dev/null)
    CONFIG=${CONFIG:-'{}'}

    echo $CONFIG | jq "del(.$PROPERTY)" > $CONFIG_PATH
}
clear_app_properties() {
    APP=$1
    
    if [ ! -d $RINKHALS_HOME/apps ]; then
        return
    fi

    CONFIG_PATH=$USER_APP_PATH/$APP.config
    rm $CONFIG_PATH 2>/dev/null
}
