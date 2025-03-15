#!/bin/sh

# This script was automatically generated, don't modify it directly
# Before MD5: d9bb6a0bb749151e326b8fbb717267a1
# After MD5: bfdf6022e9a00d65272b319436fa88cf

TARGET=$1

MD5=$(md5sum $TARGET | awk '{print $1}')
if [ "$MD5" = "bfdf6022e9a00d65272b319436fa88cf" ]; then
    echo $TARGET is already patched, skipping...
    exit 0
fi
if [ "$MD5" != "d9bb6a0bb749151e326b8fbb717267a1" ]; then
    echo $TARGET hash does not match, skipping patch...
    exit 1
fi

PATCH_FILE=/tmp/patch-$RANDOM.bin
echo 'AKDjDvCg4cEDAOoO8KDhL3VzZXJlbWFpbi9yaW5raGFscy8uY3VycmVudC9vcHQvcmlua2hhbHMvdWkvcmlua2hhbHMtdWkuc2gAAACf5QAAAOrgrA8AOa4IABvlAACQ5RCg3TIA6wgAGwAAkOUBEOPZMgA7/P/qUmlua2hhbHMAUmlua2hhbA==' | base64 -d > $PATCH_FILE

dd if=$PATCH_FILE skip=0 ibs=1 of=$TARGET seek=117949 obs=1 count=7 conv=notrunc # 0x1ccbd / 0x2ccbd > 0x00a0e30ef0a0e1
dd if=$PATCH_FILE skip=7 ibs=1 of=$TARGET seek=957968 obs=1 count=4 conv=notrunc # 0xe9e10 / 0xf9e10 > 0xc10300ea
dd if=$PATCH_FILE skip=11 ibs=1 of=$TARGET seek=961756 obs=1 count=78 conv=notrunc # 0xeacdc / 0xfacdc > 0x0ef0a0e12f75736572656d61696e2f72696e6b68616c732f2e63757272656e742f6f70742f72696e6b68616c732f75692f72696e6b68616c732d75692e73680000009fe5000000eae0ac0f0039ae
dd if=$PATCH_FILE skip=89 ibs=1 of=$TARGET seek=961836 obs=1 count=8 conv=notrunc # 0xead2c / 0xfad2c > 0x08001be5000090e5
dd if=$PATCH_FILE skip=97 ibs=1 of=$TARGET seek=961845 obs=1 count=2 conv=notrunc # 0xead35 / 0xfad35 > 0x10a0
dd if=$PATCH_FILE skip=99 ibs=1 of=$TARGET seek=961848 obs=1 count=7 conv=notrunc # 0xead38 / 0xfad38 > 0xdd3200eb08001b
dd if=$PATCH_FILE skip=106 ibs=1 of=$TARGET seek=961856 obs=1 count=6 conv=notrunc # 0xead40 / 0xfad40 > 0x000090e50110
dd if=$PATCH_FILE skip=112 ibs=1 of=$TARGET seek=961863 obs=1 count=4 conv=notrunc # 0xead47 / 0xfad47 > 0xe3d93200
dd if=$PATCH_FILE skip=116 ibs=1 of=$TARGET seek=961868 obs=1 count=4 conv=notrunc # 0xead4c / 0xfad4c > 0x3bfcffea
dd if=$PATCH_FILE skip=120 ibs=1 of=$TARGET seek=2750976 obs=1 count=16 conv=notrunc # 0x29fa00 / 0x2afa00 > 0x52696e6b68616c730052696e6b68616c

rm $PATCH_FILE
