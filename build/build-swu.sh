#!/bin/sh

# From a Windows machine:
#   docker run --rm -it -e VERSION="yyyymmdd_nn" -v .\build:/build -v .\files:/files ghcr.io/jbatonnet/rinkhals/build /build/build-swu.sh

set -e


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

echo "Building layer 2/4 (external)..."
cp -r /files/2-external/* /tmp/update_swu/rinkhals

echo "Building layer 3/4 (python)..."
cp -r /files/3-python/* /tmp/update_swu/rinkhals

echo "Building layer 4/4 (rinkhals)..."
cp -r /files/4-rinkhals/* /tmp/update_swu/rinkhals

if [ "$VERSION" != "yyyymmdd_nn" ] && [ "$VERSION" != "" ]; then
    echo "$VERSION" > /tmp/update_swu/.version
    echo "$VERSION" > /tmp/update_swu/rinkhals/.version
else
    echo "dev" > /tmp/update_swu/.version
    echo "dev" > /tmp/update_swu/rinkhals/.version
fi


# Recreate symbolic links to save space and remove .pyc files
echo "Optimizing size..."

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

mkdir -p /build/dist/update_swu
rm -rf /build/dist/update_swu/*

cd /tmp/update_swu
tar -czf /build/dist/update_swu/setup.tar.gz --exclude='setup.tar.gz' .


# Create the update.swu
rm -rf /build/dist/update.swu

cd /build/dist
zip -P U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w= -r update.swu update_swu

echo "Done, your update package is ready: build/dist/update.swu"
