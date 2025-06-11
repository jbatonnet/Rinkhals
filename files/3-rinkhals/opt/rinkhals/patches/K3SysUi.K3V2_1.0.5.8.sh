#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 1d990eda4e4c4240efbaa0852fba2b2f
# After MD5: 80f4af5e816f70202bdf0e566212e4ec

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "80f4af5e816f70202bdf0e566212e4ec" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "1d990eda4e4c4240efbaa0852fba2b2f" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4R8EAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACf5QAAAOoo/w8AHpv862QAoOOmrfzrAACfAAAA6o7/DwAYm/zrDwBQ4/f//woAAJ/lAADq6v8PABKb/OsIABvlAJDlBCCg4wEQoOPC9v7rCAAb5QCQBBCg43r4/uvQ+//qUmlua2hhbHMAUmlua2hhbA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=119757 obs=1 count=7 conv=notrunc # 0x1d3cd / 0x2d3cd > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=978828 obs=1 count=4 conv=notrunc # 0xeef8c / 0xfef8c > 0x1f0400ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=982820 obs=1 count=105 conv=notrunc # 0xeff24 / 0xfff24 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=982926 obs=1 count=19 conv=notrunc # 0xeff8e / 0xfff8e > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=135 ibs=1 of=$TARGET seek=982946 obs=1 count=108 conv=notrunc # 0xeffa2 / 0xfffa2 > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=243 ibs=1 of=$TARGET seek=983056 obs=1 count=27 conv=notrunc # 0xf0010 / 0x100010 > 0x00009fe5000000ea28ff0f001e9bfceb6400a0e3a6adfceb00009f
dd if=$PATCH_FILE skip=270 ibs=1 of=$TARGET seek=983084 obs=1 count=25 conv=notrunc # 0xf002c / 0x10002c > 0x000000ea8eff0f00189bfceb0f0050e3f7ffff0a00009fe500
dd if=$PATCH_FILE skip=295 ibs=1 of=$TARGET seek=983110 obs=1 count=15 conv=notrunc # 0xf0046 / 0x100046 > 0x00eaeaff0f00129bfceb08001be500
dd if=$PATCH_FILE skip=310 ibs=1 of=$TARGET seek=983126 obs=1 count=19 conv=notrunc # 0xf0056 / 0x100056 > 0x90e50420a0e30110a0e3c2f6feeb08001be500
dd if=$PATCH_FILE skip=329 ibs=1 of=$TARGET seek=983146 obs=1 count=1 conv=notrunc # 0xf006a / 0x10006a > 0x90
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=983148 obs=1 count=12 conv=notrunc # 0xf006c / 0x10006c > 0x0410a0e37af8feebd0fbffea
dd if=$PATCH_FILE skip=342 ibs=1 of=$TARGET seek=2786176 obs=1 count=16 conv=notrunc # 0x2a8380 / 0x2b8380 > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
