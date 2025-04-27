#!/bin/sh

# docker run --rm -it -e KOBRA_IP=x.x.x.x --mount type=bind,ro,source=./build,target=/build rclone/rclone:1.69.1 /build/deploy-dev.sh

set -e

if [ "$KOBRA_IP" == "x.x.x.x" ] || [ "$KOBRA_IP" == "" ]; then
    echo "Please specify your Kobra printer IP using KOBRA_IP environment variable"
    exit 1
fi

# Configure Kobra remote
export RCLONE_CONFIG_KOBRA_TYPE=sftp
export RCLONE_CONFIG_KOBRA_HOST=$KOBRA_IP
export RCLONE_CONFIG_KOBRA_PORT=${KOBRA_PORT:-22}
export RCLONE_CONFIG_KOBRA_USER=root
export RCLONE_CONFIG_KOBRA_PASS=$(rclone obscure "rockchip")

# Extract Rinkhals package
mkdir -p /tmp/target
rm -rf /tmp/target/*
tar -xzf /build/dist/update_swu/setup.tar.gz  -C /tmp/target

echo "dev" > /tmp/target/rinkhals/.version
touch /tmp/target/rinkhals/.enable-rinkhals

# Stage application files
echo "Updating application files in staging area..."
rclone sync --absolute --copy-links --checksum --no-update-modtime \
    --filter "- *.log" --filter "- *.pyc" --filter "- .env" --filter "- .patch" --filter "- cache_*.json" --filter "- __pycache__/**" \
    --filter "+ /*.*" --filter "+ /bin/**" --filter "+ /sbin/**" --filter "+ /usr/**" --filter "+ /etc/**" --filter "+ /opt/**" --filter "+ /home/**" --filter "+ /lib/**" --filter "+ /.version" \
    --filter "- *" \
    /tmp/target/rinkhals /build/dist/deploy_staging

# Sync startup files
echo "Syncing startup files..."
rclone -v sync --absolute --copy-links \
    --filter "- /rinkhals" --filter "- /update.sh" --filter "- /.version" --filter "- /*.log" --filter "+ /*" --filter "- *" \
    /tmp/target Kobra:/useremain/rinkhals

# Sync application files
echo "Syncing application files..."
rclone -v sync --absolute --sftp-disable-hashcheck --copy-links \
    --filter "- *.log" --filter "- *.pyc" --filter "- .env" --filter "- .patch" --filter "- cache_*.json" --filter "- __pycache__/**" \
    --filter "+ /*.*" --filter "+ /bin/**" --filter "+ /sbin/**" --filter "+ /usr/**" --filter "+ /etc/**" --filter "+ /opt/**" --filter "+ /home/**" --filter "+ /lib/**" --filter "+ /.version" \
    --filter "- *" \
    /build/dist/deploy_staging Kobra:/useremain/rinkhals/dev

echo "Deployment complete"
echo "Run the following command to activate the dev version:"
echo "  chmod +x /useremain/rinkhals/dev/start.sh && /useremain/rinkhals/dev/start.sh"
