#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: e8c68f59e35d29c7ae080c3c5403e6f9
# After MD5: 319890a577a77b3238ab738e128421d3

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "319890a577a77b3238ab738e128421d3" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "e8c68f59e35d29c7ae080c3c5403e6f9" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4cEDAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2gAAACf5QAAAOpAiA8AUrcIABvlAACQ5RCg3DIA6wgAGwAAkOUBEOPYMgA7/P/qUmlua2hhbHMAUmlua2hhbA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=117877 obs=1 count=7 conv=notrunc # 0x1cc75 / 0x2cc75 > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=948592 obs=1 count=4 conv=notrunc # 0xe7970 / 0xf7970 > 0xc10300ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=952380 obs=1 count=78 conv=notrunc # 0xe883c / 0xf883c > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73680000009fe5000000ea40880f0052b7
dd if=$PATCH_FILE skip=89 ibs=1 of=$TARGET seek=952460 obs=1 count=8 conv=notrunc # 0xe888c / 0xf888c > 0x08001be5000090e5
dd if=$PATCH_FILE skip=97 ibs=1 of=$TARGET seek=952469 obs=1 count=2 conv=notrunc # 0xe8895 / 0xf8895 > 0x10a0
dd if=$PATCH_FILE skip=99 ibs=1 of=$TARGET seek=952472 obs=1 count=7 conv=notrunc # 0xe8898 / 0xf8898 > 0xdc3200eb08001b
dd if=$PATCH_FILE skip=106 ibs=1 of=$TARGET seek=952480 obs=1 count=6 conv=notrunc # 0xe88a0 / 0xf88a0 > 0x000090e50110
dd if=$PATCH_FILE skip=112 ibs=1 of=$TARGET seek=952487 obs=1 count=4 conv=notrunc # 0xe88a7 / 0xf88a7 > 0xe3d83200
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=952492 obs=1 count=4 conv=notrunc # 0xe88ac / 0xf88ac > 0x3bfcffea
dd if=$PATCH_FILE skip=120 ibs=1 of=$TARGET seek=2736260 obs=1 count=16 conv=notrunc # 0x29c084 / 0x2ac084 > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
