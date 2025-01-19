source $(dirname $(realpath $0))/tools.sh

quit() {
    echo
    log "/!\\ Startup failed, stopping Rinkhals..."

    beep 500
    msleep 500
    beep 500

    ./stop.sh
    touch /useremain/rinkhals/.disable-rinkhals

    exit 1
}

export TZ=UTC
ntpclient -s -h pool.ntp.org > /dev/null # Try to sync local time before starting

KOBRA_VERSION=$(cat /useremain/dev/version)
export RINKHALS_ROOT=$(dirname $(realpath $0))
export RINKHALS_VERSION=$(cat $RINKHALS_ROOT/.version)
export RINKHALS_HOME=/useremain/home/rinkhals

if [ "$KOBRA_VERSION" != "2.3.5.3" ]; then
    log "Your printer has firmware $KOBRA_VERSION. This Rinkhals version is only compatible with Kobra firmware 2.3.5.3, stopping startup"
    exit 1
fi

cd $RINKHALS_ROOT
rm -rf /useremain/rinkhals/.current 2> /dev/null
ln -s $RINKHALS_ROOT /useremain/rinkhals/.current

mkdir -p ./logs

if [ ! -f /tmp/rinkhals-bootid ]; then
    echo $RANDOM > /tmp/rinkhals-bootid
fi
BOOT_ID=$(cat /tmp/rinkhals-bootid)

log
log "[$BOOT_ID] Starting Rinkhals..."

echo
echo "          ██████████              "
echo "        ██          ██            "
echo "        ██            ██          "
echo "      ██  ██      ██  ██          "
echo "      ██  ██      ██  ░░██        "
echo "      ██              ░░██        "
echo "        ██░░░░░░░░░░░░██          "
echo "          ██████████████          "
echo "      ████    ██    ░░████        "
echo "    ██      ██      ░░██░░██      "
echo "  ██    ██░░░░░░░░░░██  ░░░░██    "
echo "  ██░░    ██████████    ░░██░░██  "
echo "  ██░░                  ░░██░░██  "
echo "    ██░░░░░░░░░░░░░░░░░░████░░██  "
echo "      ██████████████████    ██    "
echo

log " --------------------------------------------------"
log "| Kobra firmware: $KOBRA_VERSION"
log "| Rinkhals version: $RINKHALS_VERSION"
log "| Rinkhals root: $RINKHALS_ROOT"
log "| Rinkhals home: $RINKHALS_HOME"
log " --------------------------------------------------"
echo

REMOTE_MODE=$(cat /useremain/dev/remote_ctrl_mode)
if [ "$REMOTE_MODE" != "lan" ]; then
    log "/!\ LAN mode is disabled, some functions might not work properly"
    echo
fi

touch /useremain/rinkhals/.disable-rinkhals


################
log "> Stopping Anycubic apps..."

kill_by_name K3SysUi
kill_by_name gkcam
kill_by_name gkapi
kill_by_name gklib


################
log "> Fixing permissions..."

