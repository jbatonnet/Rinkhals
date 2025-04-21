#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 9321779517e04f4ba18d123a27685d46
# After MD5: 8b1537c4aea8c75d15fdd3bdc6c7a83a

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "8b1537c4aea8c75d15fdd3bdc6c7a83a" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "9321779517e04f4ba18d123a27685d46" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4R8EAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACf5QAAAOpY4w8Ah6D862QAoOPusvzrAACfAAAA6r7jDwCBoPzrDwBQ4/f//woAAJ/lAADqGuQPAHug/OsIABvlAJDlBCCg4wEQoONS8v7rCAAb5QCQCvT+69D7/+pSaW5raGFscwBSaW5raGFs' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=118045 obs=1 count=7 conv=notrunc # 0x1cd1d / 0x2cd1d > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=971708 obs=1 count=4 conv=notrunc # 0xed3bc / 0xfd3bc > 0x1f0400ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=975700 obs=1 count=105 conv=notrunc # 0xee354 / 0xfe354 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=975806 obs=1 count=19 conv=notrunc # 0xee3be / 0xfe3be > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=135 ibs=1 of=$TARGET seek=975826 obs=1 count=108 conv=notrunc # 0xee3d2 / 0xfe3d2 > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=243 ibs=1 of=$TARGET seek=975936 obs=1 count=27 conv=notrunc # 0xee440 / 0xfe440 > 0x00009fe5000000ea58e30f0087a0fceb6400a0e3eeb2fceb00009f
dd if=$PATCH_FILE skip=270 ibs=1 of=$TARGET seek=975964 obs=1 count=25 conv=notrunc # 0xee45c / 0xfe45c > 0x000000eabee30f0081a0fceb0f0050e3f7ffff0a00009fe500
dd if=$PATCH_FILE skip=295 ibs=1 of=$TARGET seek=975990 obs=1 count=15 conv=notrunc # 0xee476 / 0xfe476 > 0x00ea1ae40f007ba0fceb08001be500
dd if=$PATCH_FILE skip=310 ibs=1 of=$TARGET seek=976006 obs=1 count=19 conv=notrunc # 0xee486 / 0xfe486 > 0x90e50420a0e30110a0e352f2feeb08001be500
dd if=$PATCH_FILE skip=329 ibs=1 of=$TARGET seek=976026 obs=1 count=1 conv=notrunc # 0xee49a / 0xfe49a > 0x90
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=976032 obs=1 count=8 conv=notrunc # 0xee4a0 / 0xfe4a0 > 0x0af4feebd0fbffea
dd if=$PATCH_FILE skip=338 ibs=1 of=$TARGET seek=2794140 obs=1 count=16 conv=notrunc # 0x2aa29c / 0x2ba29c > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
