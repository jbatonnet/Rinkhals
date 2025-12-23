#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 9eb5d42eca4339ddcfda3edf08c3e407
# After MD5: 1aab9cb312888a16afd3992d97f67256

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "1aab9cb312888a16afd3992d97f67256" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "9eb5d42eca4339ddcfda3edf08c3e407" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'VB4A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT46fh/xoAAJ/lAADqHH0SAP0V/OtkAKAl/OsAAJ/lAAAA6oJ9EgD3FQ8AUOP3//8KAAAAAADq3n0SAPEV/OsAG+UAAJDlBCCg4wEQoOORyv7rEAAb5QCQ5QQQoOM4zP7rjuH/6lJpbmtoYWxzAA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1115308 obs=1 count=4 conv=notrunc # 0x1104ac / 0x1204ac > 0x541e00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1146136 obs=1 count=133 conv=notrunc # 0x117d18 / 0x127d18 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1146270 obs=1 count=63 conv=notrunc # 0x117d9e / 0x127d9e > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1146334 obs=1 count=36 conv=notrunc # 0x117dde / 0x127dde > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1146372 obs=1 count=17 conv=notrunc # 0x117e04 / 0x127e04 > 0x0400a0e1030053e3a7e1ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1146390 obs=1 count=12 conv=notrunc # 0x117e16 / 0x127e16 > 0x00ea1c7d1200fd15fceb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1146404 obs=1 count=18 conv=notrunc # 0x117e24 / 0x127e24 > 0xa025fceb00009fe5000000ea827d1200f715
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1146424 obs=1 count=10 conv=notrunc # 0x117e38 / 0x127e38 > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1146436 obs=1 count=12 conv=notrunc # 0x117e44 / 0x127e44 > 0x000000eade7d1200f115fceb
dd if=$PATCH_FILE skip=305 ibs=1 of=$TARGET seek=1146449 obs=1 count=24 conv=notrunc # 0x117e51 / 0x127e51 > 0x001be5000090e50420a0e30110a0e391cafeeb10001be500
dd if=$PATCH_FILE skip=329 ibs=1 of=$TARGET seek=1146474 obs=1 count=14 conv=notrunc # 0x117e6a / 0x127e6a > 0x90e50410a0e338ccfeeb8ee1ffea
dd if=$PATCH_FILE skip=343 ibs=1 of=$TARGET seek=2799456 obs=1 count=9 conv=notrunc # 0x2ab760 / 0x2bb760 > 0x52696e6b68616c7300

rm $PATCH_FILE
