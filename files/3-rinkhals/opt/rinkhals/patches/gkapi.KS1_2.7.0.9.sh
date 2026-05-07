#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 19946492d97226450d9ec6eb63305e67
# After MD5: 1d3b9cf0f5df130a1cb844ec3c0a57cd

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "1d3b9cf0f5df130a1cb844ec3c0a57cd" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "19946492d97226450d9ec6eb63305e67" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'eYs=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6666448 obs=1 count=2 conv=notrunc # 0x65b8d0 / 0x66b8d0 > 0x798b

rm $PATCH_FILE
