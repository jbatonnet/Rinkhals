#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: fc674464a870227bf4c860f2086863de
# After MD5: 807d278614cce561376af31c5ce1365b

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "807d278614cce561376af31c5ce1365b" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "fc674464a870227bf4c860f2086863de" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'VB4A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT46fh/xoAAJ/lAADq/HwSAAUW/OtkAKgl/OsAAJ/lAAAA6mJ9EgD/FQ8AUOP3//8KAAAAAADqvn0SAPkV/OsQABvlAACQ5QQgoOMBEKDjkcr+6xAAG+UAkOUEEKDjOMz+647h/+pSaW5raGFscwA=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1115276 obs=1 count=4 conv=notrunc # 0x11048c / 0x12048c > 0x541e00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1146104 obs=1 count=133 conv=notrunc # 0x117cf8 / 0x127cf8 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1146238 obs=1 count=63 conv=notrunc # 0x117d7e / 0x127d7e > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1146302 obs=1 count=36 conv=notrunc # 0x117dbe / 0x127dbe > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1146340 obs=1 count=17 conv=notrunc # 0x117de4 / 0x127de4 > 0x0400a0e1030053e3a7e1ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1146358 obs=1 count=12 conv=notrunc # 0x117df6 / 0x127df6 > 0x00eafc7c12000516fceb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1146372 obs=1 count=18 conv=notrunc # 0x117e04 / 0x127e04 > 0xa825fceb00009fe5000000ea627d1200ff15
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1146392 obs=1 count=10 conv=notrunc # 0x117e18 / 0x127e18 > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1146404 obs=1 count=37 conv=notrunc # 0x117e24 / 0x127e24 > 0x000000eabe7d1200f915fceb10001be5000090e50420a0e30110a0e391cafeeb10001be500
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1146442 obs=1 count=14 conv=notrunc # 0x117e4a / 0x127e4a > 0x90e50410a0e338ccfeeb8ee1ffea
dd if=$PATCH_FILE skip=344 ibs=1 of=$TARGET seek=2799440 obs=1 count=9 conv=notrunc # 0x2ab750 / 0x2bb750 > 0x52696e6b68616c7300

rm $PATCH_FILE
