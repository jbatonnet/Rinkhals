#!/bin/sh

# Used by main Dockerfile

set -e

mkdir -p /files/2-python/usr
cd /files/2-python/usr

echo "Removing old packages..."
rm -rf lib

echo "Creating temporary venv..."
python -m venv .
. bin/activate

echo "Installing requirements..."
python -m pip install --upgrade pip
python -m pip install paho-mqtt psutil requests cffi # rinkhals-ui

echo "Cleaning up..."
rm -rf bin
rm -rf include
rm -f pyvenv.cfg
find lib/python3.* -name '*.pyc' -type f | xargs rm
