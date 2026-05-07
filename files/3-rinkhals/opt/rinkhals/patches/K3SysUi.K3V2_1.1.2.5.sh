#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 0c94572665312b25074ccd9ad54cf27c
# After MD5: b506802c03830b46e2eee674116c4bbb

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "b506802c03830b46e2eee674116c4bbb" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "0c94572665312b25074ccd9ad54cf27c" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4XkEAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACf5QAAAOrIhxAA3YX862QAoOM2u/zrAACfAAAA6i6IEADXhfzrDwBQ4/f//woAn+UAAADqiogQANGF/OsIG+UAAJDlBCCg4wEQ46HU/ggAAJDlBBDj0db+63r7/+pSaW5raGFscwBSaW5raGFs' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=168881 obs=1 count=7 conv=notrunc # 0x293b1 / 0x393b1 > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=1013444 obs=1 count=4 conv=notrunc # 0xf76c4 / 0x1076c4 > 0x790400ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=1017796 obs=1 count=105 conv=notrunc # 0xf87c4 / 0x1087c4 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=1017902 obs=1 count=19 conv=notrunc # 0xf882e / 0x10882e > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=135 ibs=1 of=$TARGET seek=1017922 obs=1 count=108 conv=notrunc # 0xf8842 / 0x108842 > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=243 ibs=1 of=$TARGET seek=1018032 obs=1 count=27 conv=notrunc # 0xf88b0 / 0x1088b0 > 0x00009fe5000000eac8871000dd85fceb6400a0e336bbfceb00009f
dd if=$PATCH_FILE skip=270 ibs=1 of=$TARGET seek=1018060 obs=1 count=21 conv=notrunc # 0xf88cc / 0x1088cc > 0x000000ea2e881000d785fceb0f0050e3f7ffff0a00
dd if=$PATCH_FILE skip=291 ibs=1 of=$TARGET seek=1018082 obs=1 count=15 conv=notrunc # 0xf88e2 / 0x1088e2 > 0x9fe5000000ea8a881000d185fceb08
dd if=$PATCH_FILE skip=306 ibs=1 of=$TARGET seek=1018098 obs=1 count=12 conv=notrunc # 0xf88f2 / 0x1088f2 > 0x1be5000090e50420a0e30110
dd if=$PATCH_FILE skip=318 ibs=1 of=$TARGET seek=1018111 obs=1 count=4 conv=notrunc # 0xf88ff / 0x1088ff > 0xe3a1d4fe
dd if=$PATCH_FILE skip=322 ibs=1 of=$TARGET seek=1018116 obs=1 count=1 conv=notrunc # 0xf8904 / 0x108904 > 0x08
dd if=$PATCH_FILE skip=323 ibs=1 of=$TARGET seek=1018120 obs=1 count=6 conv=notrunc # 0xf8908 / 0x108908 > 0x000090e50410
dd if=$PATCH_FILE skip=329 ibs=1 of=$TARGET seek=1018127 obs=1 count=9 conv=notrunc # 0xf890f / 0x10890f > 0xe3d1d6feeb7afbffea
dd if=$PATCH_FILE skip=338 ibs=1 of=$TARGET seek=3052784 obs=1 count=16 conv=notrunc # 0x2e94f0 / 0x2f94f0 > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
