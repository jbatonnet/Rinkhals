#!/bin/sh

function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

USB_DRIVE="/mnt/udisk"
if [ ! -e $USB_DRIVE ]; then
    exit 0
fi

# Backup userdata and useremain partitions on USB drive
cd /userdata
rm $USB_DRIVE/userdata.tar 2> /dev/null
tar -cvf $USB_DRIVE/userdata.tar \
    --exclude='./app/gk/printer_data/gcodes' \
    --exclude='*.1' \
    .

cd /useremain
rm $USB_DRIVE/useremain.tar 2> /dev/null
tar -cvf $USB_DRIVE/useremain.tar \
    --exclude='./rinkhals' \
    --exclude='./app/gk/gcodes' \
    --exclude='./update_swu' \
    --exclude='./dist' \
    --exclude='./tmp' \
    --exclude='./lost+found' \
    --exclude='./.cache' \
    .

# Cleanup
rm -rf /useremain/update_swu
sync

# Beep to notify completion
beep 500
