#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 49fb8e909b47bc16ec4d02287b1bc1ac
# After MD5: c6455a1cdf64c5a1969335c30cd2d571

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "c6455a1cdf64c5a1969335c30cd2d571" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "49fb8e909b47bc16ec4d02287b1bc1ac" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'fIA=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6640932 obs=1 count=2 conv=notrunc # 0x655524 / 0x665524 > 0x7c80

rm $PATCH_FILE
