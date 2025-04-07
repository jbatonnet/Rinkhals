#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 91ab25e14b890cbce21f3472ef94c307
# After MD5: 39dc2cfca3d66afefae1f8bb6d159f43

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "39dc2cfca3d66afefae1f8bb6d159f43" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "91ab25e14b890cbce21f3472ef94c307" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'FR0A6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT4+bi/xoAAJ/lAADqxGUUAIKX++tkAHKs++sAAJ/lAAAA6ipmFAB8lw8AUOP3//8KAAAAAADqhmYUAHaX++sQABvlAACQ5QQgoOMBEKDj1fn+6xAAG+UAkOUEEKDjavv+683i/+pSaW5raGFscwA=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1241680 obs=1 count=4 conv=notrunc # 0x12f250 / 0x13f250 > 0x151d00ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1271232 obs=1 count=133 conv=notrunc # 0x1365c0 / 0x1465c0 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1271366 obs=1 count=63 conv=notrunc # 0x136646 / 0x146646 > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1271430 obs=1 count=36 conv=notrunc # 0x136686 / 0x146686 > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1271468 obs=1 count=17 conv=notrunc # 0x1366ac / 0x1466ac > 0x0400a0e1030053e3e6e2ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1271486 obs=1 count=12 conv=notrunc # 0x1366be / 0x1466be > 0x00eac46514008297fbeb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1271500 obs=1 count=18 conv=notrunc # 0x1366cc / 0x1466cc > 0x72acfbeb00009fe5000000ea2a6614007c97
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1271520 obs=1 count=10 conv=notrunc # 0x1366e0 / 0x1466e0 > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1271532 obs=1 count=37 conv=notrunc # 0x1366ec / 0x1466ec > 0x000000ea866614007697fbeb10001be5000090e50420a0e30110a0e3d5f9feeb10001be500
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1271570 obs=1 count=14 conv=notrunc # 0x136712 / 0x146712 > 0x90e50410a0e36afbfeebcde2ffea
dd if=$PATCH_FILE skip=344 ibs=1 of=$TARGET seek=2866868 obs=1 count=9 conv=notrunc # 0x2bbeb4 / 0x2cbeb4 > 0x52696e6b68616c7300

rm $PATCH_FILE
