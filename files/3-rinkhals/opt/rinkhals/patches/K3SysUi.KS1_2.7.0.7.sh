#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: ba950ecf676fe8f9fd3b92b39dea5d1f
# After MD5: e0798c2024833b8031c2ae2b7feeaaa3

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "e0798c2024833b8031c2ae2b7feeaaa3" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "ba950ecf676fe8f9fd3b92b39dea5d1f" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'NTkA6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAAAJ/lAAAA6mTMFQCKV/vrZOOOigAAn+UAAADqyswVAIRX++sPAFDj9///CgAAn+UAAADqJs0VAH5X++swABvlAACQ5QQg4wEQoOOXtP7rMAAb5QAAkAQQoOOEtv7rucb/6lJpbmtoYWxzAA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1304688 obs=1 count=4 conv=notrunc # 0x13e870 / 0x14e870 > 0x353900ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1363040 obs=1 count=133 conv=notrunc # 0x14cc60 / 0x15cc60 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1363174 obs=1 count=63 conv=notrunc # 0x14cce6 / 0x15cce6 > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1363238 obs=1 count=36 conv=notrunc # 0x14cd26 / 0x15cd26 > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1363276 obs=1 count=17 conv=notrunc # 0x14cd4c / 0x15cd4c > 0x00009fe5000000ea64cc15008a57fbeb64
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1363295 obs=1 count=3 conv=notrunc # 0x14cd5f / 0x15cd5f > 0xe38e8a
dd if=$PATCH_FILE skip=256 ibs=1 of=$TARGET seek=1363300 obs=1 count=50 conv=notrunc # 0x14cd64 / 0x15cd64 > 0x00009fe5000000eacacc15008457fbeb0f0050e3f7ffff0a00009fe5000000ea26cd15007e57fbeb30001be5000090e50420
dd if=$PATCH_FILE skip=306 ibs=1 of=$TARGET seek=1363351 obs=1 count=16 conv=notrunc # 0x14cd97 / 0x15cd97 > 0xe30110a0e397b4feeb30001be5000090
dd if=$PATCH_FILE skip=322 ibs=1 of=$TARGET seek=1363368 obs=1 count=12 conv=notrunc # 0x14cda8 / 0x15cda8 > 0x0410a0e384b6feebb9c6ffea
dd if=$PATCH_FILE skip=334 ibs=1 of=$TARGET seek=3853328 obs=1 count=9 conv=notrunc # 0x3acc10 / 0x3bcc10 > 0x52696e6b68616c7300

rm $PATCH_FILE
