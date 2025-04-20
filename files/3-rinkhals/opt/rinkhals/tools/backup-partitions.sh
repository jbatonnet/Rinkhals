#!/bin/sh

function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

UPDATE_PATH="/useremain/update_swu"
USB_DRIVE="/mnt/udisk"

# Backup userdata and useremain partitions on USB drive
cd /userdata
tar -czvf $USB_DRIVE/userdata.tgz .

cd /useremain
tar -czvf $USB_DRIVE/useremain.tgz .

# Cleanup
rm -rf $UPDATE_PATH
sync

# Beep to notify completion
beep 500
