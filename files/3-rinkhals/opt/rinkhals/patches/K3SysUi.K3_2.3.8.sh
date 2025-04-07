#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: d9bb6a0bb749151e326b8fbb717267a1
# After MD5: b8f5e73dc7a70aa64d8061e25b55c2da

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "b8f5e73dc7a70aa64d8061e25b55c2da" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "d9bb6a0bb749151e326b8fbb717267a1" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4ewDAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2ggJiBlY2hvICQhID4gL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWR0aW1lb3V0IC10IDIgc3RyYWNlLXFxcSAtZSB0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGwAcm0gLWYgL3RtcC9yaW5raGFscy9yaW5raGFscy11aS5waWQAAACf5QAAAOrgrA8ADq7862QAoON0wPzrAACfAAAA6katDwAIrvzrDwBQ4/f//woAn+UAAADqoq0PAAKu/OsIG+UAAJDlBCCg4wEQ4xL4/ggAAJDluPn+6wP8/+pSaW5raGFscwBSaW5raGFs' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=117949 obs=1 count=7 conv=notrunc # 0x1ccbd / 0x2ccbd > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=957968 obs=1 count=4 conv=notrunc # 0xe9e10 / 0xf9e10 > 0xec0300ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=961756 obs=1 count=105 conv=notrunc # 0xeacdc / 0xfacdc > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e706964
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=961862 obs=1 count=19 conv=notrunc # 0xead46 / 0xfad46 > 0x74696d656f7574202d74203220737472616365
dd if=$PATCH_FILE skip=135 ibs=1 of=$TARGET seek=961882 obs=1 count=108 conv=notrunc # 0xead5a / 0xfad5a > 0x2d717171202d652074726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c00726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=243 ibs=1 of=$TARGET seek=961992 obs=1 count=27 conv=notrunc # 0xeadc8 / 0xfadc8 > 0x00009fe5000000eae0ac0f000eaefceb6400a0e374c0fceb00009f
dd if=$PATCH_FILE skip=270 ibs=1 of=$TARGET seek=962020 obs=1 count=21 conv=notrunc # 0xeade4 / 0xfade4 > 0x000000ea46ad0f0008aefceb0f0050e3f7ffff0a00
dd if=$PATCH_FILE skip=291 ibs=1 of=$TARGET seek=962042 obs=1 count=15 conv=notrunc # 0xeadfa / 0xfadfa > 0x9fe5000000eaa2ad0f0002aefceb08
dd if=$PATCH_FILE skip=306 ibs=1 of=$TARGET seek=962058 obs=1 count=12 conv=notrunc # 0xeae0a / 0xfae0a > 0x1be5000090e50420a0e30110
dd if=$PATCH_FILE skip=318 ibs=1 of=$TARGET seek=962071 obs=1 count=4 conv=notrunc # 0xeae17 / 0xfae17 > 0xe312f8fe
dd if=$PATCH_FILE skip=322 ibs=1 of=$TARGET seek=962076 obs=1 count=1 conv=notrunc # 0xeae1c / 0xfae1c > 0x08
dd if=$PATCH_FILE skip=323 ibs=1 of=$TARGET seek=962080 obs=1 count=4 conv=notrunc # 0xeae20 / 0xfae20 > 0x000090e5
dd if=$PATCH_FILE skip=327 ibs=1 of=$TARGET seek=962088 obs=1 count=8 conv=notrunc # 0xeae28 / 0xfae28 > 0xb8f9feeb03fcffea
dd if=$PATCH_FILE skip=335 ibs=1 of=$TARGET seek=2750976 obs=1 count=16 conv=notrunc # 0x29fa00 / 0x2afa00 > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
