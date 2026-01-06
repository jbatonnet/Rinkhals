#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: c705689d74cce5f098fc685753b274b2
# After MD5: cf0eb0222219691a910097d95cb051b7

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "cf0eb0222219691a910097d95cb051b7" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "c705689d74cce5f098fc685753b274b2" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'CSdy' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6411836 obs=1 count=3 conv=notrunc # 0x61d63c / 0x62d63c > 0x092772

rm $PATCH_FILE
