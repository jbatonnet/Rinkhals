. /useremain/rinkhals/.current/tools.sh

# Activate Python venv
python -m venv --without-pip .
. bin/activate

# Start Klippy
HOME=/userdata/app/gk python ./moonraker/moonraker/moonraker.py -c /userdata/app/gk/printer_data/config/moonraker.generated.conf >> $RINKHALS_ROOT/logs/app-moonraker.log 2>&1
