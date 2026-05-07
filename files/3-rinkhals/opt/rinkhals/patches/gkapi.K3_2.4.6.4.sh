#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 996da425632d3060e0b33f13813a1f26
# After MD5: ab2d2da8a9cb035ecd5b9fefb16e9c4e

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "ab2d2da8a9cb035ecd5b9fefb16e9c4e" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "996da425632d3060e0b33f13813a1f26" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'iC9z' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6429968 obs=1 count=3 conv=notrunc # 0x621d10 / 0x631d10 > 0x882f73

rm $PATCH_FILE
