#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 4768499bf8f7f191dbaddcc77c06dbc0
# After MD5: f3163e53b09fb308ed32f73dec725dd5

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "f3163e53b09fb308ed32f73dec725dd5" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "4768499bf8f7f191dbaddcc77c06dbc0" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo '7oU=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6660248 obs=1 count=2 conv=notrunc # 0x65a098 / 0x66a098 > 0xee85

rm $PATCH_FILE
