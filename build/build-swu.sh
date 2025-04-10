#!/bin/sh

# From a Windows machine:
#   docker run --rm -it -e VERSION="yyyymmdd_nn" -e KOBRA_MODEL_CODE="K3" -v .\build:/build -v .\files:/files ghcr.io/jbatonnet/rinkhals/build /build/build-swu.sh


if [ "$KOBRA_MODEL_CODE" = "" ]; then
    echo "Please specify your Kobra model using KOBRA_MODEL_CODE environment variable"
    exit 1
fi

set -e
BUILD_ROOT=$(dirname $(realpath $0))
. $BUILD_ROOT/tools.sh


# Combine layers
mkdir -p /tmp/update_swu
rm -rf /tmp/update_swu/*
mkdir -p /tmp/update_swu/rinkhals

cp -r /files/*.* /tmp/update_swu
chmod +x /tmp/update_swu/*.sh

echo "Building layer 1/4 (buildroot)..."
cp -r /files/1-buildroot/* /tmp/update_swu/rinkhals

BUSYBOX_TARGET=busybox.rinkhals
rm /tmp/update_swu/rinkhals/bin/busybox
cp -r /files/1-buildroot/bin/busybox /tmp/update_swu/rinkhals/bin/$BUSYBOX_TARGET

echo "Building layer 2/4 (python)..."
cp -r /files/2-python/* /tmp/update_swu/rinkhals

echo "Building layer 3/4 (rinkhals)..."
cp -r /files/3-rinkhals/* /tmp/update_swu/rinkhals

echo "Building layer 4/4 (apps)..."
cp -r /files/4-apps/* /tmp/update_swu/rinkhals

if [ "$VERSION" != "yyyymmdd_nn" ] && [ "$VERSION" != "" ]; then
    echo "$VERSION" > /tmp/update_swu/.version
    echo "$VERSION" > /tmp/update_swu/rinkhals/.version
else
    echo "dev" > /tmp/update_swu/.version
    echo "dev" > /tmp/update_swu/rinkhals/.version
fi


echo "Optimizing size..."

# Remove binary patches to keep only shell patches
find /tmp/update_swu/rinkhals/opt/rinkhals/patches -type f ! -name "*.sh" -exec rm {} +

# Recreate symbolic links to save space and remove .pyc files
cd /tmp/update_swu/rinkhals

for FILE in $(find -type f -name "*.so*"); do
    FILES=$(ls -al $FILE*)
    SIZE=$(echo "$FILES" | head -n 1 | awk '{print $5}')
    CANONICAL=$(echo "$FILES" | awk -v SIZE="$SIZE" '{ if ($5 == SIZE) { print $NF } }' | tail -n 1)

    if [ "$FILE" != "$CANONICAL" ]; then
        #echo "$FILE ($SIZE bytes) > $(basename $CANONICAL)"

        rm $FILE
        ln -s $(basename $CANONICAL) $FILE
    fi
done

BUSYBOX_SIZE=$(ls -al ./bin/$BUSYBOX_TARGET | awk '{print $5}')

for FILE in $(find ./bin -type f | grep -v busybox); do
    SIZE=$(ls -al $FILE | awk '{print $5}')

    if [ "$SIZE" -eq "$BUSYBOX_SIZE" ]; then
        #echo "$FILE ($SIZE bytes) > $BUSYBOX_TARGET"

        rm $FILE
        ln -s $BUSYBOX_TARGET $FILE
    fi
done

for FILE in $(find ./sbin -type f); do
    SIZE=$(ls -al $FILE | awk '{print $5}')

    if [ "$SIZE" -eq "$BUSYBOX_SIZE" ]; then
        #echo "$FILE ($SIZE bytes) > $BUSYBOX_TARGET"

        rm $FILE
        ln -s ../bin/$BUSYBOX_TARGET $FILE
    fi
done

for FILE in $(find ./usr/bin -type f); do
    SIZE=$(ls -al $FILE | awk '{print $5}')

    if [ "$SIZE" -eq "$BUSYBOX_SIZE" ]; then
        #echo "$FILE ($SIZE bytes) > $BUSYBOX_TARGET"

        rm $FILE
        ln -s ../../bin/$BUSYBOX_TARGET $FILE
    fi
done

for FILE in $(find ./usr/sbin -type f); do
    SIZE=$(ls -al $FILE | awk '{print $5}')

    if [ "$SIZE" -eq "$BUSYBOX_SIZE" ]; then
        #echo "$FILE ($SIZE bytes) > $BUSYBOX_TARGET"

        rm $FILE
        ln -s ../../bin/$BUSYBOX_TARGET $FILE
    fi
done


# Create the setup.tar.gz
echo "Building update package..."

SWU_PATH=${1:-/build/dist/update.swu}
build_swu $KOBRA_MODEL_CODE /tmp/update_swu $SWU_PATH

echo "Done, your update package is ready: $SWU_PATH"
