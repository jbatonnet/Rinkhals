#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: f8f1bc1dd2af13201f4f58ee4f79ed66
# After MD5: cd668e1169951d1908be0cb7265524dc

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "cd668e1169951d1908be0cb7265524dc" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "f8f1bc1dd2af13201f4f58ee4f79ed66" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'LgsO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJmVjaG8gJCE+IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkAHRpbWVvdXQgLXQgMiBzdHJhY2UgLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAn+UAAOqQyAkAo//962QAoONOHv7rAACf5QDq9sgJAJ3//esPAFDj9///CgCf5QAA6lLJCQCX//3rBQCg4QFDDf8FAKDhABBADf/rw/T/6lJpbmtoYWw=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=564408 obs=1 count=2 conv=notrunc # 0x89cb8 / 0x99cb8 > 0x2e0b
dd if=$PATCH_FILE skip=2 ibs=1 of=$TARGET seek=575628 obs=1 count=65 conv=notrunc # 0x8c88c / 0x9c88c > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026
dd if=$PATCH_FILE skip=67 ibs=1 of=$TARGET seek=575694 obs=1 count=7 conv=notrunc # 0x8c8ce / 0x9c8ce > 0x6563686f202421
dd if=$PATCH_FILE skip=74 ibs=1 of=$TARGET seek=575702 obs=1 count=159 conv=notrunc # 0x8c8d6 / 0x9c8d6 > 0x3e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=233 ibs=1 of=$TARGET seek=575864 obs=1 count=1 conv=notrunc # 0x8c978 / 0x9c978 > 0x00
dd if=$PATCH_FILE skip=234 ibs=1 of=$TARGET seek=575866 obs=1 count=3 conv=notrunc # 0x8c97a / 0x9c97a > 0x9fe500
dd if=$PATCH_FILE skip=237 ibs=1 of=$TARGET seek=575870 obs=1 count=22 conv=notrunc # 0x8c97e / 0x9c97e > 0x00ea90c80900a3fffdeb6400a0e34e1efeeb00009fe5
dd if=$PATCH_FILE skip=259 ibs=1 of=$TARGET seek=575894 obs=1 count=19 conv=notrunc # 0x8c996 / 0x9c996 > 0x00eaf6c809009dfffdeb0f0050e3f7ffff0a00
dd if=$PATCH_FILE skip=278 ibs=1 of=$TARGET seek=575914 obs=1 count=3 conv=notrunc # 0x8c9aa / 0x9c9aa > 0x9fe500
dd if=$PATCH_FILE skip=281 ibs=1 of=$TARGET seek=575918 obs=1 count=14 conv=notrunc # 0x8c9ae / 0x9c9ae > 0x00ea52c9090097fffdeb0500a0e1
dd if=$PATCH_FILE skip=295 ibs=1 of=$TARGET seek=575936 obs=1 count=1 conv=notrunc # 0x8c9c0 / 0x9c9c0 > 0x01
dd if=$PATCH_FILE skip=296 ibs=1 of=$TARGET seek=575940 obs=1 count=3 conv=notrunc # 0x8c9c4 / 0x9c9c4 > 0x430dff
dd if=$PATCH_FILE skip=299 ibs=1 of=$TARGET seek=575944 obs=1 count=6 conv=notrunc # 0x8c9c8 / 0x9c9c8 > 0x0500a0e10010
dd if=$PATCH_FILE skip=305 ibs=1 of=$TARGET seek=575952 obs=1 count=8 conv=notrunc # 0x8c9d0 / 0x9c9d0 > 0x400dffebc3f4ffea
dd if=$PATCH_FILE skip=313 ibs=1 of=$TARGET seek=1049948 obs=1 count=7 conv=notrunc # 0x10055c / 0x11055c > 0x52696e6b68616c

rm $PATCH_FILE
