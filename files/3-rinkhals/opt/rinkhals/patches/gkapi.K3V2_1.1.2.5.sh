#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: a124545f5aca1e7aa1190d07947c20a5
# After MD5: 04c36f0bdbec43816ad7d566dcaeb8c9

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "04c36f0bdbec43816ad7d566dcaeb8c9" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "a124545f5aca1e7aa1190d07947c20a5" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'iC9z' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6429968 obs=1 count=3 conv=notrunc # 0x621d10 / 0x631d10 > 0x882f73

rm $PATCH_FILE
