#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: d316681f09f4bdc9c6427771ff1ba8d9
# After MD5: 2e53c775c1c485623188a2e640c9db42

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "2e53c775c1c485623188a2e640c9db42" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "d316681f09f4bdc9c6427771ff1ba8d9" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'wh0A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT4zni/xoAAJ/lAADqAK8RAHxB/OtkADFW/OsAAJ/lAAAA6mavEQB2QQ8AUOP3//8KAAAAAADqwq8RAHBB/OsQABvlAACQ5QQgoOMBEKDjMvL+6xAAG+UAkOUEEKDj2fP+6yDi/+pSaW5raGFscwA=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1063128 obs=1 count=4 conv=notrunc # 0x1038d8 / 0x1138d8 > 0xc21d00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1093372 obs=1 count=133 conv=notrunc # 0x10aefc / 0x11aefc > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1093506 obs=1 count=63 conv=notrunc # 0x10af82 / 0x11af82 > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1093570 obs=1 count=36 conv=notrunc # 0x10afc2 / 0x11afc2 > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1093608 obs=1 count=17 conv=notrunc # 0x10afe8 / 0x11afe8 > 0x0400a0e1030053e339e2ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1093626 obs=1 count=12 conv=notrunc # 0x10affa / 0x11affa > 0x00ea00af11007c41fceb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1093640 obs=1 count=18 conv=notrunc # 0x10b008 / 0x11b008 > 0x3156fceb00009fe5000000ea66af11007641
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1093660 obs=1 count=10 conv=notrunc # 0x10b01c / 0x11b01c > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1093672 obs=1 count=37 conv=notrunc # 0x10b028 / 0x11b028 > 0x000000eac2af11007041fceb10001be5000090e50420a0e30110a0e332f2feeb10001be500
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1093710 obs=1 count=14 conv=notrunc # 0x10b04e / 0x11b04e > 0x90e50410a0e3d9f3feeb20e2ffea
dd if=$PATCH_FILE skip=344 ibs=1 of=$TARGET seek=2707724 obs=1 count=9 conv=notrunc # 0x29510c / 0x2a510c > 0x52696e6b68616c7300

rm $PATCH_FILE
