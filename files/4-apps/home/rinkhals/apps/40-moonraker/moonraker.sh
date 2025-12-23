. /useremain/rinkhals/.current/tools.sh

# Activate Python venv
python -m venv --without-pip .
. bin/activate

# Copy Kobra component
cp -rf kobra.py moonraker/moonraker/components/kobra.py
cp -rf mmu_ace.py moonraker/moonraker/components/mmu_ace.py

# Sometimes .moonraker.uuid is empty for some reason (#199)
if [ ! -s /useremain/home/rinkhals/printer_data/.moonraker.uuid ]; then
    rm -f /useremain/home/rinkhals/printer_data/.moonraker.uuid 2>/dev/null
fi

# Generate configuration
[ -f /userdata/app/gk/printer_data/config/moonraker.custom.conf ] || cp moonraker.custom.conf /userdata/app/gk/printer_data/config/moonraker.custom.conf
python /opt/rinkhals/scripts/process-cfg.py moonraker.conf > /userdata/app/gk/printer_data/config/moonraker.generated.conf

# Start Klippy
mkdir -p /useremain/tmp
TMPDIR=/useremain/tmp HOME=/userdata/app/gk python ./moonraker/moonraker/moonraker.py -c /userdata/app/gk/printer_data/config/moonraker.generated.conf >> $RINKHALS_LOGS/app-moonraker.log 2>&1
