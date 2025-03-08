python /opt/rinkhals/proxy/moonraker-proxy.py >> $RINKHALS_ROOT/logs/app-moonraker.log 2>&1 &
HOME=/userdata/app/gk python ./moonraker/moonraker/moonraker.py >> $RINKHALS_ROOT/logs/app-moonraker.log 2>&1
