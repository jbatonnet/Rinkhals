. /useremain/rinkhals/.current/tools.sh

# Activate Python venv
python -m venv --without-pip .
. bin/activate

# Start Klippy
HOME=/userdata/app/gk python ./moonraker/moonraker/moonraker.py >> $RINKHALS_ROOT/logs/app-moonraker.log 2>&1 &
