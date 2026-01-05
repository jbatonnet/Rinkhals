#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 1bbc9f9762610c94a4ae640fff02049b
# After MD5: 4eb69fbf4da95bdd329150d683c3707d

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "4eb69fbf4da95bdd329150d683c3707d" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "1bbc9f9762610c94a4ae640fff02049b" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'UiVy' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=6403788 obs=1 count=3 conv=notrunc # 0x61b6cc / 0x62b6cc > 0x522572

rm $PATCH_FILE
