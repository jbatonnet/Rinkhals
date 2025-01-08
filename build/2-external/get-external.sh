#!/bin/sh

# Run from Docker:
#   docker run --rm -it -v .\build:/build -v .\files:/files ghcr.io/jbatonnet/rinkhals/build /build/2-external/get-external.sh

mkdir /work
cd /work


# Fluidd
echo "Downloading Fluidd..."

wget -O fluidd.zip https://github.com/fluidd-core/fluidd/releases/download/v1.31.2/fluidd.zip
unzip -d fluidd fluidd.zip

mkdir -p /files/2-external/usr/share/fluidd
rm -rf /files/2-external/usr/share/fluidd/*
cp -pr /work/fluidd/* /files/2-external/usr/share/fluidd


# Mainsail
echo "Downloading Mainsail..."

wget -O mainsail.zip https://github.com/mainsail-crew/mainsail/releases/download/v2.13.1/mainsail.zip
unzip -d mainsail mainsail.zip

mkdir -p /files/2-external/usr/share/mainsail
rm -rf /files/2-external/usr/share/mainsail/*
cp -pr /work/mainsail/* /files/2-external/usr/share/mainsail


# Moonraker
echo "Downloading Moonraker..."

wget -O moonraker.zip https://github.com/utkabobr/moonraker/archive/refs/heads/duckpro.zip
unzip -d moonraker moonraker.zip

mkdir -p /files/2-external/usr/share/moonraker
rm -rf /files/2-external/usr/share/moonraker/*
cp -pr /work/moonraker/*/* /files/2-external/usr/share/moonraker
