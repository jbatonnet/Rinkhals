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

# Collect and dump logs
cp /useremain/rinkhals/*.log $TMP_PATH/ 2> /dev/null
cp /useremain/rinkhals/.version $TMP_PATH/.version 2> /dev/null

mkdir -p $TMP_PATH/moonraker
cp /userdata/app/gk/printer_data/logs/*.log $TMP_PATH/moonraker/ 2> /dev/null

# Collect different Rinkhals versions logs
cd /useremain/rinkhals
for VERSION in $(ls -1d */); do
    mkdir -p $TMP_PATH/$VERSION
    cp /useremain/rinkhals/$VERSION*.log $TMP_PATH/$VERSION 2> /dev/null
    cp /useremain/rinkhals/$VERSION/logs/*.log $TMP_PATH/$VERSION 2> /dev/null
done

# Collect basic printer info (firmware version, LAN mode, startup script)
cp /useremain/dev/remote_ctrl_mode $TMP_PATH/ 2> /dev/null
cp /useremain/dev/version $TMP_PATH/firmware_version 2> /dev/null
cat -A /userdata/app/gk/start.sh > $TMP_PATH/start.sh 2> /dev/null
cat -A /userdata/app/gk/restart_k3c.sh > $TMP_PATH/restart_k3c.sh 2> /dev/null

# Collect more information (free space, Rinkhals size, running processes)
df -h > $TMP_PATH/df.log 2> /dev/null
du -sh /useremain/rinkhals/* > $TMP_PATH/du.log 2> /dev/null
ls -al /useremain > $TMP_PATH/ls-useremain.log 2> /dev/null
ls -al /useremain/rinkhals > $TMP_PATH/ls-rinkhals.log 2> /dev/null
netstat -tln > $TMP_PATH/netstat.log 2> /dev/null
ps > $TMP_PATH/ps.log 2> /dev/null
top -n 1 > $TMP_PATH/top.log 2> /dev/null

# Collect webcam path and video formats
ls -al /dev/v4l/by-id/* > $TMP_PATH/ls-dev-v4l.log 2> /dev/null
v4l2-ctl --list-devices > $TMP_PATH/v4l2-ctl.log 2> /dev/null
ls -1 /dev/v4l/by-id/* | sort | head -n 1 | xargs -I {} v4l2-ctl -w -d {} --list-formats-ext > $TMP_PATH/v4l2-ctl-details.log 2> /dev/null

# Package everything
cd $TMP_PATH
zip -r debug-bundle.zip .

DATE=$(date '+%Y%m%d-%H%M%S')
ID=$(cat /useremain/dev/device_id | cksum | cut -f 1 -d ' ')

cp debug-bundle.zip /mnt/udisk/aGVscF9zb3Nf/debug-bundle_${ID}_${DATE}.zip

# Cleanup
cd
rm -rf $TMP_PATH
rm -rf $UPDATE_PATH
sync

# Beep to notify completion
beep 500
