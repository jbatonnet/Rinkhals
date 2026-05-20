#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 1347aeab7c2fada74f2beb807ce393fb
# After MD5: 36668b96f37c61723fb0b9dc0e44ccba

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "36668b96f37c61723fb0b9dc0e44ccba" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "1347aeab7c2fada74f2beb807ce393fb" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'YDBz' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6431312 obs=1 count=3 conv=notrunc # 0x622250 / 0x632250 > 0x603073

rm $PATCH_FILE
