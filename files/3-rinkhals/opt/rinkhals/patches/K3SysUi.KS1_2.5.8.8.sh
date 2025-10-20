#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 9d2ff7d2f92c10f709efb3f0003987da
# After MD5: a055e33a167a4a208831e5a320fc9788

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "a055e33a167a4a208831e5a320fc9788" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "9d2ff7d2f92c10f709efb3f0003987da" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo '2jYA6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT4yHJ/xoAAJ/lAADq1IoTAJfZ++tkAGrq++sAAJ/lAAAA6jqLEwCR2Q8AUOP3//8KAAAAAADqlosTAIvZ++sQABvlAACQ5QQgoOMBEKDjsq3+6xAAG+UAkOUEEKDjkK/+6wjJ/+pSaW5raGFscwA=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1159244 obs=1 count=4 conv=notrunc # 0x11b04c / 0x12b04c > 0xda3600ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1215184 obs=1 count=133 conv=notrunc # 0x128ad0 / 0x138ad0 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1215318 obs=1 count=63 conv=notrunc # 0x128b56 / 0x138b56 > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1215382 obs=1 count=36 conv=notrunc # 0x128b96 / 0x138b96 > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1215420 obs=1 count=17 conv=notrunc # 0x128bbc / 0x138bbc > 0x0400a0e1030053e321c9ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1215438 obs=1 count=12 conv=notrunc # 0x128bce / 0x138bce > 0x00ead48a130097d9fbeb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1215452 obs=1 count=18 conv=notrunc # 0x128bdc / 0x138bdc > 0x6aeafbeb00009fe5000000ea3a8b130091d9
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1215472 obs=1 count=10 conv=notrunc # 0x128bf0 / 0x138bf0 > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1215484 obs=1 count=37 conv=notrunc # 0x128bfc / 0x138bfc > 0x000000ea968b13008bd9fbeb10001be5000090e50420a0e30110a0e3b2adfeeb10001be500
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1215522 obs=1 count=14 conv=notrunc # 0x128c22 / 0x138c22 > 0x90e50410a0e390affeeb08c9ffea
dd if=$PATCH_FILE skip=344 ibs=1 of=$TARGET seek=3411936 obs=1 count=9 conv=notrunc # 0x340fe0 / 0x350fe0 > 0x52696e6b68616c7300

rm $PATCH_FILE
