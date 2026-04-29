#!/bin/sh

function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

# Tasks
# - Download current firmware
# - Stop Rinkhals if needed
# - In /useremain, delete everything except app/ and dev/
# - Delete /userdata/app/gk/config/ams_config.cfg
# - Delete /userdata/app/gk/config/para.cfg
# - Delete /userdata/app/gk/printer_mutabl*.cfg
# - Set /useremain/dev/remote_ctrl_mode to cloud
# - Create /useremain/dev/version from /userdata/app/gk/version_log.txt
# - Reinstall current firmware

# Beep to notify completion
beep 500
