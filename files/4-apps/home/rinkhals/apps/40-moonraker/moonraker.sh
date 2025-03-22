. /useremain/rinkhals/.current/tools.sh

# Activate Python venv
python -m venv --without-pip .
. bin/activate

# Copy Kobra component
cp -rf kobra.py moonraker/moonraker/components/kobra.py

# Generate configuration
[ -f /userdata/app/gk/printer_data/config/moonraker.custom.conf ] || cp moonraker.custom.conf /userdata/app/gk/printer_data/config/moonraker.custom.conf
python /opt/rinkhals/scripts/process-cfg.py moonraker.conf > /userdata/app/gk/printer_data/config/moonraker.generated.conf

# Start Klippy
HOME=/userdata/app/gk python ./moonraker/moonraker/moonraker.py -c /userdata/app/gk/printer_data/config/moonraker.generated.conf >> $RINKHALS_ROOT/logs/app-moonraker.log 2>&1
