``` sh
# Enable QEMU for ARMv7 stages
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Build the rootfs image from Docker
docker build -t rinkhals/luckfox-builder -f build/1-luckfox/builder.Dockerfile .

# Extract the rootfs
docker run --rm -it -v .\tmp:/tmp -v .\build:/build rinkhals/luckfox-builder /build/1-luckfox/extract-rootfs.sh

# Build the final Docker image
docker build -t rinkhals/luckfox -f build/1-luckfox/Dockerfile .
```
