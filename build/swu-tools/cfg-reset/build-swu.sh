#!/bin/sh

# From a Windows machine:
#   docker run --rm -it -v .\build:/build -v .\files:/files ghcr.io/jbatonnet/rinkhals/build /build/swu-tools/cfg-reset/build-swu.sh

set -e


# Prepare update
mkdir -p /tmp/update_swu
rm -rf /tmp/update_swu/*

cp /build/swu-tools/cfg-reset/update.sh /tmp/update_swu/update.sh


# Create the setup.tar.gz
echo "Building update package..."

mkdir -p /build/dist/update_swu
rm -rf /build/dist/update_swu/*

cd /tmp/update_swu
tar -czf /build/dist/update_swu/setup.tar.gz --exclude='setup.tar.gz' .


# Create the update.swu
rm -rf /build/dist/update.swu

cd /build/dist
zip -P U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w= -r update.swu update_swu

echo "Done, your update package is ready: build/dist/update.swu"
