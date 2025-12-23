#!/bin/sh

# Used by main Dockerfile

set -e

mkdir -p /files/4-apps/home/rinkhals/apps/40-moonraker
cd /files/4-apps/home/rinkhals/apps/40-moonraker

echo "Removing old packages..."
rm -rf lib

echo "Creating Moonraker venv..."
python -m venv .
. bin/activate

echo "Installing Moonraker requirements..."
python -m pip install -r moonraker/scripts/moonraker-requirements.txt

echo "Cleaning up..."
rm -rf bin
rm -rf include
rm -rf lib/python3.*/site-packages/_distutils_hack
rm -rf lib/python3.*/site-packages/pip
rm -rf lib/python3.*/site-packages/pip*
rm -rf lib/python3.*/site-packages/pkg_resources
rm -rf lib/python3.*/site-packages/setuptools
rm -rf lib/python3.*/site-packages/setuptools*
rm -f lib/python3.*/site-packages/distutils-precedence.pth
rm -f pyvenv.cfg
find lib/python3.* -name '*.pyc' -type f | xargs rm
