#!/bin/sh
# update_optional.sh
update_file_path="/useremain/update_swu"
to_update_path="/userdata/app/gk"
to_update_wifi_cfg="/userdata/wifi_cfg"
to_run_sh_path="/userdata/app/kenv"
to_gcode_path="/useremain"
swu_path="/mnt/udisk/aGVscF9zb3Nf"
cfg_name="mode_cfg"
is_udisk="yes"

mode=1

echo "mode: ${mode}"

if [ -f ${swu_path}/update.swu ];then
    is_udisk="yes"
fi

function log() {
    echo "${*}"
    echo "$(date): ${*}" >> /useremain/rinkhals/install.log
    echo "$(date): ${*}" >> /mnt/udisk/aGVscF9zb3Nf/install.log
}
function progress() {
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
function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    sleep ${*}
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

function fb_capture() {
    /ac_lib/lib/third_bin/ffmpeg -f fbdev -i /dev/fb0 -frames:v 1 -y /tmp/framebuffer.bmp 1>/dev/null 2>/dev/null
}
function fb_restore() {
    /ac_lib/lib/third_bin/ffmpeg -i /tmp/framebuffer.bmp -f fbdev /dev/fb0 1>/dev/null 2>/dev/null
}
function fb_draw() {
    /ac_lib/lib/third_bin/ffmpeg -i /tmp/framebuffer.bmp -vf "${*}" -f fbdev /dev/fb0 1>/dev/null 2>/dev/null
}


log
log "Starting Rinkhals installation..."


# Capture initial framebuffer
fb_capture
progress 0


# Make sure we install on the right compatible version
KOBRA_VERSION=$(cat /useremain/dev/version)

if [[ "$KOBRA_VERSION" != "2.3.5.3" ]]; then
    log "This Rinkhals version is only compatible with Kobra firmware 2.3.5.3, stopping installation"
    
    progress error
    beep 1
    sleep 1
    beep 1
    sleep 1
    beep 1

    fb_restore
    exit 1
fi


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

RINKHALS_VERSION=$(cat ${update_file_path}/.version)
log "Installing Rinkhals version $RINKHALS_VERSION"

log "Copying Rinkhals files"
mkdir -p /useremain/rinkhals/${RINKHALS_VERSION}
rm -rf /useremain/rinkhals/${RINKHALS_VERSION}/*
cp -r ${update_file_path}/rinkhals/* /useremain/rinkhals/${RINKHALS_VERSION}
echo ${RINKHALS_VERSION} > /useremain/rinkhals/${RINKHALS_VERSION}/.version

progress 0.8

log "Copying Rinkhals startup files"
rm -f /useremain/rinkhals/*.*
cp ${update_file_path}/start-rinkhals.sh /useremain/rinkhals/start-rinkhals.sh
cp ${update_file_path}/start.sh.patch /useremain/rinkhals/start.sh.patch
echo ${RINKHALS_VERSION} > /useremain/rinkhals/.version

rm /useremain/rinkhals/.disable-rinkhals


# Install Rinkhals loader
progress 0.9

PRESENT=$(cat /userdata/app/gk/start.sh | grep "Rinkhals/begin")
if [ "$PRESENT" == "" ]; then
    log "Installing Rinkhals loader as it is missing"

    cat ${update_file_path}/start.sh.patch >> /userdata/app/gk/start.sh
    cat ${update_file_path}/start.sh.patch >> /userdata/app/gk/restart_k3c.sh
else
    log "Rinkhals loader was detected, skipping installation"
fi

log "Removing update files"
rm -rf ${update_file_path}
rm -rf ${to_gcode_path}/update.swu
rm -rf ${swu_path}/update.swu

sync
log "Rinkhals installation complete, rebooting..."


# Notify user
progress success

beep 1
sleep 1
beep 1

reboot
