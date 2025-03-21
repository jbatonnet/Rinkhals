#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: f77300db15a6990066a0268de66338fa
# After MD5: 2cd56b66f3902fca2a7e116c0ecdaf28

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "2cd56b66f3902fca2a7e116c0ecdaf28" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "f77300db15a6990066a0268de66338fa" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'Oh0A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaAAAn+UAAOrIkhEAiUj86xAb5QAAkOUofgDrveL/6lJpbmtoYWxzAA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1056276 obs=1 count=4 conv=notrunc # 0x101e14 / 0x111e14 > 0x3a1d00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1086148 obs=1 count=64 conv=notrunc # 0x1092c4 / 0x1192c4 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e736800
dd if=$PATCH_FILE skip=68 ibs=1 of=$TARGET seek=1086213 obs=1 count=3 conv=notrunc # 0x109305 / 0x119305 > 0x009fe5
dd if=$PATCH_FILE skip=71 ibs=1 of=$TARGET seek=1086217 obs=1 count=12 conv=notrunc # 0x109309 / 0x119309 > 0x0000eac89211008948fceb10
dd if=$PATCH_FILE skip=83 ibs=1 of=$TARGET seek=1086230 obs=1 count=14 conv=notrunc # 0x109316 / 0x119316 > 0x1be5000090e5287e00ebbde2ffea
dd if=$PATCH_FILE skip=97 ibs=1 of=$TARGET seek=2689272 obs=1 count=9 conv=notrunc # 0x2908f8 / 0x2a08f8 > 0x52696e6b68616c7300

rm $PATCH_FILE
