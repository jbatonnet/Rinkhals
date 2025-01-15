function log() {
    echo "${*}"

    mkdir -p /useremain/rinkhals/.current/logs
    echo "$(date): ${*}" >> /useremain/rinkhals/.current/logs/rinkhals.log
}
function kill_by_name() {
    PIDS=$(ps | grep "$1" | grep -v grep | awk '{print $1}')

    for PID in $(echo "$PIDS"); do
        CMDLINE=$(cat /proc/$PID/cmdline) 2>/dev/null

        log "Killing $PID ($CMDLINE)"
        kill -9 $PID
    done
}


RINKHALS_ROOT=$(dirname $0)

cd $RINKHALS_ROOT
mkdir -p ./logs


if [ ! -d /useremain/rinkhals/.current ]; then
    echo Rinkhals has not started
    exit 1
fi


################
log "> Stopping apps..."

BUILTIN_APPS=$(find $RINKHALS_ROOT/home/rinkhals/apps -type d -mindepth 1 -maxdepth 1 -exec basename {} \; 2> /dev/null)
USER_APPS=$(find $RINKHALS_HOME/apps -type d -mindepth 1 -maxdepth 1 -exec basename {} \; 2> /dev/null)

APPS=$(printf "$BUILTIN_APPS\n$USER_APPS" | sort -uV)

for APP in $APPS; do
    BUITLIN_APP_ROOT=$(ls -d1 $RINKHALS_ROOT/home/rinkhals/apps/$APP 2> /dev/null)
    USER_APP_ROOT=$(ls -d1 $RINKHALS_HOME/apps/$APP 2> /dev/null)

    APP_ROOT=${USER_APP_ROOT:-${BUITLIN_APP_ROOT}}

    if [ ! -f $APP_ROOT/app.sh ]; then
        continue
    fi

    cd $APP_ROOT
    chmod +x $APP_ROOT/app.sh

    APP_STATUS=$($APP_ROOT/app.sh status | grep Status | awk '{print $1}')
    if [ "$APP_STATUS" == "$APP_STATUS_STARTED" ]; then
        log "  - Stopping $APP ($APP_ROOT)..."
        $APP_ROOT/app.sh stop
    fi
done

cd $RINKHALS_ROOT


################
log "> Stopping Rinkhals..."

kill_by_name moonraker.py
kill_by_name moonraker-proxy.py
kill_by_name nginx
kill_by_name mjpg_streamer


################
log "> Cleaning overlay..."

cd /useremain/rinkhals/.current

umount -l /userdata/app/gk/printer_data/gcodes 2> /dev/null
umount -l /userdata/app/gk/printer_data 2> /dev/null

umount -l /opt 2> /dev/null
umount -l /bin 2> /dev/null
umount -l /lib 2> /dev/null
umount -l /sbin 2> /dev/null
umount -l /usr 2> /dev/null
umount -l /etc/ssl 2> /dev/null
umount -l /etc/profile.d 2> /dev/null


################
log "> Restarting Anycubic apps..."

touch /useremain/rinkhals/.disable-rinkhals

cd /userdata/app/gk
./restart_k3c.sh &> /dev/null

rm /useremain/rinkhals/.disable-rinkhals

echo
log "Rinkhals stopped"
