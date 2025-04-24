#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 397efd14feb5ce9d7787320ea542c9e6
# After MD5: cb4e8e98bb074a440b487545b413cc98

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "cb4e8e98bb074a440b487545b413cc98" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "397efd14feb5ce9d7787320ea542c9e6" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4ewDAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACf5QAAAOrkvQ8A5Kn862QAoONLvPzrAACfAAAA6kq+DwDeqfzrDwBQ4/f//woAn+UAAADqpr4PANip/OsIG+UAAJDlBCCg4wEQ4//3/ggAAJDlBBDjrvn+6wP8/+pSaW5raGFscwBSaW5raGFs' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=118045 obs=1 count=7 conv=notrunc # 0x1cd1d / 0x2cd1d > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=962324 obs=1 count=4 conv=notrunc # 0xeaf14 / 0xfaf14 > 0xec0300ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=966112 obs=1 count=105 conv=notrunc # 0xebde0 / 0xfbde0 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=966218 obs=1 count=19 conv=notrunc # 0xebe4a / 0xfbe4a > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=135 ibs=1 of=$TARGET seek=966238 obs=1 count=108 conv=notrunc # 0xebe5e / 0xfbe5e > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=243 ibs=1 of=$TARGET seek=966348 obs=1 count=27 conv=notrunc # 0xebecc / 0xfbecc > 0x00009fe5000000eae4bd0f00e4a9fceb6400a0e34bbcfceb00009f
dd if=$PATCH_FILE skip=270 ibs=1 of=$TARGET seek=966376 obs=1 count=21 conv=notrunc # 0xebee8 / 0xfbee8 > 0x000000ea4abe0f00dea9fceb0f0050e3f7ffff0a00
dd if=$PATCH_FILE skip=291 ibs=1 of=$TARGET seek=966398 obs=1 count=15 conv=notrunc # 0xebefe / 0xfbefe > 0x9fe5000000eaa6be0f00d8a9fceb08
dd if=$PATCH_FILE skip=306 ibs=1 of=$TARGET seek=966414 obs=1 count=12 conv=notrunc # 0xebf0e / 0xfbf0e > 0x1be5000090e50420a0e30110
dd if=$PATCH_FILE skip=318 ibs=1 of=$TARGET seek=966427 obs=1 count=4 conv=notrunc # 0xebf1b / 0xfbf1b > 0xe3fff7fe
dd if=$PATCH_FILE skip=322 ibs=1 of=$TARGET seek=966432 obs=1 count=1 conv=notrunc # 0xebf20 / 0xfbf20 > 0x08
dd if=$PATCH_FILE skip=323 ibs=1 of=$TARGET seek=966436 obs=1 count=6 conv=notrunc # 0xebf24 / 0xfbf24 > 0x000090e50410
dd if=$PATCH_FILE skip=329 ibs=1 of=$TARGET seek=966443 obs=1 count=9 conv=notrunc # 0xebf2b / 0xfbf2b > 0xe3aef9feeb03fcffea
dd if=$PATCH_FILE skip=338 ibs=1 of=$TARGET seek=2782252 obs=1 count=16 conv=notrunc # 0x2a742c / 0x2b742c > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
