#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: dd49d388d7f9c8c7c35f21cd984bfe43
# After MD5: 5a96fa2d02386fecf2c6db0860138e35

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "5a96fa2d02386fecf2c6db0860138e35" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "dd49d388d7f9c8c7c35f21cd984bfe43" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4XAEAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACf5QAAAOp4LQ8A5dD862QAoOOZ5PzrAACfAAAA6t4tDwDf0PzrDwBQ4/f//woAn+UAAADqOi4PANnQ/OsIG+UAAJDlBCCg4wEQ41bm/ggAAJDlBBDjDuj+6377/+pSaW5raGFscwBSaW5raGFs' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=122313 obs=1 count=7 conv=notrunc # 0x1ddc9 / 0x2ddc9 > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=924824 obs=1 count=4 conv=notrunc # 0xe1c98 / 0xf1c98 > 0x700400ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=929140 obs=1 count=105 conv=notrunc # 0xe2d74 / 0xf2d74 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=929246 obs=1 count=19 conv=notrunc # 0xe2dde / 0xf2dde > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=135 ibs=1 of=$TARGET seek=929266 obs=1 count=108 conv=notrunc # 0xe2df2 / 0xf2df2 > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=243 ibs=1 of=$TARGET seek=929376 obs=1 count=27 conv=notrunc # 0xe2e60 / 0xf2e60 > 0x00009fe5000000ea782d0f00e5d0fceb6400a0e399e4fceb00009f
dd if=$PATCH_FILE skip=270 ibs=1 of=$TARGET seek=929404 obs=1 count=21 conv=notrunc # 0xe2e7c / 0xf2e7c > 0x000000eade2d0f00dfd0fceb0f0050e3f7ffff0a00
dd if=$PATCH_FILE skip=291 ibs=1 of=$TARGET seek=929426 obs=1 count=15 conv=notrunc # 0xe2e92 / 0xf2e92 > 0x9fe5000000ea3a2e0f00d9d0fceb08
dd if=$PATCH_FILE skip=306 ibs=1 of=$TARGET seek=929442 obs=1 count=12 conv=notrunc # 0xe2ea2 / 0xf2ea2 > 0x1be5000090e50420a0e30110
dd if=$PATCH_FILE skip=318 ibs=1 of=$TARGET seek=929455 obs=1 count=4 conv=notrunc # 0xe2eaf / 0xf2eaf > 0xe356e6fe
dd if=$PATCH_FILE skip=322 ibs=1 of=$TARGET seek=929460 obs=1 count=1 conv=notrunc # 0xe2eb4 / 0xf2eb4 > 0x08
dd if=$PATCH_FILE skip=323 ibs=1 of=$TARGET seek=929464 obs=1 count=6 conv=notrunc # 0xe2eb8 / 0xf2eb8 > 0x000090e50410
dd if=$PATCH_FILE skip=329 ibs=1 of=$TARGET seek=929471 obs=1 count=9 conv=notrunc # 0xe2ebf / 0xf2ebf > 0xe30ee8feeb7efbffea
dd if=$PATCH_FILE skip=338 ibs=1 of=$TARGET seek=2713904 obs=1 count=16 conv=notrunc # 0x296930 / 0x2a6930 > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
