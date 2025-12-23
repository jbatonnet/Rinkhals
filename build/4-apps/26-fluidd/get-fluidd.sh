#!/bin/sh

# Used by main Dockerfile

mkdir /work
cd /work


FLUIDD_VERSION="1.35.0"
FLUIDD_DIRECTORY=/files/4-apps/home/rinkhals/apps/26-fluidd


echo "Downloading Fluidd..."

wget -O fluidd.zip https://github.com/fluidd-core/fluidd/releases/download/v${FLUIDD_VERSION}/fluidd.zip
unzip -d fluidd fluidd.zip

mkdir -p $FLUIDD_DIRECTORY/fluidd
rm -rf $FLUIDD_DIRECTORY/fluidd/*
cp -pr /work/fluidd/* $FLUIDD_DIRECTORY/fluidd

sed -i "s/\"version\": *\"[^\"]*\"/\"version\": \"${FLUIDD_VERSION}\"/" $FLUIDD_DIRECTORY/app.json
