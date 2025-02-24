#!/bin/sh

function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

UPDATE_PATH="/useremain/update_swu"


# Check if the printer has a supported configuration
KOBRA_MODEL=$(cat /userdata/app/gk/printer.cfg | grep device_type | awk -F':' '{print $2}' | xargs)
KOBRA_VERSION=$(cat /useremain/dev/version)

if [ "$KOBRA_MODEL" == "Anycubic Kobra 2 Pro" ]; then
    export KOBRA_MODEL_CODE=K2P
    if [ "$KOBRA_VERSION" != "3.1.2.3" ]; then
        beep 100 && usleep 100000 && beep 100
        exit 1
    fi
elif [ "$KOBRA_MODEL" == "Anycubic Kobra 3" ]; then
    export KOBRA_MODEL_CODE=K3
    if [ "$KOBRA_VERSION" != "2.3.5.3" ]; then
        beep 100 && usleep 100000 && beep 100
        exit 1
    fi
else
    beep 100 && usleep 100000 && beep 100
    exit 1
fi


# Restore default config
RINKHALS_HOME=/useremain/home/rinkhals

if [ -e $RINKHALS_HOME/printer_data/config/printer.cfg ]; then
    rm $RINKHALS_HOME/printer_data/config/printer.cfg.bak
    cp $RINKHALS_HOME/printer_data/config/printer.cfg $RINKHALS_HOME/printer_data/config/printer.cfg.bak
    rm $RINKHALS_HOME/printer_data/config/printer.cfg
fi

rm /useremain/rinkhals/.disable-rinkhals


# Cleanup
cd
rm -rf $UPDATE_PATH
sync

# Beep to notify completion
beep 500
