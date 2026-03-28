#!/bin/sh

function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

UPDATE_PATH="/useremain/update_swu"

RINKHALS_PATH="/useremain/rinkhals"
RINKHALS_CURRENT=$(realpath /useremain/rinkhals/.current)

# Find all directories in RINKHALS_PATH except symlinks
installs=$(find "$RINKHALS_PATH" -mindepth 1 -maxdepth 1 -type d ! -type l)

for i in $installs; do
    basename=$(basename "$i")
    
    # Never delete the currently active installation, or the standard dev workspace
    if [ "$i" = "$RINKHALS_CURRENT" ] || [ "$basename" = "dev" ] || [ "$basename" = "user_data" ]; then
        continue
    fi
    
    # Actually delete any other folder found in the Rinkhals root
    rm -rf "$i"
done

# Cleanup temporary update payloads

cd
rm -rf $TMP_PATH
rm -rf $UPDATE_PATH
sync

# Beep to notify completion
beep 500
