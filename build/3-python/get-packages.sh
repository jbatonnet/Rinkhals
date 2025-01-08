#!/bin/sh

# From a Windows machine:
#   docker run --rm -it -e KOBRA_IP=x.x.x.x -v .\build:/build -v .\files:/files --entrypoint=/bin/sh rclone/rclone:1.68.2 /build/3-python/get-packages.sh


if [ "$KOBRA_IP" == "x.x.x.x" ] || [ "$KOBRA_IP" == "" ]; then
    echo "Please specify your Kobra 3 IP using KOBRA_IP environment variable"
    exit 1
fi


export RCLONE_CONFIG_KOBRA_TYPE=sftp
export RCLONE_CONFIG_KOBRA_HOST=$KOBRA_IP
export RCLONE_CONFIG_KOBRA_PORT=${KOBRA_PORT:-22}
export RCLONE_CONFIG_KOBRA_USER=root
export RCLONE_CONFIG_KOBRA_PASS=$(rclone obscure "rockchip")


mkdir -p /files/3-python/usr/lib/python3.11/site-packages
rclone -v sync --exclude "*.pyc" Kobra:/usr/lib/python3.11/site-packages /files/3-python/usr/lib/python3.11/site-packages

#find /usr/local/lib/python3.11/site-packages -name '*.pyc' -type f -delete
#cp -r /usr/local/lib/python3.11/site-packages/* /files/3-python/usr/lib/python3.11/site-packages
