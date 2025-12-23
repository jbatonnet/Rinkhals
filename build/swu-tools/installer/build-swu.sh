#!/bin/sh

# From a Windows machine:
#   docker run --rm -it -e KOBRA_MODEL_CODE="K3" -v .\build:/build -v .\files:/files ghcr.io/jbatonnet/rinkhals/build /build/swu-tools/installer/build-swu.sh
#   docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
#   docker run --platform=linux/arm/v7 --rm -it -e KOBRA_MODEL_CODE="K3" -v .\build:/build -v .\files:/files ghcr.io/jbatonnet/armv7-uclibc:rinkhals /build/swu-tools/installer/build-swu.sh


if [ "$KOBRA_MODEL_CODE" = "" ]; then
    echo "Please specify your Kobra model using KOBRA_MODEL_CODE environment variable"
    exit 1
fi

set -e

BUILD_ROOT=$(dirname $(realpath $0))
. $BUILD_ROOT/../../tools.sh

set -x

# Prepare update
mkdir -p /tmp/update_swu
rm -rf /tmp/update_swu/*

# Libraries for Python
cp /files/1-buildroot/usr/lib/libffi.so.8 /tmp/update_swu/libffi.so.8
cp /files/1-buildroot/usr/lib/libstdc++.so.6 /tmp/update_swu/libstdc++.so.6
cp /files/1-buildroot/usr/lib/libpython3.11.so.1.0 /tmp/update_swu/libpython3.11.so.1.0
cp /files/1-buildroot/usr/lib/libz.so.1 /tmp/update_swu/libz.so.1
cp /files/1-buildroot/lib/libc.so.0 /tmp/update_swu/libc.so.0
cp /files/1-buildroot/lib/libgcc_s.so.1 /tmp/update_swu/libgcc_s.so.1
cp /files/1-buildroot/lib/ld-uClibc.so.0 /tmp/update_swu/ld-uClibc
cp /files/1-buildroot/lib/ld-uClibc.so.1 /tmp/update_swu/ld-uClibc.so.1

# Libraries for SSH
cp /files/3-rinkhals/usr/local/etc/dropbear/dropbear_rsa_host_key /tmp/update_swu/dropbear_rsa_host_key
cp /files/1-buildroot/usr/lib/libcrypto.so.1.1 /tmp/update_swu/libcrypto.so.1.1
cp /files/1-buildroot/usr/lib/libssl.so.1.1 /tmp/update_swu/libssl.so.1.1
cp /files/1-buildroot/lib/libatomic.so.1 /tmp/update_swu/libatomic.so.1

# Python runtime
mkdir -p /tmp/update_swu/lib
cp -r /files/1-buildroot/usr/lib/python3.11 /tmp/update_swu/lib

# Tool
cp -r /files/3-rinkhals/opt/rinkhals/ui/assets /tmp/update_swu/
cp -r /files/3-rinkhals/opt/rinkhals/ui/lvgl /tmp/update_swu/
cp -r /files/3-rinkhals/opt/rinkhals/tools /tmp/update_swu/
cp /files/start.sh.patch /tmp/update_swu/start.sh.patch
cp /files/3-rinkhals/opt/rinkhals/ui/*.* /tmp/update_swu/
cp $BUILD_ROOT/update.sh /tmp/update_swu/update.sh

# Clean Python
rm -rf /tmp/update_swu/lib/python3.11/config-3.11-arm-linux-gnueabihf
rm -rf /tmp/update_swu/lib/python3.11/ensurepip
rm -rf /tmp/update_swu/lib/python3.11/distutils
rm -rf /tmp/update_swu/lib/python3.11/xml
rm -rf /tmp/update_swu/lib/python3.11/unittest
rm -rf /tmp/update_swu/lvgl/*.dll

# TODO: Embed Python libraries
# cd /tmp/update_swu/lib/python3.11
# zip -r /tmp/update_swu/python.zip .
# rm -rf /tmp/update_swu/lib
# cp BUILD_ROOT/python._pth /tmp/update_swu/python._pth
# cp -r /files/1-buildroot/usr/lib/python3.11/lib-dynload/zlib.cpython-311-arm-linux-gnueabihf.so /tmp/update_swu/zlib.cpython-311-arm-linux-gnueabihf.so

# Python libraries
mkdir -p /tmp/update_swu/lib/python3.11/site-packages
cp -r /files/2-python/usr/lib/python3.11/site-packages/cffi* /tmp/update_swu/lib/python3.11/site-packages
cp /files/2-python/usr/lib/python3.11/site-packages/_cffi_backend*.so /tmp/update_swu/lib/python3.11/site-packages
cp /files/2-python/usr/lib/python3.11/site-packages/_cffi_backend*.so /tmp/update_swu/
cp -r /files/2-python/usr/lib/python3.11/site-packages/requests* /tmp/update_swu/lib/python3.11/site-packages
cp -r /files/2-python/usr/lib/python3.11/site-packages/certifi* /tmp/update_swu/lib/python3.11/site-packages
cp -r /files/2-python/usr/lib/python3.11/site-packages/idna* /tmp/update_swu/lib/python3.11/site-packages
cp -r /files/2-python/usr/lib/python3.11/site-packages/urllib* /tmp/update_swu/lib/python3.11/site-packages
cp -r /files/2-python/usr/lib/python3.11/site-packages/paho* /tmp/update_swu/lib/python3.11/site-packages

# Precompile LVGL
find /tmp/update_swu -name '*.pyc' -type f -exec rm {} \;
#python -m compileall /tmp/update_swu/lvgl

# Patch python for local interpreter
cat /files/1-buildroot/usr/bin/python |
    sed "s/\/lib\/ld-uClibc.so.0/\/tmp\/rin\/\/ld-uClibc/g" \
    > /tmp/update_swu/python

# Patch dropbear to run sftp-server locally
cat /files/1-buildroot/usr/sbin/dropbear |
    sed "s/\/lib\/ld-uClibc.so.0/\/tmp\/rin\/\/ld-uClibc/g" |
    sed "s/\/usr\/libexec\/sftp-server/\/tmp\/rin\/sftp-server    /g" \
    > /tmp/update_swu/dropbear

cat /files/1-buildroot/usr/libexec/sftp-server |
    sed "s/\/lib\/ld-uClibc.so.0/\/tmp\/rin\/\/ld-uClibc/g" \
    > /tmp/update_swu/sftp-server

# Create the update.swu
echo "Building update package..."

SWU_PATH=${1:-/build/dist/update.swu}
build_swu $KOBRA_MODEL_CODE /tmp/update_swu $SWU_PATH

echo "Done, your update package is ready: $SWU_PATH"
