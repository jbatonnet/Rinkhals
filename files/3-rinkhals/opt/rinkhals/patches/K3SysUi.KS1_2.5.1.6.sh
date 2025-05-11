#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 37aa475fad1a7f41c44d20ad01a3738c
# After MD5: 3da669fd4105fed147a489732c6295ad

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "3da669fd4105fed147a489732c6295ad" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "37aa475fad1a7f41c44d20ad01a3738c" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'Tx0A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT46zi/xoAAJ/lAADqbKYRAKFD/OtkAFZY/OsAAJ/lAAAA6tKmEQCbQw8AUOP3//8KAAAAAADqLqcRAJVD/OsQABvlAACQ5QQgoOMBEKDjf/T+6xAAG+UAkOUEEKDjJvb+65Pi/+pSaW5raGFscwA=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1061392 obs=1 count=4 conv=notrunc # 0x103210 / 0x113210 > 0x4f1d00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1091176 obs=1 count=133 conv=notrunc # 0x10a668 / 0x11a668 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1091310 obs=1 count=63 conv=notrunc # 0x10a6ee / 0x11a6ee > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1091374 obs=1 count=36 conv=notrunc # 0x10a72e / 0x11a72e > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1091412 obs=1 count=17 conv=notrunc # 0x10a754 / 0x11a754 > 0x0400a0e1030053e3ace2ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1091430 obs=1 count=12 conv=notrunc # 0x10a766 / 0x11a766 > 0x00ea6ca61100a143fceb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1091444 obs=1 count=18 conv=notrunc # 0x10a774 / 0x11a774 > 0x5658fceb00009fe5000000ead2a611009b43
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1091464 obs=1 count=10 conv=notrunc # 0x10a788 / 0x11a788 > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1091476 obs=1 count=37 conv=notrunc # 0x10a794 / 0x11a794 > 0x000000ea2ea711009543fceb10001be5000090e50420a0e30110a0e37ff4feeb10001be500
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1091514 obs=1 count=14 conv=notrunc # 0x10a7ba / 0x11a7ba > 0x90e50410a0e326f6feeb93e2ffea
dd if=$PATCH_FILE skip=344 ibs=1 of=$TARGET seek=2702216 obs=1 count=9 conv=notrunc # 0x293b88 / 0x2a3b88 > 0x52696e6b68616c7300

rm $PATCH_FILE
