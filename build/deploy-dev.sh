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





set -- --filter "- *.log" --filter "- *.pyc" --filter "- .env" --filter "- .patch" --filter "- cache_*.json" --filter "- __pycache__/**" --filter "+ /*.*" --filter "+ /bin/**" --filter "+ /sbin/**" --filter "+ /usr/**" --filter "+ /etc/**" --filter "+ /opt/**" --filter "+ /home/**" --filter "+ /lib/**" --filter "+ /.version" --filter "- *"

LIST_1=$(rclone --config "" hashsum md5 --fast-list --max-age 1d "$@" /files/1-buildroot)
LIST_2=$(rclone --config "" hashsum md5 --fast-list --max-age 1d "$@" /files/2-python)
LIST_3=$(rclone --config "" hashsum md5 --fast-list --max-age 1d "$@" /files/3-rinkhals)
LIST_4=$(rclone --config "" hashsum md5 --fast-list --max-age 1d "$@" /files/4-apps)

LIST=$(printf "$LIST_1\n$LIST_2\n$LIST_3\n$LIST_4" | sort -uV)
echo "$LIST" > /build/cache/current_deploy_dev

LAST_LIST=$(cat /build/cache/last_deploy_dev)

echo "To delete:"
comm -13 /build/cache/last_deploy_dev /build/cache/current_deploy_dev

echo "To copy:"
comm -23 /build/cache/last_deploy_dev /build/cache/current_deploy_dev

exit 0





# Sync base files
mkdir -p /tmp/target
rm -rf /tmp/target/*

cp -pr /files/*.* /tmp/target

#rclone -v sync --absolute \
#    --filter "- /*.log" --filter "- /update.sh" --filter "- /.version" --filter "+ /*" --filter "- *" \
#    /tmp/target Kobra:/useremain/rinkhals


# Combine layers
mkdir -p /tmp/target
rm -rf /tmp/target/*

echo "Building layer 1/4 (buildroot)..."
cp -pr /files/1-buildroot/* /tmp/target

echo "Building layer 2/4 (python)..."
cp -pr /files/2-python/* /tmp/target

echo "Building layer 3/4 (rinkhals)..."
cp -pr /files/3-rinkhals/* /tmp/target

echo "Building layer 4/4 (apps)..."
cp -pr /files/4-apps/* /tmp/target

echo "dev" > /tmp/target/.version

# Push to the Kobra
#rclone -v sync --absolute --sftp-disable-hashcheck \
#    --filter "- *.log" --filter "- *.pyc" --filter "- .env" --filter "- .patch" --filter "- cache_*.json" --filter "- __pycache__/**" \
#    --filter "+ /*.*" --filter "+ /bin/**" --filter "+ /sbin/**" --filter "+ /usr/**" --filter "+ /etc/**" --filter "+ /opt/**" --filter "+ /home/**" --filter "+ /lib/**" --filter "+ /.version" \
#    --filter "- *" \
#    /tmp/target Kobra:/useremain/rinkhals/dev

rclone -v hashsum --absolute --sftp-disable-hashcheck \
   --filter "- *.log" --filter "- *.pyc" --filter "- .env" --filter "- .patch" --filter "- cache_*.json" --filter "- __pycache__/**" \
   --filter "+ /*.*" --filter "+ /bin/**" --filter "+ /sbin/**" --filter "+ /usr/**" --filter "+ /etc/**" --filter "+ /opt/**" --filter "+ /home/**" --filter "+ /lib/**" --filter "+ /.version" \
   --filter "- *" \
   /tmp/target
