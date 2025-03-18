#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: d51716c204bfab5f273b478b827b213a
# After MD5: e9cdde29f703aad50db70e668af6e5f0

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "e9cdde29f703aad50db70e668af6e5f0" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "d51716c204bfab5f273b478b827b213a" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'Oh0A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaAAAn+UAAOp4khEAjUj86xAb5QAAkOUjfgDrveL/6lJpbmtoYWxzAA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1056196 obs=1 count=4 conv=notrunc # 0x101dc4 / 0x111dc4 > 0x3a1d00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1086068 obs=1 count=64 conv=notrunc # 0x109274 / 0x119274 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e736800
dd if=$PATCH_FILE skip=68 ibs=1 of=$TARGET seek=1086133 obs=1 count=3 conv=notrunc # 0x1092b5 / 0x1192b5 > 0x009fe5
dd if=$PATCH_FILE skip=71 ibs=1 of=$TARGET seek=1086137 obs=1 count=12 conv=notrunc # 0x1092b9 / 0x1192b9 > 0x0000ea789211008d48fceb10
dd if=$PATCH_FILE skip=83 ibs=1 of=$TARGET seek=1086150 obs=1 count=14 conv=notrunc # 0x1092c6 / 0x1192c6 > 0x1be5000090e5237e00ebbde2ffea
dd if=$PATCH_FILE skip=97 ibs=1 of=$TARGET seek=2689176 obs=1 count=9 conv=notrunc # 0x290898 / 0x2a0898 > 0x52696e6b68616c7300

rm $PATCH_FILE
