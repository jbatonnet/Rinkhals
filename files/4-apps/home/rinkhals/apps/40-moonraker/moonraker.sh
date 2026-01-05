. /useremain/rinkhals/.current/tools.sh

# Activate Python venv
python -m venv --without-pip .
. bin/activate

# Copy Kobra and Memory Manager components
cp -rf kobra.py moonraker/moonraker/components/kobra.py
cp -rf memory_manager.py moonraker/moonraker/components/memory_manager.py
cp -rf mmu_ace.py moonraker/moonraker/components/mmu_ace.py
cp -rf mmu_ace_metadata.py moonraker/moonraker/components/mmu_ace_metadata.py

# Sometimes .moonraker.uuid is empty for some reason (#199)
if [ ! -s /useremain/home/rinkhals/printer_data/.moonraker.uuid ]; then
    rm -f /useremain/home/rinkhals/printer_data/.moonraker.uuid 2>/dev/null
fi

# Generate configuration
[ -f /userdata/app/gk/printer_data/config/moonraker.custom.conf ] || cp moonraker.custom.conf /userdata/app/gk/printer_data/config/moonraker.custom.conf
python /opt/rinkhals/scripts/process-cfg.py moonraker.conf > /userdata/app/gk/printer_data/config/moonraker.generated.conf

# Optimize kernel message queue parameters for Moonraker IPC performance
sysctl -w kernel.msgmax=65536 >/dev/null 2>&1
sysctl -w kernel.msgmnb=65536 >/dev/null 2>&1

# Graceful shutdown handler
# Ensures Moonraker stops gracefully on SIGTERM/SIGINT
MOONRAKER_PID=""
cleanup() {
    echo "$(date): Received shutdown signal, stopping Moonraker gracefully" >> $RINKHALS_ROOT/logs/app-moonraker.log

    if [ ! -z "$MOONRAKER_PID" ]; then
        # Send SIGTERM to allow graceful cleanup
        kill -TERM $MOONRAKER_PID 2>/dev/null

        # Wait up to 10 seconds for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 $MOONRAKER_PID 2>/dev/null; then
                echo "$(date): Moonraker stopped gracefully" >> $RINKHALS_ROOT/logs/app-moonraker.log
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if kill -0 $MOONRAKER_PID 2>/dev/null; then
            echo "$(date): Force killing Moonraker" >> $RINKHALS_ROOT/logs/app-moonraker.log
            kill -KILL $MOONRAKER_PID 2>/dev/null
        fi
    fi

    exit 0
}

trap cleanup SIGTERM SIGINT

# Auto-restart mechanism with memory limit
# Protects against memory leaks causing system crashes
start_moonraker_with_restart() {
    local crash_count=0
    local max_crashes=5
    local crash_window_start=$(date +%s)

    while true; do
        # Reset crash counter if more than 5 minutes have passed
        local current_time=$(date +%s)
        if [ $((current_time - crash_window_start)) -gt 300 ]; then
            crash_count=0
            crash_window_start=$current_time
        fi

        echo "$(date): Starting Moonraker (crash count: $crash_count/$max_crashes)" >> $RINKHALS_ROOT/logs/app-moonraker.log

        # Python Garbage Collection settings for RAM-constrained systems
        # Enable aggressive GC to prevent memory creep
        export PYTHONGC=1
        # Set GC thresholds (generation0, generation1, generation2)
        # Default: (700, 10, 10) - collect less frequently
        # Aggressive: (500, 5, 5) - collect more frequently to save RAM
        export PYTHONGCTHRESHOLD="500,5,5"

        # Start Moonraker
        mkdir -p /useremain/tmp
        TMPDIR=/useremain/tmp HOME=/userdata/app/gk python ./moonraker/moonraker/moonraker.py \
            -c /userdata/app/gk/printer_data/config/moonraker.generated.conf \
            >> $RINKHALS_ROOT/logs/app-moonraker.log 2>&1 &

        MOONRAKER_PID=$!
        wait $MOONRAKER_PID
        exit_code=$?

        echo "$(date): Moonraker exited with code $exit_code" >> $RINKHALS_ROOT/logs/app-moonraker.log

        # Exit code 0 = clean shutdown (manual stop) → don't restart
        if [ $exit_code -eq 0 ]; then
            echo "$(date): Clean shutdown detected, exiting restart loop" >> $RINKHALS_ROOT/logs/app-moonraker.log
            break
        fi

        # Exit code 137 = killed by OOM or ulimit → restart
        # Exit code 1 = error → restart
        crash_count=$((crash_count + 1))

        if [ $crash_count -ge $max_crashes ]; then
            echo "$(date): ERROR: Too many crashes ($crash_count), stopping auto-restart" >> $RINKHALS_ROOT/logs/app-moonraker.log
            echo "$(date): Check logs: $RINKHALS_ROOT/logs/app-moonraker.log" >> $RINKHALS_ROOT/logs/app-moonraker.log
            break
        fi

        # Wait before restart
        echo "$(date): Waiting 10 seconds before restart..." >> $RINKHALS_ROOT/logs/app-moonraker.log
        sleep 10
    done
}

# Start Moonraker with auto-restart protection
start_moonraker_with_restart
