#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: e561df478a385b6cd7fa7f21899c237d
# After MD5: 14b59a0113d16b02576c6e611631f2b2

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "14b59a0113d16b02576c6e611631f2b2" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "e561df478a385b6cd7fa7f21899c237d" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4XkEAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACf5QAAAOrwhxAA04X862QAoOMsu/zrAACfAAAA6laIEADNhfzrDwBQ4/f//woAn+UAAADqsogQAMeF/OsIG+UAAJDlBCCg4wEQ45fU/ggAAJDlBBDjx9b+63r7/+pSaW5raGFscwBSaW5raGFs' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=168881 obs=1 count=7 conv=notrunc # 0x293b1 / 0x393b1 > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=1013484 obs=1 count=4 conv=notrunc # 0xf76ec / 0x1076ec > 0x790400ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=1017836 obs=1 count=105 conv=notrunc # 0xf87ec / 0x1087ec > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=1017942 obs=1 count=19 conv=notrunc # 0xf8856 / 0x108856 > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=135 ibs=1 of=$TARGET seek=1017962 obs=1 count=108 conv=notrunc # 0xf886a / 0x10886a > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=243 ibs=1 of=$TARGET seek=1018072 obs=1 count=27 conv=notrunc # 0xf88d8 / 0x1088d8 > 0x00009fe5000000eaf0871000d385fceb6400a0e32cbbfceb00009f
dd if=$PATCH_FILE skip=270 ibs=1 of=$TARGET seek=1018100 obs=1 count=21 conv=notrunc # 0xf88f4 / 0x1088f4 > 0x000000ea56881000cd85fceb0f0050e3f7ffff0a00
dd if=$PATCH_FILE skip=291 ibs=1 of=$TARGET seek=1018122 obs=1 count=15 conv=notrunc # 0xf890a / 0x10890a > 0x9fe5000000eab2881000c785fceb08
dd if=$PATCH_FILE skip=306 ibs=1 of=$TARGET seek=1018138 obs=1 count=12 conv=notrunc # 0xf891a / 0x10891a > 0x1be5000090e50420a0e30110
dd if=$PATCH_FILE skip=318 ibs=1 of=$TARGET seek=1018151 obs=1 count=4 conv=notrunc # 0xf8927 / 0x108927 > 0xe397d4fe
dd if=$PATCH_FILE skip=322 ibs=1 of=$TARGET seek=1018156 obs=1 count=1 conv=notrunc # 0xf892c / 0x10892c > 0x08
dd if=$PATCH_FILE skip=323 ibs=1 of=$TARGET seek=1018160 obs=1 count=6 conv=notrunc # 0xf8930 / 0x108930 > 0x000090e50410
dd if=$PATCH_FILE skip=329 ibs=1 of=$TARGET seek=1018167 obs=1 count=9 conv=notrunc # 0xf8937 / 0x108937 > 0xe3c7d6feeb7afbffea
dd if=$PATCH_FILE skip=338 ibs=1 of=$TARGET seek=3052968 obs=1 count=16 conv=notrunc # 0x2e95a8 / 0x2f95a8 > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
