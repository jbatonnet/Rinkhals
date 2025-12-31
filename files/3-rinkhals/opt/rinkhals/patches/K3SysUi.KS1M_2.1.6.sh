#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 92d9dd4d001dd0d5bcd7b6aa52b2c05b
# After MD5: c4b2175991e188c3725a7507ba3226de

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "c4b2175991e188c3725a7507ba3226de" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "92d9dd4d001dd0d5bcd7b6aa52b2c05b" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'azMA6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBT45DM/xoAAJ/lAADqhIgVAGVo++tkAGWb++sAAJ/lAAAA6uqIFQBfaA8AUOP3//8KAAAAAADqRokVAFlo++sQABvlAACQ5QQgoOMBEKDjVrb+6xAAG+UAkOUQoONDuP7rd8z/6lJpbmtoYWxzAA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1293240 obs=1 count=4 conv=notrunc # 0x13bbb8 / 0x14bbb8 > 0x6b3300ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1345664 obs=1 count=133 conv=notrunc # 0x148880 / 0x158880 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1345798 obs=1 count=63 conv=notrunc # 0x148906 / 0x158906 > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1345862 obs=1 count=36 conv=notrunc # 0x148946 / 0x158946 > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1345900 obs=1 count=17 conv=notrunc # 0x14896c / 0x15896c > 0x0400a0e1030053e390ccff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1345918 obs=1 count=12 conv=notrunc # 0x14897e / 0x15897e > 0x00ea848815006568fbeb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1345932 obs=1 count=18 conv=notrunc # 0x14898c / 0x15898c > 0x659bfbeb00009fe5000000eaea8815005f68
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1345952 obs=1 count=10 conv=notrunc # 0x1489a0 / 0x1589a0 > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1345964 obs=1 count=37 conv=notrunc # 0x1489ac / 0x1589ac > 0x000000ea468915005968fbeb10001be5000090e50420a0e30110a0e356b6feeb10001be500
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1346002 obs=1 count=2 conv=notrunc # 0x1489d2 / 0x1589d2 > 0x90e5
dd if=$PATCH_FILE skip=332 ibs=1 of=$TARGET seek=1346005 obs=1 count=11 conv=notrunc # 0x1489d5 / 0x1589d5 > 0x10a0e343b8feeb77ccffea
dd if=$PATCH_FILE skip=343 ibs=1 of=$TARGET seek=3824456 obs=1 count=9 conv=notrunc # 0x3a5b48 / 0x3b5b48 > 0x52696e6b68616c7300

rm $PATCH_FILE
