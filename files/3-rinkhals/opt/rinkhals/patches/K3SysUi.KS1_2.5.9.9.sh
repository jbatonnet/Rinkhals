#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: eafc70a0ccee6233f4435c4d4e83a231
# After MD5: 2f4d2d488ad76ef1a73a7c7ed648eccf

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "2f4d2d488ad76ef1a73a7c7ed648eccf" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "eafc70a0ccee6233f4435c4d4e83a231" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'FDkA6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAEAKDhAwBR4+fG/xoAAJ/lAADqjIgVAGNo++tkAGOb++sAAJ/lAAAA6vKIFQBdaA8AUOP3//8KAAAAAADqTokVAFdo++swABvlAACQ5QQgoOMBEKDjVrb+6zAAG+UAkOUEEKDjQ7j+687G/+pSaW5raGFscwA=' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1287452 obs=1 count=4 conv=notrunc # 0x13a51c / 0x14a51c > 0x143900ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1345672 obs=1 count=133 conv=notrunc # 0x148888 / 0x158888 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1345806 obs=1 count=63 conv=notrunc # 0x14890e / 0x15890e > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1345870 obs=1 count=36 conv=notrunc # 0x14894e / 0x15894e > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1345908 obs=1 count=17 conv=notrunc # 0x148974 / 0x158974 > 0x0400a0e1030051e3e7c6ff1a00009fe500
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1345926 obs=1 count=12 conv=notrunc # 0x148986 / 0x158986 > 0x00ea8c8815006368fbeb6400
dd if=$PATCH_FILE skip=265 ibs=1 of=$TARGET seek=1345940 obs=1 count=18 conv=notrunc # 0x148994 / 0x158994 > 0x639bfbeb00009fe5000000eaf28815005d68
dd if=$PATCH_FILE skip=283 ibs=1 of=$TARGET seek=1345960 obs=1 count=10 conv=notrunc # 0x1489a8 / 0x1589a8 > 0x0f0050e3f7ffff0a0000
dd if=$PATCH_FILE skip=293 ibs=1 of=$TARGET seek=1345972 obs=1 count=37 conv=notrunc # 0x1489b4 / 0x1589b4 > 0x000000ea4e8915005768fbeb30001be5000090e50420a0e30110a0e356b6feeb30001be500
dd if=$PATCH_FILE skip=330 ibs=1 of=$TARGET seek=1346010 obs=1 count=14 conv=notrunc # 0x1489da / 0x1589da > 0x90e50410a0e343b8feebcec6ffea
dd if=$PATCH_FILE skip=344 ibs=1 of=$TARGET seek=3824360 obs=1 count=9 conv=notrunc # 0x3a5ae8 / 0x3b5ae8 > 0x52696e6b68616c7300

rm $PATCH_FILE
