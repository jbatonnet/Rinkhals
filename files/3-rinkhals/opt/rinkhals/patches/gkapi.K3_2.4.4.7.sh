#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: c6732b9d419fed042b5cc55db857280e
# After MD5: 6da1bee35930cfc63df8ddc4c1a3debc

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "6da1bee35930cfc63df8ddc4c1a3debc" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "c6732b9d419fed042b5cc55db857280e" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'IiVy' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6402704 obs=1 count=3 conv=notrunc # 0x61b290 / 0x62b290 > 0x222572

rm $PATCH_FILE
