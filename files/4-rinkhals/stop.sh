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
