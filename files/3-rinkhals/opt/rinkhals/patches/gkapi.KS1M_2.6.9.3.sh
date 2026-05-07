#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 8b4a567cef8127ce97fa8c8f20af71d7
# After MD5: 2a96fbade3bb6b059bfb8c01faa357e1

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "2a96fbade3bb6b059bfb8c01faa357e1" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "8b4a567cef8127ce97fa8c8f20af71d7" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'MIw=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6673716 obs=1 count=2 conv=notrunc # 0x65d534 / 0x66d534 > 0x308c

rm $PATCH_FILE
