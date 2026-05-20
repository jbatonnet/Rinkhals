#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 037ed5133322f457de1bbe8498e54590
# After MD5: 7589e45908722e15fd06c45ec9786c44

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "7589e45908722e15fd06c45ec9786c44" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "037ed5133322f457de1bbe8498e54590" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'bzkA6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAAAJ/lAAAA6ozaFQAAVPvrZOMEhwAAn+UAAADq8toVAPpT++sPAFDj9///CgAAn+UAAADqTtsVAPRT++s4ABvlAACQ5QQg4wEQoOMZsv7rOAAb5QAAkAQQoOMHtP7rpcb/6lJpbmtoYWxzAA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1308080 obs=1 count=4 conv=notrunc # 0x13f5b0 / 0x14f5b0 > 0x6f3900ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1366664 obs=1 count=133 conv=notrunc # 0x14da88 / 0x15da88 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1366798 obs=1 count=63 conv=notrunc # 0x14db0e / 0x15db0e > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1366862 obs=1 count=36 conv=notrunc # 0x14db4e / 0x15db4e > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1366900 obs=1 count=17 conv=notrunc # 0x14db74 / 0x15db74 > 0x00009fe5000000ea8cda15000054fbeb64
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1366919 obs=1 count=3 conv=notrunc # 0x14db87 / 0x15db87 > 0xe30487
dd if=$PATCH_FILE skip=256 ibs=1 of=$TARGET seek=1366924 obs=1 count=50 conv=notrunc # 0x14db8c / 0x15db8c > 0x00009fe5000000eaf2da1500fa53fbeb0f0050e3f7ffff0a00009fe5000000ea4edb1500f453fbeb38001be5000090e50420
dd if=$PATCH_FILE skip=306 ibs=1 of=$TARGET seek=1366975 obs=1 count=16 conv=notrunc # 0x14dbbf / 0x15dbbf > 0xe30110a0e319b2feeb38001be5000090
dd if=$PATCH_FILE skip=322 ibs=1 of=$TARGET seek=1366992 obs=1 count=12 conv=notrunc # 0x14dbd0 / 0x15dbd0 > 0x0410a0e307b4feeba5c6ffea
dd if=$PATCH_FILE skip=334 ibs=1 of=$TARGET seek=3858264 obs=1 count=9 conv=notrunc # 0x3adf58 / 0x3bdf58 > 0x52696e6b68616c7300

rm $PATCH_FILE
