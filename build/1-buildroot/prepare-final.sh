#!/bin/sh

# Copy all files
mkdir -p /files/1-buildroot
rm -rf /files/1-buildroot/*
cp -pr ./output/target/* /files/1-buildroot/

# Fix a broken symlink in iptables
cd /files/1-buildroot/usr/bin
ln -f ../sbin/xtables-legacy-multi iptables-xml

# Clean unused files
rm -rf /files/1-buildroot/dev
rm -rf /files/1-buildroot/lib32
rm -rf /files/1-buildroot/media
rm -rf /files/1-buildroot/mnt
rm -rf /files/1-buildroot/opt
rm -rf /files/1-buildroot/proc
rm -rf /files/1-buildroot/root
rm -rf /files/1-buildroot/run
rm -rf /files/1-buildroot/sys
rm -rf /files/1-buildroot/share
rm -rf /files/1-buildroot/tmp
rm -rf /files/1-buildroot/usr/lib32
rm -rf /files/1-buildroot/var
rm /files/1-buildroot/THIS_IS_NOT_YOUR_ROOT_FILESYSTEM

# Clean /etc except for ssl
for dir in /files/1-buildroot/etc/*; do
    [ "$dir" = "/files/1-buildroot/etc/ssl" ] && continue
    rm -rf "$dir"
done

# Create certificate bundle
cat /files/1-buildroot/etc/ssl/certs/*.pem > /files/1-buildroot/etc/ssl/cert.pem

# Clean GCC copies
rm -rf /files/1-buildroot/usr/bin/arm-buildroot-linux-uclibcgnueabihf-*

# Clean python packages
rm -rf /files/1-buildroot/usr/lib/python3.11/site-packages/*
rm -rf /files/1-buildroot/usr/lib/python3.*/site-packages/*

# Clean python .pyc files
find /files/1-buildroot/usr/lib/python3.* -name '*.pyc' -type f -delete
