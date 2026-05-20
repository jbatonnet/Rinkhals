#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 988971db76662cbbd8d3ef07ed4b6385
# After MD5: 82f7a1077be7654e4edb545db553a1d9

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "82f7a1077be7654e4edb545db553a1d9" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "988971db76662cbbd8d3ef07ed4b6385" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo '7oU=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6660316 obs=1 count=2 conv=notrunc # 0x65a0dc / 0x66a0dc > 0xee85

rm $PATCH_FILE
