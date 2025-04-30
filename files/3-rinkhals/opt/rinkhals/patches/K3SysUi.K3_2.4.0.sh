#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 9ae93aa475d994aeba1a9e38013b0db8
# After MD5: f613618e901a9850c38e0bad386d0be0

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "f613618e901a9850c38e0bad386d0be0" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "9ae93aa475d994aeba1a9e38013b0db8" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4R8EAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACf5QAAAOoU4g8A/KD862QAoONls/zrAACfAAAA6nriDwD2oPzrDwBQ4/f//woAAJ/lAADq1uIPAPCg/OsIABvlAJDlBCCg4wEQoOMc8v7rCAAb5QCQBBCg49Tz/uvQ+//qUmlua2hhbHMAUmlua2hhbA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=118197 obs=1 count=7 conv=notrunc # 0x1cdb5 / 0x2cdb5 > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=971384 obs=1 count=4 conv=notrunc # 0xed278 / 0xfd278 > 0x1f0400ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=975376 obs=1 count=105 conv=notrunc # 0xee210 / 0xfe210 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=975482 obs=1 count=19 conv=notrunc # 0xee27a / 0xfe27a > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=135 ibs=1 of=$TARGET seek=975502 obs=1 count=108 conv=notrunc # 0xee28e / 0xfe28e > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=243 ibs=1 of=$TARGET seek=975612 obs=1 count=27 conv=notrunc # 0xee2fc / 0xfe2fc > 0x00009fe5000000ea14e20f00fca0fceb6400a0e365b3fceb00009f
dd if=$PATCH_FILE skip=270 ibs=1 of=$TARGET seek=975640 obs=1 count=25 conv=notrunc # 0xee318 / 0xfe318 > 0x000000ea7ae20f00f6a0fceb0f0050e3f7ffff0a00009fe500
dd if=$PATCH_FILE skip=295 ibs=1 of=$TARGET seek=975666 obs=1 count=15 conv=notrunc # 0xee332 / 0xfe332 > 0x00ead6e20f00f0a0fceb08001be500
dd if=$PATCH_FILE skip=310 ibs=1 of=$TARGET seek=975682 obs=1 count=19 conv=notrunc # 0xee342 / 0xfe342 > 0x90e50420a0e30110a0e31cf2feeb08001be500
dd if=$PATCH_FILE skip=329 ibs=1 of=$TARGET seek=975702 obs=1 count=1 conv=notrunc # 0xee356 / 0xfe356 > 0x90
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=975704 obs=1 count=12 conv=notrunc # 0xee358 / 0xfe358 > 0x0410a0e3d4f3feebd0fbffea
dd if=$PATCH_FILE skip=342 ibs=1 of=$TARGET seek=2793676 obs=1 count=16 conv=notrunc # 0x2aa0cc / 0x2ba0cc > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
