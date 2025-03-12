#!/bin/sh

# From a Windows machine:
#   docker run --rm -it -e KOBRA_IP=x.x.x.x -v .\build:/build -v .\files:/files --entrypoint=/bin/sh rclone/rclone:1.68.2 /build/4-apps/deploy-apps.sh


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
for APP_ROOT in $(find /files/4-apps/home/rinkhals/apps -type d -mindepth 1 -maxdepth 1); do
    if [ ! -f $APP_ROOT/app.sh ]; then
        continue
    fi

    APP=$(basename $APP_ROOT)

    echo "Syncing $APP to /useremain/rinkhals/dev/home/rinkhals/apps/$APP..."

    rclone -v sync --absolute \
        --filter "- /*.log"  --filter "- /.enable" --filter "- /.disable" --filter "+ *" \
        $APP_ROOT Kobra:/useremain/rinkhals/dev/home/rinkhals/apps/$APP
done
