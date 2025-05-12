#!/bin/sh

function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

UPDATE_PATH="/useremain/update_swu"


# Check if the printer has Rinkhals installed
if [ ! -e /useremain/rinkhals/.current ]; then
    beep 100 && usleep 100000 && beep 100
    exit 1
fi


# Backup config
TMP_PATH="/tmp/rinkhals-config-reset"

mkdir -p $TMP_PATH
rm -rf $TMP_PATH/*

cp /useremain/home/rinkhals/printer_data/config/* $TMP_PATH 2> /dev/null
rm $TMP_PATH/*.zip 2> /dev/null

cd $TMP_PATH
DATE=$(date '+%Y%m%d-%H%M%S')
BACKUP_NAME=config-backup-${DATE}.zip
zip -r $BACKUP_NAME .

cp $BACKUP_NAME /useremain/home/rinkhals/printer_data/config/
if [ -e /mnt/udisk ]; then
    mkdir -p /mnt/udisk/aGVscF9zb3Nf
    cp $BACKUP_NAME /mnt/udisk/aGVscF9zb3Nf/
fi

# Restore default config
RINKHALS_HOME=/useremain/home/rinkhals

rm $RINKHALS_HOME/printer_data/config/*.conf 2> /dev/null
rm $RINKHALS_HOME/printer_data/config/*.cfg 2> /dev/null

rm /useremain/rinkhals/.disable-rinkhals


# Cleanup
cd
rm -rf $UPDATE_PATH
sync


# Beep to notify completion
beep 500
