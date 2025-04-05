#!/bin/sh

# From a Windows machine:
#   docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
#   docker run --platform=linux/arm/v7 --rm -it -v .\build\cache\pip:/root/.cache/pip -v .\build:/build -v .\files:/files ghcr.io/jbatonnet/armv7-uclibc:rinkhals /build/2-python/get-packages.sh


cd /files/2-python/usr

echo "Removing old packages..."
rm -rf lib

echo "Creating temporary venv..."
python -m venv .
. bin/activate

echo "Installing requirements..."
python -m pip install --upgrade pip
python -m pip install paho-mqtt evdev pillow psutil qrcode requests # rinkhals-ui

echo "Cleaning up..."
rm -rf bin
rm -rf include
rm -f pyvenv.cfg
find lib/python3.* -name '*.pyc' -type f | xargs rm
