#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: d51716c204bfab5f273b478b827b213a
# After MD5: 647578d4252036964cedc0395cd3bf78

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "647578d4252036964cedc0395cd3bf78" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "d51716c204bfab5f273b478b827b213a" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'Oh0A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaAAEAKDhAwBTweL/GgAAn+UAAOp4khEAikj86xAAG+UAkOUgfgDruuL/6lJpbmtoYWxzAA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1056196 obs=1 count=4 conv=notrunc # 0x101dc4 / 0x111dc4 > 0x3a1d00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1086068 obs=1 count=71 conv=notrunc # 0x109274 / 0x119274 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e7368000400a0e1030053
dd if=$PATCH_FILE skip=75 ibs=1 of=$TARGET seek=1086140 obs=1 count=9 conv=notrunc # 0x1092bc / 0x1192bc > 0xc1e2ff1a00009fe500
dd if=$PATCH_FILE skip=84 ibs=1 of=$TARGET seek=1086150 obs=1 count=14 conv=notrunc # 0x1092c6 / 0x1192c6 > 0x00ea789211008a48fceb10001be5
dd if=$PATCH_FILE skip=98 ibs=1 of=$TARGET seek=1086165 obs=1 count=11 conv=notrunc # 0x1092d5 / 0x1192d5 > 0x0090e5207e00ebbae2ffea
dd if=$PATCH_FILE skip=109 ibs=1 of=$TARGET seek=2689176 obs=1 count=9 conv=notrunc # 0x290898 / 0x2a0898 > 0x52696e6b68616c7300

rm $PATCH_FILE
