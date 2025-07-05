``` sh
# Enable QEMU for ARMv7 stages
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Build the rootfs image from Docker
docker build -t rinkhals/buildroot-builder -f build/1-buildroot/builder.Dockerfile .

# Extarct the rootfs
docker run --rm -it -v .\tmp:/tmp -v .\build:/build rinkhals/buildroot-builder /build/1-buildroot/extract-rootfs.sh

# Build the final Docker image
docker build -t rinkhals/buildroot -f build/1-buildroot/Dockerfile .
```
