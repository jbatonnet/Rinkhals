msleep() {
    usleep $(($1 * 1000))
}
beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $((${*}*1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}
log() {
    echo "${*}"

    mkdir -p $RINKHALS_ROOT/logs
    echo "`date`: ${*}" >> $RINKHALS_ROOT/logs/rinkhals.log
}
kill_by_name() {
    PIDS=`ps | grep "$1" | grep -v grep | awk '{print $1}'`

    for PID in `echo "$PIDS"`; do
        CMDLINE=`cat /proc/$PID/cmdline` 2>/dev/null

        log "Killing $PID ($CMDLINE)"
        kill -9 $PID
    done
}
assert_by_name() {
    PIDS=`ps | grep "$1" | grep -v grep | awk '{print $1}'`

    if [ "$PIDS" == "" ]; then
        log "/!\ ${*} should be running but it's not"
        quit
    fi
}
wait_for_port() {
    DELAY=250
    TOTAL=0

    while [ 1 ]; do
        OPEN=`netstat -tln | grep :$1`
        if [ "$OPEN" != "" ]; then
            break
        fi

        if [ "$TOTAL" -gt "60000" ]; then
            log "/!\ Timeout waiting for port $1 to open"
            quit
        fi

        msleep $DELAY

        TOTAL=$(( $TOTAL + $DELAY ))
        DELAY=$(( $DELAY * 2 ))
    done
}
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

KOBRA_VERSION=`cat /useremain/dev/version`
RINKHALS_ROOT=`dirname $(realpath $0)`
RINKHALS_VERSION=`cat $RINKHALS_ROOT/.version`
RINKHALS_HOME=/useremain/home/rinkhals

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
BOOT_ID=`cat /tmp/rinkhals-bootid`

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

REMOTE_MODE=`cat /useremain/dev/remote_ctrl_mode`
if [ "$REMOTE_MODE" != "lan" ]; then
    log "LAN mode is disabled, some functions might not work properly"
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

umount -l /sbin 2> /dev/null
umount -l /bin 2> /dev/null
umount -l /usr 2> /dev/null
umount -l /lib 2> /dev/null

mount -o ro --bind ./lib /lib
mount --bind ./usr /usr
mount -o ro --bind ./bin /bin
mount -o ro --bind ./sbin /sbin


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
    python /usr/share/scripts/moonraker-proxy.py >> ./logs/moonraker.log 2>&1 &
    wait_for_port 7125
else
    log "/!\ Moonraker was disabled by .disable-moonraker"
fi


################
# log "> Starting OctoApp companion..."

# if [ ! -f $RINKHALS_HOME/.disable-octoapp ]; then
#     # python -m /usr/share/octoapp/moonraker_octoapp "ewogICAgJ0tsaXBwZXJDb25maWdGb2xkZXInOiAnL3VzZXJlbWFpbi9yaW5raGFscy9xdWljay1kZXBsb3kvaG9tZS9yaW5raGFscy9wcmludGVyX2RhdGEvY29uZmlnJywKICAgICdNb29ucmFrZXJDb25maWdGaWxlJzogJy91c2VyZW1haW4vcmlua2hhbHMvcXVpY2stZGVwbG95L2hvbWUvcmlua2hhbHMvcHJpbnRlcl9kYXRhL2NvbmZpZy9tb29ucmFrZXIuY29uZicsCiAgICAnS2xpcHBlckxvZ0ZvbGRlcic6ICcvdXNlcmVtYWluL3JpbmtoYWxzL3F1aWNrLWRlcGxveS9ob21lL3JpbmtoYWxzL3ByaW50ZXJfZGF0YS9sb2dzJywKICAgICdMb2NhbEZpbGVTdG9yYWdlUGF0aCc6ICcvdXNlcmVtYWluL3JpbmtoYWxzL3F1aWNrLWRlcGxveS9ob21lL3JpbmtoYWxzL29jdG9hcHAnLAogICAgJ0lzT2JzZXJ2ZXInIDogZmFsc2UKfQ=="

#     # {
#     #     'KlipperConfigFolder': '/useremain/rinkhals/quick-deploy/home/rinkhals/printer_data/config',
#     #     'MoonrakerConfigFile': '/useremain/rinkhals/quick-deploy/home/rinkhals/printer_data/config/moonraker.conf',
#     #     'KlipperLogFolder': '/useremain/rinkhals/quick-deploy/home/rinkhals/printer_data/logs',
#     #     'LocalFileStoragePath': '/useremain/rinkhals/quick-deploy/home/rinkhals/octoapp',
#     #     'IsObserver' : false
#     # }
# else
#     log "/!\ OctoApp companion was disabled by .disable-octoapp"
# fi


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
log "> Restarting Anycubic apps..."

cd /userdata/app/gk
export LD_LIBRARY_PATH=/userdata/app/gk:$LD_LIBRARY_PATH

./gklib -a /tmp/unix_uds1 printer_data/config/printer.cfg &> $RINKHALS_ROOT/logs/gklib.log &

sleep 1

./gkapi &> $RINKHALS_ROOT/logs/gkapi.log &
./K3SysUi &> $RINKHALS_ROOT/logs/gkui.log &

cd $RINKHALS_ROOT

sleep 1

assert_by_name gklib
assert_by_name gkapi
#assert_by_name K3SysUi


################
log "> Cleaning up..."

rm /useremain/rinkhals/.disable-rinkhals

echo
log "Rinkhals started"
