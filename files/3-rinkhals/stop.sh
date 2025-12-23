. $(dirname $(realpath $0))/tools.sh

cd $RINKHALS_ROOT
mkdir -p $RINKHALS_LOGS

if [ ! -d /useremain/rinkhals/.current ]; then
    echo Rinkhals has not started
    exit 1
fi


################
log "> Stopping apps..."

APPS=$(list_apps)
for APP in $APPS; do
    APP_ROOT=$(get_app_root $APP)

    if [ ! -f $APP_ROOT/app.sh ]; then
        continue
    fi

    cd $APP_ROOT
    chmod +x $APP_ROOT/app.sh

    APP_STATUS=$(get_app_status $APP)
    if [ "$APP_STATUS" == "$APP_STATUS_STARTED" ]; then
        log "  - Stopping $APP ($APP_ROOT)..."
        stop_app $APP
    fi
done

cd $RINKHALS_ROOT


################
log "> Cleaning overlay..."

cd /useremain/rinkhals/.current

rm -f /userdata/app/gk/printer_mutable.cfg 2> /dev/null
[ -f /userdata/app/gk/printer_mutable.cfg.bak ] && mv /userdata/app/gk/printer_mutable.cfg.bak /userdata/app/gk/printer_mutable.cfg

umount -l /userdata/app/gk/printer_data/gcodes 2> /dev/null
umount -l /userdata/app/gk/printer_data 2> /dev/null

umount -l /etc 2> /dev/null
umount -l /opt 2> /dev/null
umount -l /sbin 2> /dev/null
umount -l /bin 2> /dev/null
umount -l /usr 2> /dev/null
umount -l /lib 2> /dev/null


################
log "> Restarting Anycubic apps..."

touch /useremain/rinkhals/.disable-rinkhals

cd /userdata/app/gk
./start.sh &> /dev/null

rm /useremain/rinkhals/.disable-rinkhals

echo
log "Rinkhals stopped"
