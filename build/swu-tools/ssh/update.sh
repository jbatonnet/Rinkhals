#!/bin/sh

function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

UPDATE_PATH="/useremain/update_swu"
TMP_TOOL_PATH="/tmp/ssh"

# Create a temp directory
mkdir -p $TMP_TOOL_PATH
rm -rf $TMP_TOOL_PATH/*

# Copy the files
cp -r $UPDATE_PATH/* $TMP_TOOL_PATH/
rm -rf $UPDATE_PATH

# Fix permissions
chmod +x $TMP_TOOL_PATH/ld-uClibc
chmod +x $TMP_TOOL_PATH/dropbear
chmod +x $TMP_TOOL_PATH/sftp-server

# Kill anything on port 2222
INODE=$(cat /proc/net/tcp | grep 00000000:08AE | awk '/.*:.*:.*/{print $10;}')
if [[ "$INODE" != "" ]]; then
    PID=$(ls -l /proc/*/fd/* 2> /dev/null | grep "socket:\[$INODE\]" | awk -F'/' '{print $3}')
    kill -9 $PID
    sleep 1
fi

# Run the SSH server
LD_LIBRARY_PATH=$TMP_TOOL_PATH $TMP_TOOL_PATH/dropbear -F -E -a -p 2222 -P $TMP_TOOL_PATH/dropbear.pid -r $TMP_TOOL_PATH/dropbear_rsa_host_key \
    >> $TMP_TOOL_PATH/dropbear.log 1>&2 &

# Beep to notify completion
beep 500
