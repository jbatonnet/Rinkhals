#!/bin/sh

PIP_TEMP=/useremain/tmp/pip

mkdir -p $PIP_TEMP

export PATH=/usr/libexec/gcc/arm-buildroot-linux-uclibcgnueabihf/11.4.0:$PATH
export CC=/usr/bin/gcc
export LD_LIBRARY_PATH=/lib:/usr/lib
export HOME=$PIP_TEMP
export TMPDIR=$PIP_TEMP

python -m ensurepip
python -m pip install -r /usr/share/moonraker/scripts/moonraker-requirements.txt
python -m pip install websockets paho-mqtt aiohttp evdev

rm -rf $PIP_TEMP
