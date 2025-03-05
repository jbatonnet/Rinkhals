#!/bin/sh

function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

UPDATE_PATH="/useremain/update_swu"
TMP_PATH="/tmp/rinkhals-debug"

mkdir -p $TMP_PATH
rm -rf $TMP_PATH/*

# TODO
# - Bind mount /bin to hide tar
# - Watch for /useremain/update.swu file
# - Copy /useremain/update.swu to /useremain/update.swu.bak
# - Watch and kill unzip process (+ gkapi)
# - Copy /useremain/update.swu.bak to USB

# Cleanup
cd
rm -rf $TMP_PATH
rm -rf $UPDATE_PATH
sync

# Beep to notify completion
beep 500
