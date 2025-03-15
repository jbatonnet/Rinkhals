#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 91ab25e14b890cbce21f3472ef94c307
# After MD5: c5e7b86db3c38534ccc58ba50941103b

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "c5e7b86db3c38534ccc58ba50941103b" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "91ab25e14b890cbce21f3472ef94c307" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo '6hwA6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaAAEAKDhAwBTEeP/GgAAn+UAAOrEZRQArZf76xAAG+UAkOWDfQDrCuP/6lJpbmtoYWxzAA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1241680 obs=1 count=4 conv=notrunc # 0x12f250 / 0x13f250 > 0xea1c00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1271232 obs=1 count=71 conv=notrunc # 0x1365c0 / 0x1465c0 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e7368000400a0e1030053
dd if=$PATCH_FILE skip=75 ibs=1 of=$TARGET seek=1271304 obs=1 count=9 conv=notrunc # 0x136608 / 0x146608 > 0x11e3ff1a00009fe500
dd if=$PATCH_FILE skip=84 ibs=1 of=$TARGET seek=1271314 obs=1 count=14 conv=notrunc # 0x136612 / 0x146612 > 0x00eac4651400ad97fbeb10001be5
dd if=$PATCH_FILE skip=98 ibs=1 of=$TARGET seek=1271329 obs=1 count=11 conv=notrunc # 0x136621 / 0x146621 > 0x0090e5837d00eb0ae3ffea
dd if=$PATCH_FILE skip=109 ibs=1 of=$TARGET seek=2866868 obs=1 count=9 conv=notrunc # 0x2bbeb4 / 0x2cbeb4 > 0x52696e6b68616c7300

rm $PATCH_FILE
