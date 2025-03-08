chmod +x rinkhals-monitor

while [ 1 ]; do
	./rinkhals-monitor >> $RINKHALS_ROOT/logs/monitor.log 2>&1
	sleep 5
done
