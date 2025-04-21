#!/bin/sh

if [ "$1" != "async" ]; then
    echo "Re-running async..."
    nohup $0 async > /dev/null &
    exit 0
fi


SOURCE_PATH="/useremain/update_swu"
USB_PATH="/mnt/udisk/aGVscF9zb3Nf"


. $SOURCE_PATH/rinkhals/tools.sh


log() {
    echo "${*}"
    echo "$(date): ${*}" >> /useremain/rinkhals/install.log
    if [ -e $USB_PATH ]; then
        echo "$(date): ${*}" >> $USB_PATH/install.log
    fi
}
progress() {
    if [ "$1" == "success" ]; then
        fb_draw "drawbox=x=16:y=16:w=32:h=ih-32:t=fill:color=black,drawbox=x=20:y=20:w=24:h=ih-40:t=fill:color=green"
        return
    fi
    if [ "$1" == "error" ]; then
        fb_draw "drawbox=x=16:y=16:w=32:h=ih-32:t=fill:color=black,drawbox=x=20:y=20:w=24:h=ih-40:t=fill:color=red"
        return
    fi
    if [ $1 == 0 ]; then
        fb_draw "drawbox=x=16:y=16:w=32:h=ih-32:t=fill:color=black"
        return
    fi

    fb_draw "drawbox=x=16:y=16:w=32:h=ih-32:t=fill:color=black,drawbox=x=20:y=20:w=24:h=(ih-40)*${*}:t=fill:color=white"
}
quit() {
    sync
    progress error

    beep 1000
    msleep 1000
    beep 1000
    msleep 1000
    beep 1000

    fb_restore
    exit 1
}

fb_capture() {
    if [ -f /ac_lib/lib/third_bin/ffmpeg ]; then
        /ac_lib/lib/third_bin/ffmpeg -f fbdev -i /dev/fb0 -frames:v 1 -y /tmp/framebuffer.bmp 1>/dev/null 2>/dev/null
    fi
}
fb_restore() {
    if [ -f /ac_lib/lib/third_bin/ffmpeg ]; then
        /ac_lib/lib/third_bin/ffmpeg -i /tmp/framebuffer.bmp -f fbdev /dev/fb0 1>/dev/null 2>/dev/null
    fi
}
fb_draw() {
    if [ -f /ac_lib/lib/third_bin/ffmpeg ]; then
        /ac_lib/lib/third_bin/ffmpeg -i /tmp/framebuffer.bmp -vf "${*}" -f fbdev /dev/fb0 1>/dev/null 2>/dev/null
    fi
}


log
log "Starting Rinkhals installation..."


# Capture initial framebuffer
fb_capture
progress 0


# Make sure we install on a compatible model
check_compatibility


# Check if we have enough space
FREE_SPACE=$(df -k /useremain | tail -1 | awk '{print $3}')
if [ "$FREE_SPACE" != "" ] && [ "$FREE_SPACE" -lt "500000" ]; then
    log "Not enough free space in /useremain"
    quit
fi


# Backup the machine-specific files
progress 0.1

log "Backing up machine-specific files..."

INSTALL_BACKUP_PATH=/tmp/rinkhals/install-backup
mkdir -p $INSTALL_BACKUP_PATH
rm -rf $INSTALL_BACKUP_PATH/*

mkdir -p $INSTALL_BACKUP_PATH/userdata/app/gk/config
cp /userdata/app/gk/config/device.ini $INSTALL_BACKUP_PATH/userdata/app/gk/config/device.ini
cp /userdata/app/gk/config/device_account.json $INSTALL_BACKUP_PATH/userdata/app/gk/config/device_account.json

mkdir -p $INSTALL_BACKUP_PATH/useremain/app/gk
cp -r /useremain/app/gk/cert1 $INSTALL_BACKUP_PATH/useremain/app/gk/
cp -r /useremain/app/gk/cert3 $INSTALL_BACKUP_PATH/useremain/app/gk/

PREVIOUS_WD=$(pwd)
cd $INSTALL_BACKUP_PATH
zip -r kobra-personnal-backup.zip . > /dev/null
cp -f kobra-personnal-backup.zip /useremain/kobra-personnal-backup.zip
if [ -e $USB_PATH ]; then
    cp -f kobra-personnal-backup.zip $USB_PATH/kobra-personnal-backup.zip
fi
cd $PREVIOUS_WD


# Find the right directory target
progress 0.2

RINKHALS_VERSION=$(cat $SOURCE_PATH/.version)

TARGET_PATH=/useremain/rinkhals/$RINKHALS_VERSION
CURRENT_RINKHALS_PATH=$(readlink -f /useremain/rinkhals/.current 2> /dev/null)

if [ "$CURRENT_RINKHALS_PATH" != "" ] && [ "$TARGET_PATH" = "$CURRENT_RINKHALS_PATH" ]; then
    TARGET_PATH="${TARGET_PATH}-2"
fi

log "Installing Rinkhals version $RINKHALS_VERSION to $TARGET_PATH"


# Copy Rinkhals
progress 0.3

log "Copying Rinkhals files"

mkdir -p $TARGET_PATH
rm -rf $TARGET_PATH/*
cp -r $SOURCE_PATH/rinkhals/* $TARGET_PATH

echo $RINKHALS_VERSION > $TARGET_PATH/.version

progress 0.8

log "Copying Rinkhals startup files"

cp -f $SOURCE_PATH/start-rinkhals.sh /useremain/rinkhals/start-rinkhals.sh
cp -f $SOURCE_PATH/start.sh.patch /useremain/rinkhals/start.sh.patch
echo $(basename $TARGET_PATH) > /useremain/rinkhals/.version

rm /useremain/rinkhals/.disable-rinkhals 2> /dev/null


# Install Rinkhals loader
progress 0.9

PRESENT=$(cat /userdata/app/gk/start.sh | grep "Rinkhals/begin")
if [ "$PRESENT" == "" ]; then
    log "Installing Rinkhals loader as it is missing"

    cat $SOURCE_PATH/start.sh.patch >> /userdata/app/gk/start.sh
    if [ -f /userdata/app/gk/restart_k3c.sh ]; then
        cat $SOURCE_PATH/start.sh.patch >> /userdata/app/gk/restart_k3c.sh
    fi
else
    log "Rinkhals loader was detected, skipping installation"
fi

log "Removing update files"

rm -rf $SOURCE_PATH
rm -f /useremain/update.swu
rm -f $USB_PATH/update.swu

sync
log "Rinkhals installation complete, rebooting..."


# Notify user
progress success

beep 1000
msleep 1000
beep 1000

reboot
