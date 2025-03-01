#!/bin/sh

UPDATE_PATH="/useremain/update_swu"
USB_UPDATE_PATH="/mnt/udisk/aGVscF9zb3Nf"


. $UPDATE_PATH/rinkhals/tools.sh


log() {
    echo "${*}"
    echo "$(date): ${*}" >> /useremain/rinkhals/install.log
    echo "$(date): ${*}" >> /mnt/udisk/aGVscF9zb3Nf/install.log
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


# Make sure we install on the right compatible version
check_compatibility


# Unmount everything to prevent any issues
progress 0.1

umount -l /etc 2> /dev/null
umount -l /opt 2> /dev/null
umount -l /sbin 2> /dev/null
umount -l /bin 2> /dev/null
umount -l /usr 2> /dev/null
umount -l /lib 2> /dev/null


# Backup the machine-specific files
progress 0.2

log "Backing up machine-specific files"
rm -f /mnt/udisk/aGVscF9zb3Nf/device.ini
rm -f /mnt/udisk/aGVscF9zb3Nf/device_account.json
cp /userdata/app/gk/config/device.ini /mnt/udisk/aGVscF9zb3Nf/device.ini
cp /userdata/app/gk/config/device_account.json /mnt/udisk/aGVscF9zb3Nf/device_account.json


# TODO: Check if we have enough space


# Copy Rinkhals
progress 0.3

RINKHALS_VERSION=$(cat $UPDATE_PATH/.version)

log "Installing Rinkhals version $RINKHALS_VERSION"

log "Copying Rinkhals files"
mkdir -p /useremain/rinkhals/$RINKHALS_VERSION
rm -rf /useremain/rinkhals/$RINKHALS_VERSION/*
cp -r $UPDATE_PATH/rinkhals/* /useremain/rinkhals/$RINKHALS_VERSION

echo $RINKHALS_VERSION > /useremain/rinkhals/$RINKHALS_VERSION/.version

progress 0.8

log "Copying Rinkhals startup files"
rm -f /useremain/rinkhals/*.*
cp $UPDATE_PATH/start-rinkhals.sh /useremain/rinkhals/start-rinkhals.sh

cp $UPDATE_PATH/start.sh.patch /useremain/rinkhals/start.sh.patch

echo $RINKHALS_VERSION > /useremain/rinkhals/.version

rm /useremain/rinkhals/.disable-rinkhals


# Install Rinkhals loader
progress 0.9

PRESENT=$(cat /userdata/app/gk/start.sh | grep "Rinkhals/begin")
if [ "$PRESENT" == "" ]; then
    log "Installing Rinkhals loader as it is missing"

    cat $UPDATE_PATH/start.sh.patch >> /userdata/app/gk/start.sh
    if [ -f /userdata/app/gk/restart_k3c.sh ]; then
        cat $UPDATE_PATH/start.sh.patch >> /userdata/app/gk/restart_k3c.sh
    fi
else
    log "Rinkhals loader was detected, skipping installation"
fi

log "Removing update files"

rm -rf $UPDATE_PATH
rm -f /useremain/update.swu
rm -f $USB_UPDATE_PATH/update.swu

sync
log "Rinkhals installation complete, rebooting..."


# Notify user
progress success

beep 1000
msleep 1000
beep 1000

reboot
