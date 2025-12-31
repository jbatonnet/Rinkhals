#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: dc7c5367bc041577bfb21a37375c5865
# After MD5: 7f35a084d7f378851a974f93fea3c416

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "7f35a084d7f378851a974f93fea3c416" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "dc7c5367bc041577bfb21a37375c5865" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'UiVy' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6403788 obs=1 count=3 conv=notrunc # 0x61b6cc / 0x62b6cc > 0x522572

rm $PATCH_FILE
