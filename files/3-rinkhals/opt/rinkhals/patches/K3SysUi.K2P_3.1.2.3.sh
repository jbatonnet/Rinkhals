#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: f8f1bc1dd2af13201f4f58ee4f79ed66
# After MD5: 338a5c38a2d062094034a763d15f0705

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "338a5c38a2d062094034a763d15f0705" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "f8f1bc1dd2af13201f4f58ee4f79ed66" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AwsO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2gAAJ/lAAAA6pDICQDO//3rBQCg4QAQ40kqAOsFAKDhARCg40YqAOv79P/qUmlua2hhbA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=564408 obs=1 count=2 conv=notrunc # 0x89cb8 / 0x99cb8 > 0x030b
dd if=$PATCH_FILE skip=2 ibs=1 of=$TARGET seek=575628 obs=1 count=64 conv=notrunc # 0x8c88c / 0x9c88c > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e736800
dd if=$PATCH_FILE skip=66 ibs=1 of=$TARGET seek=575693 obs=1 count=21 conv=notrunc # 0x8c8cd / 0x9c8cd > 0x009fe5000000ea90c80900cefffdeb0500a0e10010
dd if=$PATCH_FILE skip=87 ibs=1 of=$TARGET seek=575715 obs=1 count=21 conv=notrunc # 0x8c8e3 / 0x9c8e3 > 0xe3492a00eb0500a0e10110a0e3462a00ebfbf4ffea
dd if=$PATCH_FILE skip=108 ibs=1 of=$TARGET seek=1049948 obs=1 count=7 conv=notrunc # 0x10055c / 0x11055c > 0x52696e6b68616c

rm $PATCH_FILE
