#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 2b7695b63c8587622b7c5bba5d0dec2e
# After MD5: 716229218804a960ed965617e496528e

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "716229218804a960ed965617e496528e" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "2b7695b63c8587622b7c5bba5d0dec2e" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'NTkA6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hscy11aS5waWQpIDI+IC9kZXYvbnVsbHJtIC1mIC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkAAAAn+UAAADqtNMVALZV++tk47qIAACf5QAAAOoa1BUAsFX76w8AUOP3//8KAACf5QAAAOp21BUAqlX76zAAG+UAAJDlBCDjARCg4520/uswABvlAACQBBCg44q2/uu5xv/qUmlua2hhbHMA' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1306560 obs=1 count=4 conv=notrunc # 0x13efc0 / 0x14efc0 > 0x353900ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1364912 obs=1 count=133 conv=notrunc # 0x14d3b0 / 0x15d3b0 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1365046 obs=1 count=39 conv=notrunc # 0x14d436 / 0x15d436 > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68
dd if=$PATCH_FILE skip=176 ibs=1 of=$TARGET seek=1365086 obs=1 count=23 conv=notrunc # 0x14d45e / 0x15d45e > 0x6c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=199 ibs=1 of=$TARGET seek=1365110 obs=1 count=36 conv=notrunc # 0x14d476 / 0x15d476 > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=235 ibs=1 of=$TARGET seek=1365148 obs=1 count=17 conv=notrunc # 0x14d49c / 0x15d49c > 0x00009fe5000000eab4d31500b655fbeb64
dd if=$PATCH_FILE skip=252 ibs=1 of=$TARGET seek=1365167 obs=1 count=3 conv=notrunc # 0x14d4af / 0x15d4af > 0xe3ba88
dd if=$PATCH_FILE skip=255 ibs=1 of=$TARGET seek=1365172 obs=1 count=50 conv=notrunc # 0x14d4b4 / 0x15d4b4 > 0x00009fe5000000ea1ad41500b055fbeb0f0050e3f7ffff0a00009fe5000000ea76d41500aa55fbeb30001be5000090e50420
dd if=$PATCH_FILE skip=305 ibs=1 of=$TARGET seek=1365223 obs=1 count=16 conv=notrunc # 0x14d4e7 / 0x15d4e7 > 0xe30110a0e39db4feeb30001be5000090
dd if=$PATCH_FILE skip=321 ibs=1 of=$TARGET seek=1365240 obs=1 count=12 conv=notrunc # 0x14d4f8 / 0x15d4f8 > 0x0410a0e38ab6feebb9c6ffea
dd if=$PATCH_FILE skip=333 ibs=1 of=$TARGET seek=3855112 obs=1 count=9 conv=notrunc # 0x3ad308 / 0x3bd308 > 0x52696e6b68616c7300

rm $PATCH_FILE
