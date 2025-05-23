#!/bin/sh

function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

# Backup config
TMP_PATH="/tmp/rinkhals-config-reset"

mkdir -p $TMP_PATH
rm -rf $TMP_PATH/*

cp /useremain/home/rinkhals/printer_data/config/* $TMP_PATH 2> /dev/null
rm $TMP_PATH/*.zip 2> /dev/null

cd $TMP_PATH
DATE=$(date '+%Y%m%d-%H%M%S')
zip -r /useremain/config-backup-${DATE}.zip .

if [ -e /mnt/udisk ]; then
    cp /useremain/config-backup-${DATE}.zip /mnt/udisk/config-backup-${DATE}.zip
fi

# Stop Rinkhals if needed
if [ -e /useremain/rinkhals/.current/stop.sh ]; then
    chmod +x /useremain/rinkhals/.current/stop.sh
    /useremain/rinkhals/.current/stop.sh
fi

# Delete Rinkhals completely
rm -rf /useremain/rinkhals 2> /dev/null
rm -rf /useremain/home/rinkhals 2> /dev/null
rm -rf /userdata/app/gk/K3SysUi.patch 2> /dev/null

sed -i '/# Rinkhals\/begin/,/# Rinkhals\/end/d' /userdata/app/gk/start.sh
if [ -f /userdata/app/gk/restart_k3c.sh ]; then
    sed -i '/# Rinkhals\/begin/,/# Rinkhals\/end/d' /userdata/app/gk/restart_k3c.sh
fi

# Beep to notify completion
beep 500

sync 2> /dev/null
reboot
