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


# Restore default config
RINKHALS_HOME=/useremain/home/rinkhals
CONFIG_FILE=$RINKHALS_HOME/printer_data/config/printer.custom.cfg

if [ -f $CONFIG_FILE ]; then
    rm $CONFIG_FILE.bak
    cp $CONFIG_FILE $CONFIG_FILE.bak
    rm $CONFIG_FILE
fi

rm /useremain/rinkhals/.disable-rinkhals


# Cleanup
cd
rm -rf $UPDATE_PATH
sync

# Beep to notify completion
beep 500
