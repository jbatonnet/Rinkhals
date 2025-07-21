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

# pwntools for binary patching
python -m pip install capstone python-dateutil intervaltree isort mako>=1.0.0 pyelftools>=0.29 pyserial pysocks ropgadget>=5.3
python -m pip install packaging
python -m pip install --no-deps pwntools
rm -rf lib/python3.11/site-packages/pwnlib/shellcraft/templates/*
touch lib/python3.11/site-packages/pwnlib/shellcraft/templates/__doc__

echo "Cleaning up..."
rm -rf bin
rm -rf include
rm -f pyvenv.cfg
find lib/python3.* -name '*.pyc' -type f | xargs rm
