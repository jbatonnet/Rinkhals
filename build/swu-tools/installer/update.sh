#!/bin/sh -x

UPDATE_PATH="/useremain/update_swu"
TMP_TOOL_PATH="/tmp/rin"

if [ -f /useremain/rinkhals/.reboot-marker ]; then
    rm /useremain/rinkhals/.reboot-marker
    exit 0
fi

if [ "$1" == "ssh" ]; then
    # Kill anything on port 2222
    INODE=$(cat /proc/net/tcp | grep 00000000:08AE | awk '/.*:.*:.*/{print $10;}')
    if [[ "$INODE" != "" ]]; then
        PID=$(ls -l /proc/*/fd/* 2> /dev/null | grep "socket:\[$INODE\]" | awk -F'/' '{print $3}')
        kill -9 $PID
        sleep 1
    fi

    # Run the SSH server
    LD_LIBRARY_PATH=$TMP_TOOL_PATH $TMP_TOOL_PATH/dropbear -F -E -a -p 2222 -P $TMP_TOOL_PATH/dropbear.pid -r $TMP_TOOL_PATH/dropbear_rsa_host_key 1>&2 &
    exit 0
fi

if [ "$1" != "async" ]; then
    echo "Re-running async..."
    nohup $0 async > /dev/null &
    exit 0
fi


# Kill Python UI processes
PIDS=$(lsof | grep python | grep fb0 | awk '{print $1}')
for PID in $(echo "$PIDS"); do
    kill -9 $PID
done

# Create a temp directory
mkdir -p $TMP_TOOL_PATH
rm -rf $TMP_TOOL_PATH/*
cd $TMP_TOOL_PATH

# Copy the files
cp -r $UPDATE_PATH/* $TMP_TOOL_PATH/

# Fix permissions
chmod +x $TMP_TOOL_PATH/ld-uClibc
chmod +x $TMP_TOOL_PATH/python
chmod +x $TMP_TOOL_PATH/dropbear
chmod +x $TMP_TOOL_PATH/sftp-server
chmod +x $TMP_TOOL_PATH/tools/*.sh

# Start SSH async
nohup $0 ssh > /dev/null &

# Run the installer UI
/ac_lib/lib/third_bin/ffmpeg -f fbdev -i /dev/fb0 -frames:v 1 -y /tmp/rinkhals-installer-backup.bmp 1>/dev/null 2>/dev/null &
LD_LIBRARY_PATH=$TMP_TOOL_PATH:$LD_LIBRARY_PATH PYTHONPATH= $TMP_TOOL_PATH/python $TMP_TOOL_PATH/rinkhals-install.py >> $TMP_TOOL_PATH/rinkhals-install.log 2>&1
/ac_lib/lib/third_bin/ffmpeg -i /tmp/rinkhals-installer-backup.bmp -f fbdev /dev/fb0 1>/dev/null 2>/dev/null
