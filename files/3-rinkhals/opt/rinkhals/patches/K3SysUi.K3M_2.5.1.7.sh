#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: a922d283682f2d9cc78bf70fd32b2b8d
# After MD5: b8f2b4595e5514b6de50f90da660d6a8

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "b8f2b4595e5514b6de50f90da660d6a8" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "a922d283682f2d9cc78bf70fd32b2b8d" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4XQEAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACfAAAA6khGEACQk/zrZACg4+LI/OsAAJ/lAAAA6q5GEACKk/zrDwBQ4/f//woAAJ/lAAAA6gpHEACEk/zrCAAb5QAAkOUEIOMBEKDjt9f+6wgAG+UAkOUEEKB42f7re/v/6lJpbmtoYWxzAFJpbmtoYWw=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=166113 obs=1 count=7 conv=notrunc # 0x288e1 / 0x388e1 > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=996696 obs=1 count=4 conv=notrunc # 0xf3558 / 0x103558 > 0x740400ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=1001028 obs=1 count=105 conv=notrunc # 0xf4644 / 0x104644 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=1001134 obs=1 count=19 conv=notrunc # 0xf46ae / 0x1046ae > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=135 ibs=1 of=$TARGET seek=1001154 obs=1 count=108 conv=notrunc # 0xf46c2 / 0x1046c2 > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=243 ibs=1 of=$TARGET seek=1001264 obs=1 count=3 conv=notrunc # 0xf4730 / 0x104730 > 0x00009f
dd if=$PATCH_FILE skip=246 ibs=1 of=$TARGET seek=1001268 obs=1 count=70 conv=notrunc # 0xf4734 / 0x104734 > 0x000000ea484610009093fceb6400a0e3e2c8fceb00009fe5000000eaae4610008a93fceb0f0050e3f7ffff0a00009fe5000000ea0a4710008493fceb08001be5000090e50420
dd if=$PATCH_FILE skip=316 ibs=1 of=$TARGET seek=1001339 obs=1 count=13 conv=notrunc # 0xf477b / 0x10477b > 0xe30110a0e3b7d7feeb08001be5
dd if=$PATCH_FILE skip=329 ibs=1 of=$TARGET seek=1001353 obs=1 count=6 conv=notrunc # 0xf4789 / 0x104789 > 0x0090e50410a0
dd if=$PATCH_FILE skip=335 ibs=1 of=$TARGET seek=1001360 obs=1 count=8 conv=notrunc # 0xf4790 / 0x104790 > 0x78d9feeb7bfbffea
dd if=$PATCH_FILE skip=343 ibs=1 of=$TARGET seek=3007848 obs=1 count=16 conv=notrunc # 0x2de568 / 0x2ee568 > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
