#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: e4546ff669ad8f5b22b74d613cc6c410
# After MD5: 17cbc43fe66f5fb3674f74b1b7054af8

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "17cbc43fe66f5fb3674f74b1b7054af8" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "e4546ff669ad8f5b22b74d613cc6c410" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AACg4w7woOEoAgDqDvCg4S91c2VyZW1haW4vcmlua2hhbHMvLmN1cnJlbnQvb3B0L3JpbmtoYWxzL3VpL3JpbmtoYWxzLXVpLnNoAAAAn+UAAOr4pQ4AhNT86wgAlOUAEKDj0SwA6wiU5QEQoOPOLADqUmlua2hhbHMAUmlua2hhbA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=202352 obs=1 count=8 conv=notrunc # 0x31670 / 0x41670 > 0x0000a0e30ef0a0e1
dd if=$PATCH_FILE skip=8 ibs=1 of=$TARGET seek=892300 obs=1 count=4 conv=notrunc # 0xd9d8c / 0xe9d8c > 0x280200ea
dd if=$PATCH_FILE skip=12 ibs=1 of=$TARGET seek=894452 obs=1 count=69 conv=notrunc # 0xda5f4 / 0xea5f4 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73680000009fe500
dd if=$PATCH_FILE skip=81 ibs=1 of=$TARGET seek=894522 obs=1 count=23 conv=notrunc # 0xda63a / 0xea63a > 0x00eaf8a50e0084d4fceb080094e50010a0e3d12c00eb08
dd if=$PATCH_FILE skip=104 ibs=1 of=$TARGET seek=894546 obs=1 count=10 conv=notrunc # 0xda652 / 0xea652 > 0x94e50110a0e3ce2c00ea
dd if=$PATCH_FILE skip=114 ibs=1 of=$TARGET seek=1794928 obs=1 count=16 conv=notrunc # 0x1b6370 / 0x1c6370 > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
