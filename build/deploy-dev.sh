#!/bin/sh

# From a Windows machine:
#   docker run --rm -it -e KOBRA_IP=x.x.x.x -v .\build:/build -v .\files:/files --entrypoint=/bin/sh rclone/rclone:1.68.2 /build/deploy-dev.sh


if [ "$KOBRA_IP" == "x.x.x.x" ] || [ "$KOBRA_IP" == "" ]; then
    echo "Please specify your Kobra 3 IP using KOBRA_IP environment variable"
    exit 1
fi


export RCLONE_CONFIG_KOBRA_TYPE=sftp
export RCLONE_CONFIG_KOBRA_HOST=$KOBRA_IP
export RCLONE_CONFIG_KOBRA_PORT=${KOBRA_PORT:-22}
export RCLONE_CONFIG_KOBRA_USER=root
export RCLONE_CONFIG_KOBRA_PASS=$(rclone obscure "rockchip")

# Sync base files
mkdir -p /tmp/target
rm -rf /tmp/target/*

cp -pr /files/*.* /tmp/target

rclone -v sync --absolute \
    --filter "- /*.log" --filter "- /update.sh" --filter "- /.version" --filter "+ /*" --filter "- *" \
    /tmp/target Kobra:/useremain/rinkhals


# Combine layers
mkdir -p /tmp/target
rm -rf /tmp/target/*

echo "Building layer 1/4 (buildroot)..."
cp -pr /files/1-buildroot/* /tmp/target

echo "Building layer 2/4 (external)..."
cp -pr /files/2-external/* /tmp/target

echo "Building layer 3/4 (python)..."
cp -pr /files/3-python/* /tmp/target

echo "Building layer 4/4 (rinkhals)..."
cp -pr /files/4-rinkhals/* /tmp/target

echo "dev" > /tmp/target/.version

# Push to the Kobra
rclone -v sync --absolute --sftp-disable-hashcheck \
    --filter "- *.log" --filter "- *.pyc" --filter "- .env" --filter "- __pycache__/**" \
    --filter "+ /*.*" --filter "+ /bin/**" --filter "+ /sbin/**" --filter "+ /usr/**" --filter "+ /etc/**" --filter "+ /opt/**" --filter "+ /home/**" --filter "+ /lib/**" --filter "+ /.version" \
    --filter "- *" \
    /tmp/target Kobra:/useremain/rinkhals/dev
