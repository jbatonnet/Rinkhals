#!/bin/sh

# Used by main Dockerfile

mkdir /work
cd /work


MAINSAIL_VERSION="2.14.0"
MAINSAIL_DIRECTORY=/files/4-apps/home/rinkhals/apps/25-mainsail


echo "Downloading Mainsail..."

wget -O mainsail.zip https://github.com/mainsail-crew/mainsail/releases/download/v${MAINSAIL_VERSION}/mainsail.zip
unzip -d mainsail mainsail.zip

mkdir -p $MAINSAIL_DIRECTORY/mainsail
rm -rf $MAINSAIL_DIRECTORY/mainsail/*
cp -pr /work/mainsail/* $MAINSAIL_DIRECTORY/mainsail

sed -i "s/\"version\": *\"[^\"]*\"/\"version\": \"${MAINSAIL_VERSION}\"/" $MAINSAIL_DIRECTORY/app.json
