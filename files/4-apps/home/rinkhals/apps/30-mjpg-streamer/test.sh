

# ghcr.io/jbatonnet/armv7-uclibc:rinkhals
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
docker run --platform=linux/arm/v7 --rm -it -v .:/work ghcr.io/jbatonnet/armv7-uclibc:rinkhals