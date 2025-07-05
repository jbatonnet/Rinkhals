

###############################################################
# luckfox prepares the luckfox SDK environment
FROM debian:12.11 AS luckfox
ENV DEBIAN_FRONTEND=noninteractive

# Install LuckFox and Buildroot dependencies
# https://wiki.luckfox.com/Luckfox-Pico/Luckfox-Pico-SDK/
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        which sed make binutils build-essential diffutils gcc g++ bash patch gzip bzip2 perl tar cpio unzip rsync file bc findutils wget \
        python3 libncurses5 git mercurial ca-certificates \
        git ssh make gcc gcc-multilib g++-multilib module-assistant expect g++ gawk texinfo libssl-dev bison flex fakeroot cmake unzip gperf autoconf device-tree-compiler libncurses5-dev pkg-config bc python-is-python3 passwd openssl openssh-server openssh-client vim file cpio rsync \
        locales whois vim bison flex \
        libncurses5-dev libdevmapper-dev libsystemd-dev libssl-dev libfdt-dev libvncserver-dev libdrm-dev && \
    rm -rf /var/lib/apt/lists/*

# Sometimes Buildroot needs proper locale, e.g. when using a toolchain based on glibc
RUN locale-gen en_US.utf8

ADD https://github.com/LuckfoxTECH/luckfox-pico.git#a984090f0620bf643c990422747d7306f6c82857 /luckfox
WORKDIR /luckfox

# Configure LuckFox SDK
#   8: RV1106_Luckfox_Pico_Ultra_W
#   0: Boot from EMMC
#   0: Buildroot build system
RUN (echo 8; echo 0; echo 0) | ./build.sh lunch

COPY ./build/1-luckfox/kernel.config /luckfox/sysdrv/source/kernel/arch/arm/configs/luckfox_rv1106_linux_defconfig


###############################################################
# output image with prebuilt binaries
FROM luckfox

RUN \
<<EOT
    set -e
    ./build.sh kernel
    ./build.sh rootfs
    ln -s /luckfox/sysdrv/source/buildroot/buildroot-2023.02.6 /buildroot
EOT

WORKDIR /buildroot
