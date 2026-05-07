#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 0cebcfbb44ae5ceb3f582ffedaeb6cf2
# After MD5: 5c96db99cd98411e834958c074be054a

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "5c96db99cd98411e834958c074be054a" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "0cebcfbb44ae5ceb3f582ffedaeb6cf2" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'YDBz' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6431312 obs=1 count=3 conv=notrunc # 0x622250 / 0x632250 > 0x603073

rm $PATCH_FILE
