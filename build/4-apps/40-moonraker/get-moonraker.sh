#!/bin/sh

# Used by main Dockerfile

set -e

mkdir /work
cd /work

MOONRAKER_COMMIT=ebaa6645b2bcaa593d99e863530c52a84c69b470
MOONRAKER_DIRECTORY=/files/4-apps/home/rinkhals/apps/40-moonraker

echo "Downloading Moonraker..."
wget -O moonraker.zip https://github.com/Arksine/moonraker/archive/${MOONRAKER_COMMIT}.zip
unzip -d moonraker moonraker.zip

mkdir -p $MOONRAKER_DIRECTORY/moonraker
rm -rf $MOONRAKER_DIRECTORY/moonraker/*
cp -pr /work/moonraker/*/* $MOONRAKER_DIRECTORY/moonraker

VERSION=$(echo $MOONRAKER_COMMIT | cut -c1-7)
sed -i "s/\"version\": *\"[^\"]*\"/\"version\": \"${VERSION}\"/" $MOONRAKER_DIRECTORY/app.json
