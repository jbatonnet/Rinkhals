#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 1c3e02d598b05c163bbce78f8d71a86a
# After MD5: 25ade4dbeb3c495c23b6cbc03eb4f90a

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "25ade4dbeb3c495c23b6cbc03eb4f90a" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "1c3e02d598b05c163bbce78f8d71a86a" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'UiVy' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6403788 obs=1 count=3 conv=notrunc # 0x61b6cc / 0x62b6cc > 0x522572

rm $PATCH_FILE
