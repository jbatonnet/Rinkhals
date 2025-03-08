#!/bin/sh

PIP_TEMP=/useremain/tmp/pip
mkdir -p $PIP_TEMP

export HOME=$PIP_TEMP
export TMPDIR=$PIP_TEMP

python -m ensurepip
python -m pip install -r /usr/share/moonraker/scripts/moonraker-requirements.txt
python -m pip install websockets paho-mqtt aiohttp evdev

rm -rf $PIP_TEMP
