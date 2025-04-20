#!/bin/sh

function beep() {
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable
    usleep $(($1 * 1000))
    echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
}

UPDATE_PATH="/useremain/update_swu"

RINKHALS_PATH="/useremain/rinkhals"
RINKHALS_ROOT=$(dirname $(realpath /useremain/rinkhals/.current))

# List all directories in RINKHALS_PATH except symlinks
installs=$(find "$RINKHALS_PATH" -mindepth 1 -maxdepth 1 -type d ! -lname '*')

# Separate installs with and without date prefix (YYYYMMDD_)
non_dates_installs=""
dates_installs=""

for i in $installs; do
    basename=$(basename "$i")
    if [ "$i" = "$RINKHALS_ROOT" ] || [ "$basename" = "dev" ]; then
        continue
    fi
    if echo "$basename" | grep -qE '^20[0-9]{6}_'; then
        dates_installs="$dates_installs $i"
    else
        non_dates_installs="$non_dates_installs $i"
    fi
done

# Remove non-date installs
for i in $non_dates_installs; do
    echo rm -rf "$i"
done

# Sort date installs descending, keep 2 newest, remove the rest
dates_installs_sorted=$(echo $dates_installs | tr ' ' '\n' | sort -r)
count=0
for i in $dates_installs_sorted; do
    count=$((count + 1))
    if [ $count -le 2 ]; then
        continue
    fi
    echo rm -rf "$i"
done

# Cleanup
cd
rm -rf $TMP_PATH
rm -rf $UPDATE_PATH
sync

# Beep to notify completion
beep 500
