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
cp /useremain/home/rinkhals/printer_data/logs/*.log $TMP_PATH/moonraker/ 2> /dev/null

# Collect different Rinkhals versions logs
cd /useremain/rinkhals
for VERSION in $(ls -1d */); do
    mkdir -p $TMP_PATH/$VERSION
    cp /useremain/rinkhals/$VERSION/*.log $TMP_PATH/$VERSION 2> /dev/null
    cp /useremain/rinkhals/$VERSION/logs/*.log $TMP_PATH/$VERSION 2> /dev/null
done

mkdir -p $TMP_PATH/current
cp /tmp/rinkhals/*.log $TMP_PATH/current 2> /dev/null

# Collect other logs
mkdir -p $TMP_PATH/other
cp /tmp/*.log $TMP_PATH/other 2> /dev/null

# Collect general info
cat /proc/cpuinfo > $TMP_PATH/cpuinfo.log 2> /dev/null
cat /proc/meminfo > $TMP_PATH/meminfo.log 2> /dev/null
ifconfig > $TMP_PATH/ifconfig.log 2> /dev/null
uname -a > $TMP_PATH/uname.log 2> /dev/null
df -h > $TMP_PATH/df.log 2> /dev/null
netstat -tln > $TMP_PATH/netstat.log 2> /dev/null
ps > $TMP_PATH/ps.log 2> /dev/null
top -n 1 > $TMP_PATH/top.log 2> /dev/null
dmesg > $TMP_PATH/dmesg.log 2> /dev/null
iostat > $TMP_PATH/iostat.log 2> /dev/null

# Collect partition structure
find /userdata > $TMP_PATH/find-userdata.log 2> /dev/null
find /useremain > $TMP_PATH/find-useremain.log 2> /dev/null
find /oem > $TMP_PATH/find-oem.log 2> /dev/null
find /ac_lib > $TMP_PATH/find-aclib.log 2> /dev/null
find /bin > $TMP_PATH/find-bin.log 2> /dev/null
find /usr > $TMP_PATH/find-usr.log 2> /dev/null
find /lib > $TMP_PATH/find-lib.log 2> /dev/null

# Collect printer info (firmware version, LAN mode, startup script)
cp /useremain/dev/remote_ctrl_mode $TMP_PATH/ 2> /dev/null
cp /useremain/dev/version $TMP_PATH/firmware_version 2> /dev/null
cat -A /userdata/app/gk/start.sh > $TMP_PATH/start.sh 2> /dev/null
cat -A /userdata/app/gk/restart_k3c.sh > $TMP_PATH/restart_k3c.sh 2> /dev/null
cat /userdata/app/gk/printer.cfg > $TMP_PATH/original-printer.cfg 2> /dev/null

# Collect Rinkhals info
du -sh /useremain/rinkhals/* > $TMP_PATH/du.log 2> /dev/null
ls -al /useremain > $TMP_PATH/ls-useremain.log 2> /dev/null
ls -al /useremain/rinkhals > $TMP_PATH/ls-rinkhals.log 2> /dev/null

mkdir -p $TMP_PATH/config
cp /useremain/home/rinkhals/printer_data/config/* $TMP_PATH/config/ 2> /dev/null
cp /useremain/home/rinkhals/apps/*.config $TMP_PATH/config/ 2> /dev/null

# Collect webcam path and video formats
ls -al /dev/v4l/by-id/* > $TMP_PATH/ls-dev-v4l.log 2> /dev/null
v4l2-ctl --list-devices > $TMP_PATH/v4l2-ctl.log 2> /dev/null
ls -1 /dev/v4l/by-id/* | sort | head -n 1 | xargs -I {} v4l2-ctl -w -d {} --list-formats-ext > $TMP_PATH/v4l2-ctl-details.log 2> /dev/null

# Package everything
cd $TMP_PATH
zip -r debug-bundle.zip .

DATE=$(date '+%Y%m%d-%H%M%S')
ID=$(cat /useremain/dev/device_id | cksum | cut -f 1 -d ' ')

if [ -e /mnt/udisk ]; then
    mkdir -p /mnt/udisk/aGVscF9zb3Nf
    cp debug-bundle.zip /mnt/udisk/aGVscF9zb3Nf/debug-bundle_${ID}_${DATE}.zip
fi

# Cleanup
cd
rm -rf $TMP_PATH
rm -rf $UPDATE_PATH
sync

# Beep to notify completion
beep 500
