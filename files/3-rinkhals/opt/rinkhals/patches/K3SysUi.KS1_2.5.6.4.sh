#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: b7d4fb56942f64b2b25f5f4d29e82923
# After MD5: 92c3a1db9d65016782593fe498fbcd6b

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "92c3a1db9d65016782593fe498fbcd6b" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "b7d4fb56942f64b2b25f5f4d29e82923" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'nDYA6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT41/J/xoAAJ/lAADqZPcSADT4++tkAOoH/OsAAJ/lAAAA6sr3EgAu+PsPAFDj9///CgAAAAAA6ib4EgAo+PvrEAAb5QAAkOUEIKDjARCg466x/usQABvlAJDlBBCg44yz/utGyf/qUmlua2hhbHMA' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1121748 obs=1 count=4 conv=notrunc # 0x111dd4 / 0x121dd4 > 0x9c3600ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1177440 obs=1 count=133 conv=notrunc # 0x11f760 / 0x12f760 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1177574 obs=1 count=63 conv=notrunc # 0x11f7e6 / 0x12f7e6 > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1177638 obs=1 count=36 conv=notrunc # 0x11f826 / 0x12f826 > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1177676 obs=1 count=17 conv=notrunc # 0x11f84c / 0x12f84c > 0x0400a0e1030053e35fc9ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1177694 obs=1 count=12 conv=notrunc # 0x11f85e / 0x12f85e > 0x00ea64f7120034f8fbeb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1177708 obs=1 count=19 conv=notrunc # 0x11f86c / 0x12f86c > 0xea07fceb00009fe5000000eacaf712002ef8fb
dd if=$PATCH_FILE skip=284 ibs=1 of=$TARGET seek=1177728 obs=1 count=10 conv=notrunc # 0x11f880 / 0x12f880 > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=294 ibs=1 of=$TARGET seek=1177740 obs=1 count=37 conv=notrunc # 0x11f88c / 0x12f88c > 0x000000ea26f8120028f8fbeb10001be5000090e50420a0e30110a0e3aeb1feeb10001be500
dd if=$PATCH_FILE skip=331 ibs=1 of=$TARGET seek=1177778 obs=1 count=14 conv=notrunc # 0x11f8b2 / 0x12f8b2 > 0x90e50410a0e38cb3feeb46c9ffea
dd if=$PATCH_FILE skip=345 ibs=1 of=$TARGET seek=2846544 obs=1 count=9 conv=notrunc # 0x2b6f50 / 0x2c6f50 > 0x52696e6b68616c7300

rm $PATCH_FILE
