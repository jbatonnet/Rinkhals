#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 8c8618e7aea8724be76ebfcab9f2d166
# After MD5: 446add7e556205bb7aaad8c1b022fc47

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "446add7e556205bb7aaad8c1b022fc47" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "8c8618e7aea8724be76ebfcab9f2d166" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'wh0A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT4zni/xoAAJ/lAADqAKwRADxC/OtkAPFW/OsAAJ/lAAAA6masEQA2Qg8AUOP3//8KAAAAAADqwqwRADBC/OsQABvlAACQ5QQgoOMBEKDj8vL+6xAAG+UAkOUEEKDjmfT+6yDi/+pSaW5raGFscwA=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1062360 obs=1 count=4 conv=notrunc # 0x1035d8 / 0x1135d8 > 0xc21d00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1092604 obs=1 count=133 conv=notrunc # 0x10abfc / 0x11abfc > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1092738 obs=1 count=63 conv=notrunc # 0x10ac82 / 0x11ac82 > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1092802 obs=1 count=36 conv=notrunc # 0x10acc2 / 0x11acc2 > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1092840 obs=1 count=17 conv=notrunc # 0x10ace8 / 0x11ace8 > 0x0400a0e1030053e339e2ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1092858 obs=1 count=12 conv=notrunc # 0x10acfa / 0x11acfa > 0x00ea00ac11003c42fceb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1092872 obs=1 count=18 conv=notrunc # 0x10ad08 / 0x11ad08 > 0xf156fceb00009fe5000000ea66ac11003642
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1092892 obs=1 count=10 conv=notrunc # 0x10ad1c / 0x11ad1c > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1092904 obs=1 count=37 conv=notrunc # 0x10ad28 / 0x11ad28 > 0x000000eac2ac11003042fceb10001be5000090e50420a0e30110a0e3f2f2feeb10001be500
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1092942 obs=1 count=14 conv=notrunc # 0x10ad4e / 0x11ad4e > 0x90e50410a0e399f4feeb20e2ffea
dd if=$PATCH_FILE skip=344 ibs=1 of=$TARGET seek=2706864 obs=1 count=9 conv=notrunc # 0x294db0 / 0x2a4db0 > 0x52696e6b68616c7300

rm $PATCH_FILE
