#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 690354025e73d8b8e970d236b75f1b87
# After MD5: bb4c82de2278a30dead3414c2afb8a64

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "bb4c82de2278a30dead3414c2afb8a64" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "690354025e73d8b8e970d236b75f1b87" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'mggO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACfAAAA6jTmCADlQv7rZACg40VR/usAAJ/lAADqmuYIAN9C/usPUOP3//8KAACf5QD25ggA2UL+6zgAG+UAAJDlBCCg4wEQoONcNf/rOAAb5QCQ5QAQoONYNeto9//qUmlua2hhbA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=509100 obs=1 count=2 conv=notrunc # 0x7c4ac / 0x8c4ac > 0x9a08
dd if=$PATCH_FILE skip=2 ibs=1 of=$TARGET seek=517680 obs=1 count=105 conv=notrunc # 0x7e630 / 0x8e630 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=107 ibs=1 of=$TARGET seek=517786 obs=1 count=19 conv=notrunc # 0x7e69a / 0x8e69a > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=126 ibs=1 of=$TARGET seek=517806 obs=1 count=108 conv=notrunc # 0x7e6ae / 0x8e6ae > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=234 ibs=1 of=$TARGET seek=517916 obs=1 count=3 conv=notrunc # 0x7e71c / 0x8e71c > 0x00009f
dd if=$PATCH_FILE skip=237 ibs=1 of=$TARGET seek=517920 obs=1 count=25 conv=notrunc # 0x7e720 / 0x8e720 > 0x000000ea34e60800e542feeb6400a0e34551feeb00009fe500
dd if=$PATCH_FILE skip=262 ibs=1 of=$TARGET seek=517946 obs=1 count=11 conv=notrunc # 0x7e73a / 0x8e73a > 0x00ea9ae60800df42feeb0f
dd if=$PATCH_FILE skip=273 ibs=1 of=$TARGET seek=517958 obs=1 count=11 conv=notrunc # 0x7e746 / 0x8e746 > 0x50e3f7ffff0a00009fe500
dd if=$PATCH_FILE skip=284 ibs=1 of=$TARGET seek=517972 obs=1 count=33 conv=notrunc # 0x7e754 / 0x8e754 > 0xf6e60800d942feeb38001be5000090e50420a0e30110a0e35c35ffeb38001be500
dd if=$PATCH_FILE skip=317 ibs=1 of=$TARGET seek=518006 obs=1 count=8 conv=notrunc # 0x7e776 / 0x8e776 > 0x90e50010a0e35835
dd if=$PATCH_FILE skip=325 ibs=1 of=$TARGET seek=518015 obs=1 count=5 conv=notrunc # 0x7e77f / 0x8e77f > 0xeb68f7ffea
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1731836 obs=1 count=7 conv=notrunc # 0x1a6cfc / 0x1b6cfc > 0x52696e6b68616c

rm $PATCH_FILE
