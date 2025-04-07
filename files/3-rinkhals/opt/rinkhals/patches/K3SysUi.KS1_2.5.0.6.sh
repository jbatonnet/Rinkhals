#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: f77300db15a6990066a0268de66338fa
# After MD5: cdd6f39e658f2d3e06aa3cc901d2f48e

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "cdd6f39e658f2d3e06aa3cc901d2f48e" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "f77300db15a6990066a0268de66338fa" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'ZR0A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT45bi/xoAAJ/lAADqyJIRAFtI/OtkAA1d/OsAAJ/lAAAA6i6TEQBVSA8AUOP3//8KAAAAAADqipMRAE9I/OsQABvlAACQ5QQgoOMBEKDjPfX+6xAAG+UAkOUEEKDj0vb+633i/+pSaW5raGFscwA=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1056276 obs=1 count=4 conv=notrunc # 0x101e14 / 0x111e14 > 0x651d00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1086148 obs=1 count=133 conv=notrunc # 0x1092c4 / 0x1192c4 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1086282 obs=1 count=63 conv=notrunc # 0x10934a / 0x11934a > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1086346 obs=1 count=36 conv=notrunc # 0x10938a / 0x11938a > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1086384 obs=1 count=17 conv=notrunc # 0x1093b0 / 0x1193b0 > 0x0400a0e1030053e396e2ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1086402 obs=1 count=12 conv=notrunc # 0x1093c2 / 0x1193c2 > 0x00eac89211005b48fceb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1086416 obs=1 count=18 conv=notrunc # 0x1093d0 / 0x1193d0 > 0x0d5dfceb00009fe5000000ea2e9311005548
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1086436 obs=1 count=10 conv=notrunc # 0x1093e4 / 0x1193e4 > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1086448 obs=1 count=37 conv=notrunc # 0x1093f0 / 0x1193f0 > 0x000000ea8a9311004f48fceb10001be5000090e50420a0e30110a0e33df5feeb10001be500
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1086486 obs=1 count=14 conv=notrunc # 0x109416 / 0x119416 > 0x90e50410a0e3d2f6feeb7de2ffea
dd if=$PATCH_FILE skip=344 ibs=1 of=$TARGET seek=2689272 obs=1 count=9 conv=notrunc # 0x2908f8 / 0x2a08f8 > 0x52696e6b68616c7300

rm $PATCH_FILE