chmod +x ./*.sh 2> /dev/null
chmod +x ./lib/ld-* 2> /dev/null
chmod +x ./bin/* 2> /dev/null
chmod +x ./sbin/* 2> /dev/null
chmod +x ./usr/bin/* 2> /dev/null
chmod +x ./usr/sbin/* 2> /dev/null
chmod +x ./usr/libexec/* 2> /dev/null
chmod +x ./usr/share/scripts/* 2> /dev/null
chmod +x ./usr/libexec/gcc/arm-buildroot-linux-uclibcgnueabihf/11.4.0/* 2> /dev/null


################
log "> Preparing overlay..."

umount -l /userdata/app/gk/printer_data/gcodes 2> /dev/null
umount -l /userdata/app/gk/printer_data 2> /dev/null

umount -l /etc 2> /dev/null
umount -l /opt 2> /dev/null
umount -l /sbin 2> /dev/null
umount -l /bin 2> /dev/null
umount -l /usr 2> /dev/null
umount -l /lib 2> /dev/null

DIRECTORIES="/lib /usr /bin /sbin /opt /etc"
ORIGINAL_ROOT=/tmp/rinkhals/original
MERGED_ROOT=/tmp/rinkhals/merged

# Backup original directories
for DIRECTORY in $DIRECTORIES; do
    ORIGINAL_DIRECTORY=$ORIGINAL_ROOT$DIRECTORY

    umount -l $ORIGINAL_DIRECTORY 2> /dev/null

    mkdir -p $ORIGINAL_DIRECTORY
    rm -rf $ORIGINAL_DIRECTORY/*

    mount --bind $DIRECTORY $ORIGINAL_DIRECTORY
done

# Overlay directories
for DIRECTORY in $DIRECTORIES; do
    ORIGINAL_DIRECTORY=$ORIGINAL_ROOT$DIRECTORY
    RINKHALS_DIRECTORY=$RINKHALS_ROOT$DIRECTORY
    MERGED_DIRECTORY=$MERGED_ROOT$DIRECTORY

    mkdir -p $MERGED_DIRECTORY
    rm -rf $MERGED_DIRECTORY/*

    [ -d $ORIGINAL_DIRECTORY ] && cp -ars $ORIGINAL_DIRECTORY/* $MERGED_DIRECTORY
    [ -d $RINKHALS_DIRECTORY ] && cp -ars $RINKHALS_DIRECTORY/* $MERGED_DIRECTORY

    mount --bind $MERGED_DIRECTORY $DIRECTORY
done


################
log "> Starting SSH & ADB..."

if [ "$(cat /proc/net/tcp | grep 00000000:0016)" != "" ]; then # 22 = x16
    log "/!\ SSH is already running"
else
    dropbear -F -E -a -p 22 -P /tmp/dropbear.pid -r /usr/local/etc/dropbear/dropbear_rsa_host_key >> ./logs/dropbear.log 2>&1 &
    msleep 500

    if [ "$(cat /proc/net/tcp | grep 00000000:0016)" == "" ]; then
        log "/!\ SSH did not start properly"
        quit
    fi
fi

# if [ "$(cat /proc/net/tcp | grep 00000000:15B3)" != "" ]; then # 5555 = x15B3
#     log "/!\ ADB is already running"
# else
#     adbd >> ./logs/adbd.log &
#     msleep 500

#     if [ "$(cat /proc/net/tcp | grep 00000000:15B3)" == "" ]; then
#         log "/!\ ADB did not start properly"
#         quit
#     fi
# fi


################
log "> Preparing mounts..."

mkdir -p $RINKHALS_HOME/printer_data
mkdir -p /userdata/app/gk/printer_data
umount -l /userdata/app/gk/printer_data 2> /dev/null
mount --bind $RINKHALS_HOME/printer_data /userdata/app/gk/printer_data

mkdir -p /userdata/app/gk/printer_data/config/default
umount -l /userdata/app/gk/printer_data/config/default 2> /dev/null
mount --bind -o ro $RINKHALS_ROOT/home/rinkhals/printer_data/config /userdata/app/gk/printer_data/config/default

mkdir -p /userdata/app/gk/printer_data/gcodes
umount -l /userdata/app/gk/printer_data/gcodes 2> /dev/null
mount --bind /useremain/app/gk/gcodes /userdata/app/gk/printer_data/gcodes

[ -f /userdata/app/gk/printer_data/config/moonraker.conf ] || cp /userdata/app/gk/printer_data/config/default/moonraker.conf /userdata/app/gk/printer_data/config/
[ -f /userdata/app/gk/printer_data/config/printer.cfg ] || cp /userdata/app/gk/printer_data/config/default/printer.cfg /userdata/app/gk/printer_data/config/


################
log "> Starting Moonraker..."

kill_by_name moonraker.py
kill_by_name moonraker-proxy.py

if [ ! -f $RINKHALS_HOME/.disable-moonraker ]; then
    HOME=/userdata/app/gk python /usr/share/moonraker/moonraker/moonraker.py >> ./logs/moonraker.log 2>&1 &
    python /opt/rinkhals/proxy/moonraker-proxy.py >> ./logs/moonraker.log 2>&1 &
    wait_for_port 7125
else
    log "/!\ Moonraker was disabled by .disable-moonraker"
fi


################
log "> Starting nginx..."

kill_by_name nginx

if [ ! -f $RINKHALS_HOME/.disable-nginx ]; then
    mkdir -p /var/log/nginx
    mkdir -p /var/cache/nginx

    nginx -c /usr/local/etc/nginx/nginx.conf &
    wait_for_port 80
else
    log "/!\ nginx was disabled by .disable-nginx"
fi


################
if [ ! -f $RINKHALS_HOME/.disable-moonraker ]; then
    log "> Waiting for Moonraker to start..."
    wait_for_port 7126
fi


################
log "> Restarting Anycubic apps..."

cd /userdata/app/gk
export LD_LIBRARY_PATH=/userdata/app/gk:$LD_LIBRARY_PATH

./gklib -a /tmp/unix_uds1 /userdata/app/gk/printer_data/config/printer.cfg &> $RINKHALS_ROOT/logs/gklib.log &

sleep 1

./gkapi &> $RINKHALS_ROOT/logs/gkapi.log &
./K3SysUi &> $RINKHALS_ROOT/logs/K3SysUi.log &

cd $RINKHALS_ROOT

sleep 1

assert_by_name gklib
assert_by_name gkapi
#assert_by_name K3SysUi


################
log "> Starting mjpg-streamer..."

kill_by_name mjpg_streamer

if [ ! -f $RINKHALS_HOME/.disable-mjpgstreamer ]; then
    if [ -e /dev/video10 ]; then
        kill_by_name gkcam

        sleep 1

        mjpg_streamer -i "/usr/lib/mjpg-streamer/input_uvc.so -d /dev/video10 -n" -o "/usr/lib/mjpg-streamer/output_http.so -w /usr/share/mjpg-streamer/www"  >> ./logs/mjpg_streamer.log 2>&1 &
        wait_for_port 8080
    else
        log "Webcam /dev/video10 not found. mjpg-streamer will not start"
    fi
else
    log "/!\ mjpg-streamer was disabled by .disable-mjpgstreamer"
fi


################
log "> Starting apps..."

OLD_LD_LIBRARY_PATH=$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/lib:/usr/lib:$LD_LIBRARY_PATH

BUILTIN_APPS=$(find $RINKHALS_ROOT/home/rinkhals/apps -type d -mindepth 1 -maxdepth 1 -exec basename {} \; 2> /dev/null)
USER_APPS=$(find $RINKHALS_HOME/apps -type d -mindepth 1 -maxdepth 1 -exec basename {} \; 2> /dev/null)

APPS=$(printf "$BUILTIN_APPS\n$USER_APPS" | sort -uV)

for APP in $APPS; do
    BUITLIN_APP_ROOT=$(ls -d1 $RINKHALS_ROOT/home/rinkhals/apps/$APP 2> /dev/null)
    USER_APP_ROOT=$(ls -d1 $RINKHALS_HOME/apps/$APP 2> /dev/null)

    APP_ROOT=${USER_APP_ROOT:-${BUITLIN_APP_ROOT}}

    if [ ! -f $APP_ROOT/app.sh ] || [ ! -f $APP_ROOT/app.json ]; then
        continue
    fi

    APP_SCHEMA_VERSION=$(cat $APP_ROOT/app.json | sed 's/\/\/.*$//' | jq -r '.["$version"]')
    if [ "$APP_SCHEMA_VERSION" != "1" ]; then
        log "  - Skipping $APP ($APP_ROOT) as it is not compatible with this version of Rinkhals"
        continue
    fi

    cd $APP_ROOT
    chmod +x $APP_ROOT/app.sh

    if ([ -f $APP_ROOT/.enabled ] || [ -f $RINKHALS_HOME/apps/$APP.enabled ]) && [ ! -f $APP_ROOT/.disabled ] && [ ! -f $RINKHALS_HOME/apps/$APP.disabled ]; then
        log "  - Starting $APP ($APP_ROOT)..."
        $APP_ROOT/app.sh start
    else
        APP_STATUS=$($APP_ROOT/app.sh status | grep Status | awk '{print $1}')

        if [ "$APP_STATUS" == "$APP_STATUS_STARTED" ]; then
            log "  - Stopping $APP ($APP_ROOT) as it is not enabled..."
            $APP_ROOT/app.sh stop
        else
            log "  - Skipping $APP ($APP_ROOT) as it is not enabled"
        fi
    fi
done

cd $RINKHALS_ROOT
export LD_LIBRARY_PATH=$OLD_LD_LIBRARY_PATH


################
log "> Cleaning up..."

rm /useremain/rinkhals/.disable-rinkhals

echo
log "Rinkhals started"
