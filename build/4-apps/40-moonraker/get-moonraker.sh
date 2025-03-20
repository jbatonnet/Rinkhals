#!/bin/sh

# Run from Docker:
#   docker run --rm -it -v .\build:/build -v .\files:/files ghcr.io/jbatonnet/rinkhals/build /build/4-apps/40-moonraker/get-moonraker.sh

mkdir /work
cd /work


MOONRAKER_DIRECTORY=/files/4-apps/home/rinkhals/apps/40-moonraker


echo "Downloading Moonraker..."

wget -O moonraker.zip https://github.com/jbatonnet/Rinkhals.Moonraker/archive/refs/heads/rinkhals-next.zip
unzip -d moonraker moonraker.zip

mkdir -p $MOONRAKER_DIRECTORY/moonraker
rm -rf $MOONRAKER_DIRECTORY/moonraker/*
cp -pr /work/moonraker/*/* $MOONRAKER_DIRECTORY/moonraker

CURRENT_DATE=$(date +"%Y-%m-%d")
sed -i "s/\"version\": *\"[^\"]*\"/\"version\": \"${CURRENT_DATE}\"/" $MOONRAKER_DIRECTORY/app.json
