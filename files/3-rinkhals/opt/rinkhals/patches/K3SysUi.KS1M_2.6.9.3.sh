#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: 25aebde23301907ec74161bdf4a61ee6
# After MD5: faf62b9e67588b1ee270050737b1e49b

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "faf62b9e67588b1ee270050737b1e49b" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "25aebde23301907ec74161bdf4a61ee6" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'WTkA6g7woOEvdXNlcmVtYWluL3JpbmtoYWxzLy5jdXJyZW50L29wdC9yaW5raGFscy91aS9yaW5raGFscy11aS5zaCAmIGVjaG8gJCEgPiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAB0aW1lb3V0IC10IDIgc3RyYWNlIC1xcXEgLWV0cmFjZT1ub25lIC1wICQoY2F0IC90bXAvcmlua2hhbHMvcmlua2hhbHMtdWkucGlkKSAyPiAvZGV2L251bGxybSAtZiAvdG1wL3JpbmtoYWxzL3JpbmtoYWxzLXVpLnBpZAAAAJ/lAAAA6rTvFQDqTvvrZOMhggAAn+UAAADqGvAVAORO++sPAFDj9///CgAAn+UAAADqdvAVAN5O++s4ABvlAACQ5QQg4wEQoONMsf7rOAAb5QAAkAQQoOM6s/7rs8b/6lJpbmtoYWxzAA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=1313584 obs=1 count=4 conv=notrunc # 0x140b30 / 0x150b30 > 0x593900ea
dd if=$PATCH_FILE skip=4 ibs=1 of=$TARGET seek=1372080 obs=1 count=133 conv=notrunc # 0x14efb0 / 0x15efb0 > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73682026206563686f202421203e202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069640074696d656f7574202d74203220737472616365202d717171202d65
dd if=$PATCH_FILE skip=137 ibs=1 of=$TARGET seek=1372214 obs=1 count=63 conv=notrunc # 0x14f036 / 0x15f036 > 0x74726163653d6e6f6e65202d70202428636174202f746d702f72696e6b68616c732f72696e6b68616c732d75692e7069642920323e202f6465762f6e756c6c
dd if=$PATCH_FILE skip=200 ibs=1 of=$TARGET seek=1372278 obs=1 count=36 conv=notrunc # 0x14f076 / 0x15f076 > 0x726d202d66202f746d702f72696e6b68616c732f72696e6b68616c732d75692e70696400
dd if=$PATCH_FILE skip=236 ibs=1 of=$TARGET seek=1372316 obs=1 count=17 conv=notrunc # 0x14f09c / 0x15f09c > 0x00009fe5000000eab4ef1500ea4efbeb64
dd if=$PATCH_FILE skip=253 ibs=1 of=$TARGET seek=1372335 obs=1 count=3 conv=notrunc # 0x14f0af / 0x15f0af > 0xe32182
dd if=$PATCH_FILE skip=256 ibs=1 of=$TARGET seek=1372340 obs=1 count=50 conv=notrunc # 0x14f0b4 / 0x15f0b4 > 0x00009fe5000000ea1af01500e44efbeb0f0050e3f7ffff0a00009fe5000000ea76f01500de4efbeb38001be5000090e50420
dd if=$PATCH_FILE skip=306 ibs=1 of=$TARGET seek=1372391 obs=1 count=16 conv=notrunc # 0x14f0e7 / 0x15f0e7 > 0xe30110a0e34cb1feeb38001be5000090
dd if=$PATCH_FILE skip=322 ibs=1 of=$TARGET seek=1372408 obs=1 count=12 conv=notrunc # 0x14f0f8 / 0x15f0f8 > 0x0410a0e33ab3feebb3c6ffea
dd if=$PATCH_FILE skip=334 ibs=1 of=$TARGET seek=3862464 obs=1 count=9 conv=notrunc # 0x3aefc0 / 0x3befc0 > 0x52696e6b68616c7300

rm $PATCH_FILE
