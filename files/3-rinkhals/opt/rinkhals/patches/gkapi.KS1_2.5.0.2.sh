#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: c2fa27fe0b99613699024754f75314bb
# After MD5: 620a89a5f2f52918299ee355160cd360

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "620a89a5f2f52918299ee355160cd360" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "c2fa27fe0b99613699024754f75314bb" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'MC4wOjAw' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=7122773 obs=1 count=3 conv=notrunc # 0x6caf55 / 0x6daf55 > 0x302e30
dd if=$PATCH_FILE skip=3 ibs=1 of=$TARGET seek=7122780 obs=1 count=3 conv=notrunc # 0x6caf5c / 0x6daf5c > 0x3a3030

rm $PATCH_FILE
