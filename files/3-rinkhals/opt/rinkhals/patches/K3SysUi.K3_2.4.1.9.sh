#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 1f628e70311f52d934e851d232f66da3
# After MD5: 11aaee7010853180dc29ed4cb1d0c6ae

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "11aaee7010853180dc29ed4cb1d0c6ae" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "1f628e70311f52d934e851d232f66da3" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4WsEAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACfAAAA6vzcDgBS5PzrZACg4/j3/OsAAJ/lAAAA6mLdDgBM5PzrDwBQ4/f//woAAJ/lAAAA6r7dDgBG5PzrCAAb5QAAkOUEIOMBEKDjHer+6wgAG+UAkOUEEKDV6/7rg/v/6lJpbmtoYWxzAFJpbmtoYWw=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=121545 obs=1 count=7 conv=notrunc # 0x1dac9 / 0x2dac9 > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=904240 obs=1 count=4 conv=notrunc # 0xdcc30 / 0xecc30 > 0x6b0400ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=908536 obs=1 count=105 conv=notrunc # 0xddcf8 / 0xedcf8 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=908642 obs=1 count=19 conv=notrunc # 0xddd62 / 0xedd62 > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=135 ibs=1 of=$TARGET seek=908662 obs=1 count=108 conv=notrunc # 0xddd76 / 0xedd76 > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=243 ibs=1 of=$TARGET seek=908772 obs=1 count=3 conv=notrunc # 0xddde4 / 0xedde4 > 0x00009f
dd if=$PATCH_FILE skip=246 ibs=1 of=$TARGET seek=908776 obs=1 count=70 conv=notrunc # 0xddde8 / 0xedde8 > 0x000000eafcdc0e0052e4fceb6400a0e3f8f7fceb00009fe5000000ea62dd0e004ce4fceb0f0050e3f7ffff0a00009fe5000000eabedd0e0046e4fceb08001be5000090e50420
dd if=$PATCH_FILE skip=316 ibs=1 of=$TARGET seek=908847 obs=1 count=13 conv=notrunc # 0xdde2f / 0xede2f > 0xe30110a0e31deafeeb08001be5
dd if=$PATCH_FILE skip=329 ibs=1 of=$TARGET seek=908861 obs=1 count=6 conv=notrunc # 0xdde3d / 0xede3d > 0x0090e50410a0
dd if=$PATCH_FILE skip=335 ibs=1 of=$TARGET seek=908868 obs=1 count=8 conv=notrunc # 0xdde44 / 0xede44 > 0xd5ebfeeb83fbffea
dd if=$PATCH_FILE skip=343 ibs=1 of=$TARGET seek=2673680 obs=1 count=16 conv=notrunc # 0x28cc10 / 0x29cc10 > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
