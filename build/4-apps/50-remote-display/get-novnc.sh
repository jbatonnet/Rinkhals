#!/bin/sh

# Used by main Dockerfile

mkdir /work
cd /work

NOVNC_VERSION="1.6.0"
APP_DIRECTORY=/files/4-apps/home/rinkhals/apps/50-remote-display

echo "Downloading noVNC..."

wget -O novnc.zip https://github.com/novnc/noVNC/archive/refs/tags/v${NOVNC_VERSION}.zip
unzip -d novnc novnc.zip

# Remove everything except the web files
find /work/novnc/*/* -mindepth 1 ! -name 'vnc.html' ! -name 'app' ! -name 'core' ! -name 'vendor' \
  ! -path "/work/novnc/*/app/*" \
  ! -path "/work/novnc/*/core/*" \
  ! -path "/work/novnc/*/vendor/*" \
  -exec rm -rf {} +

mkdir -p $APP_DIRECTORY/novnc
rm -rf $APP_DIRECTORY/novnc/*
cp -pr /work/novnc/*/* $APP_DIRECTORY/novnc
mv $APP_DIRECTORY/index.vnc $APP_DIRECTORY/novnc/
