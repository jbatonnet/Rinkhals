#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 25b5e89b7f25ebcb0e45f26dac5fabe6
# After MD5: 848c08121f8d050624a8a40c0018a1cc

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "848c08121f8d050624a8a40c0018a1cc" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "25b5e89b7f25ebcb0e45f26dac5fabe6" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'YDBz' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6431312 obs=1 count=3 conv=notrunc # 0x622250 / 0x632250 > 0x603073

rm $PATCH_FILE
