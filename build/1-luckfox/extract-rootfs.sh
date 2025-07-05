#!/bin/sh

mkdir -p /build/tmp
cp -rf ./output/images/rootfs.tar /build/tmp/luckfox-rootfs.tar
tar czvf /build/tmp/luckfox-drivers.tgz -C /luckfox/sysdrv/out/kernel_drv_ko .
