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
RUN ./build.sh kernel
RUN ./build.sh rootfs

RUN ln -s /luckfox/sysdrv/source/buildroot/buildroot-2023.02.6 /buildroot
WORKDIR /buildroot

# Apply global patches to Buildroot environment
COPY ./build/1-buildroot/*.patch /buildroot/
RUN git apply ./*.patch

COPY ./build/1-buildroot/.config /buildroot/.config
COPY ./build/1-buildroot/busybox.config /buildroot/busybox.config
COPY ./build/1-buildroot/external/ /external/
COPY ./build/1-buildroot/prepare-final.sh /buildroot/

WORKDIR /luckfox

FROM luckfox AS buildroot-build
# Remove downloads and output after build to reduce layer size
ARG clean_buildroot=1

# Make Buildroot using provided config and external tree
ENV KCONFIG_NOSILENTUPDATE=1
RUN --mount=type=cache,target=/buildroot/dl \
<<EOT
    set -e
    ./build.sh kernel
    #./build.sh rootfs
    cd /luckfox/sysdrv/source/buildroot/buildroot-2023.02.6
    make BR2_EXTERNAL=/external
    chmod +x /buildroot/prepare-final.sh
    /buildroot/prepare-final.sh
    if [ ${clean_buildroot} -eq 1 ]; then
        ./build.sh clean
    fi
EOT

###############################################################
# buildroot-build builds the root filesystem and core packages
FROM buildroot-build AS buildroot-rebuild

# Use files from rebuild/ (if it exists) to rebuild without invalidating the base image
# Note: pattern matching 'rebuil[d]' is a trick to copy-if-exists
COPY ./build/1-buildroot/rebuil[d]/.config /buildroot/
COPY ./build/1-buildroot/rebuil[d]/busybox.config /buildroot/
COPY ./build/1-buildroot/rebuil[d]/external/ /external/

# Perform dirclean and rebuild for selected packages
# https://buildroot.org/downloads/manual/manual.html#rebuild-pkg
ENV KCONFIG_NOSILENTUPDATE=1
ARG clean_buildroot=1
ARG rebuild=""
RUN --mount=type=cache,target=/buildroot/dl \
<<EOT
    set -e
    if [ $clean_buildroot -eq 1 ] && [ -n "$rebuild" ]; then
        echo "Unable to rebuild because Buildroot stage was cleaned"
        exit 1
    fi
    if [ -n "$rebuild" ]; then
        echo "Rebuilding packages: $rebuild"
        echo $rebuild | tr ',' ' ' | while read -r p; do
            make ${p}-dirclean
            make ${p}-rebuild
        done;
        chmod +x /buildroot/prepare-final.sh
        /buildroot/prepare-final.sh
    else
        echo "No packages to rebuild";
    fi
EOT
