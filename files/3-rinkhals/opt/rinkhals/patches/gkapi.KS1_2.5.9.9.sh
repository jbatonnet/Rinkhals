#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 1d3bbe1f5a2255bc3cf6fe8464cd9181
# After MD5: 3dd2b37cf02ac81029ad1b933746dcce

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "3dd2b37cf02ac81029ad1b933746dcce" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "1d3bbe1f5a2255bc3cf6fe8464cd9181" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'UiVy' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6403584 obs=1 count=3 conv=notrunc # 0x61b600 / 0x62b600 > 0x522572

rm $PATCH_FILE
