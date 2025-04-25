#!/bin/sh

# Run from Docker:
#   docker run --rm -it -v .\build:/build -v .\files:/files ghcr.io/jbatonnet/rinkhals/build /build/4-apps/26-fluidd/get-fluidd.sh

mkdir /work
cd /work


FLUIDD_VERSION="1.34.1"
FLUIDD_DIRECTORY=/files/4-apps/home/rinkhals/apps/26-fluidd


echo "Downloading Fluidd..."

wget -O fluidd.zip https://github.com/fluidd-core/fluidd/releases/download/v${FLUIDD_VERSION}/fluidd.zip
unzip -d fluidd fluidd.zip

mkdir -p $FLUIDD_DIRECTORY/fluidd
rm -rf $FLUIDD_DIRECTORY/fluidd/*
cp -pr /work/fluidd/* $FLUIDD_DIRECTORY/fluidd

sed -i "s/\"version\": *\"[^\"]*\"/\"version\": \"${FLUIDD_VERSION}\"/" $FLUIDD_DIRECTORY/app.json
