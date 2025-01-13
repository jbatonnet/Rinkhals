#!/bin/sh

function log() {
    echo "${*}"
    echo "$(date): ${*}" >> /useremain/rinkhals/rinkhals.log
}

log
log "Starting Rinkhals..."

CALLER=$(cat /proc/$PPID/cmdline)
log "Rinkhals startup was called from $CALLER ($PPID)"

if [ ! -f /useremain/rinkhals/.version ]; then
    log "Rinkhals is installed but no version is selected to start"
    exit 1
fi

if [ -f /mnt/udisk/.disable-rinkhals ] || [ -f /useremain/rinkhals/.disable-rinkhals ]; then
    log "Rinkhals statup was stopped with the .disable-rinkhals file"
    exit 1
fi

RINKHALS_VERSION=$(cat /useremain/rinkhals/.version)
log "Rinkhals version $RINKHALS_VERSION selected"

if [ ! -d /useremain/rinkhals/$RINKHALS_VERSION ]; then
    log "Rinkhals version $RINKHALS_VERSION does not exist"
    exit 1
fi

cd /useremain/rinkhals/$RINKHALS_VERSION

chmod +x ./start.sh
./start.sh
