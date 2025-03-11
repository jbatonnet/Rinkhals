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

if [ -e $RINKHALS_HOME/printer_data/config/printer.cfg ]; then
    rm $RINKHALS_HOME/printer_data/config/printer.custom.cfg.bak
    cp $RINKHALS_HOME/printer_data/config/printer.custom.cfg $RINKHALS_HOME/printer_data/config/printer.custom.cfg.bak
    rm $RINKHALS_HOME/printer_data/config/printer.custom.cfg
fi

rm /useremain/rinkhals/.disable-rinkhals


# Cleanup
cd
rm -rf $UPDATE_PATH
sync

# Beep to notify completion
beep 500
