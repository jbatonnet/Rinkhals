#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 974d1ef2afa63cb8944079644f3cd8c0
# After MD5: ed105efbb9812ab3ffa7939b19d8578e

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "ed105efbb9812ab3ffa7939b19d8578e" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "974d1ef2afa63cb8944079644f3cd8c0" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'Dx4A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT4+zh/xoAAJ/lAADq6GsSAMwZ/OtkAG0p/OsAAJ/lAAAA6k5sEgDGGQ8AUOP3//8KAAAAAADqqmwSAMAZ/OsQABvlAACQ5QQgoOMBEKDjnsz+6xAAG+UAkOUEEKDjRc7+69Ph/+pSaW5raGFscwA=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1111180 obs=1 count=4 conv=notrunc # 0x10f48c / 0x11f48c > 0x0f1e00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1141732 obs=1 count=133 conv=notrunc # 0x116be4 / 0x126be4 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1141866 obs=1 count=63 conv=notrunc # 0x116c6a / 0x126c6a > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1141930 obs=1 count=36 conv=notrunc # 0x116caa / 0x126caa > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1141968 obs=1 count=17 conv=notrunc # 0x116cd0 / 0x126cd0 > 0x0400a0e1030053e3ece1ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1141986 obs=1 count=12 conv=notrunc # 0x116ce2 / 0x126ce2 > 0x00eae86b1200cc19fceb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1142000 obs=1 count=18 conv=notrunc # 0x116cf0 / 0x126cf0 > 0x6d29fceb00009fe5000000ea4e6c1200c619
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1142020 obs=1 count=10 conv=notrunc # 0x116d04 / 0x126d04 > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1142032 obs=1 count=37 conv=notrunc # 0x116d10 / 0x126d10 > 0x000000eaaa6c1200c019fceb10001be5000090e50420a0e30110a0e39eccfeeb10001be500
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1142070 obs=1 count=14 conv=notrunc # 0x116d36 / 0x126d36 > 0x90e50410a0e345cefeebd3e1ffea
dd if=$PATCH_FILE skip=344 ibs=1 of=$TARGET seek=2791084 obs=1 count=9 conv=notrunc # 0x2a96ac / 0x2b96ac > 0x52696e6b68616c7300

rm $PATCH_FILE
