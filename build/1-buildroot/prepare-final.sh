#!/bin/sh

# Copy all files
mkdir -p ./output/final
rm -rf ./output/final/*
cp -pr ./output/target/* ./output/final/

# Clean unused files
rm -rf ./output/final/dev
rm -rf ./output/final/lib32
rm -rf ./output/final/media
rm -rf ./output/final/mnt
rm -rf ./output/final/opt
rm -rf ./output/final/proc
rm -rf ./output/final/root
rm -rf ./output/final/run
rm -rf ./output/final/sys
rm -rf ./output/final/share
rm -rf ./output/final/tmp
rm -rf ./output/final/usr/lib32
rm -rf ./output/final/var
rm ./output/final/THIS_IS_NOT_YOUR_ROOT_FILESYSTEM

# Clean /etc except for ssl
for dir in ./output/final/etc/*; do
    [ "$dir" = "./output/final/etc/ssl" ] && continue
    rm -rf "$dir"
done

# Create certificate bundle
cat ./output/final/etc/ssl/certs/*.pem > ./output/final/etc/ssl/cert.pem

# Clean GCC copies
rm -rf ./output/final/usr/bin/arm-buildroot-linux-uclibcgnueabihf-*

# Clean python packages
rm -rf ./output/final/usr/lib/python3.11/site-packages/*
rm -rf ./output/final/usr/lib/python3.*/site-packages/*

# Clean python .pyc files
find ./output/final/usr/lib/python3.* -name '*.pyc' -type f -delete

# Copy output to volume mount and derefence symlinks
mkdir -p /config/output/final
rm -rf /config/output/final/*
cp -pr -L ./output/final/* /config/output/final/
