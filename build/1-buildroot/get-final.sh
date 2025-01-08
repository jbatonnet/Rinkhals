#!/bin/sh

# From a Windows machine:
#   docker run --rm -it -e BUILDER_IP=x.x.x.x -e BUILDER_PATH=x -v .\build:/build -v .\files:/files --entrypoint=/bin/sh rclone/rclone:1.68.2 /build/1-buildroot/get-final.sh


if [ "$BUILDER_IP" == "x.x.x.x" ] || [ "$BUILDER_IP" == "" ]; then
    echo "Please specify your builder IP using BUILDER_IP environment variable"
    exit 1
fi
if [ "$BUILDER_PATH" == "x" ] || [ "$BUILDER_PATH" == "" ]; then
    echo "Please specify your builder machine buildroot base path using BUILDER_PATH environment variable"
    exit 1
fi


export RCLONE_CONFIG_BUILDER_TYPE=sftp
export RCLONE_CONFIG_BUILDER_HOST=$BUILDER_IP
export RCLONE_CONFIG_BUILDER_PORT=${BUILDER_PORT:-22}
export RCLONE_CONFIG_BUILDER_USER=${BUILDER_USER:-"root"}
export RCLONE_CONFIG_BUILDER_PASS=$(rclone obscure "${BUILDER_PASS}")


rclone -v sync Builder:$BUILDER_PATH/output/final /files/1-buildroot
