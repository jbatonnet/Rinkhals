###############################################################
# buildroot prepares the buildroot environment
FROM debian:12.10 AS buildroot
ENV DEBIAN_FRONTEND=noninteractive

# Install buildroot dependencies
# https://buildroot.org/downloads/manual/manual.html#requirement
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        which sed make binutils build-essential diffutils gcc g++ bash patch gzip bzip2 perl tar cpio unzip rsync file bc findutils wget \
        python3 libncurses5 git mercurial ca-certificates \
        locales whois vim bison flex \
        libncurses5-dev libdevmapper-dev libsystemd-dev libssl-dev libfdt-dev libvncserver-dev libdrm-dev && \
    rm -rf /var/lib/apt/lists/*

# Sometimes Buildroot needs proper locale, e.g. when using a toolchain based on glibc
RUN locale-gen en_US.utf8

ADD https://gitlab.com/buildroot.org/buildroot.git#2023.02.6 /buildroot
WORKDIR /buildroot

# Apply global patches to Buildroot environment
COPY ./build/1-buildroot/*.patch /buildroot/
RUN git apply ./*.patch

COPY ./build/1-buildroot/.config /buildroot/.config
COPY ./build/1-buildroot/busybox.config /buildroot/busybox.config
COPY ./build/1-buildroot/external/ /external/
COPY ./build/1-buildroot/prepare-final.sh /buildroot/

FROM buildroot AS buildroot-build
# Remove downloads and output after build to reduce layer size
ARG clean_buildroot=1

# Make Buildroot using provided config and external tree
ENV KCONFIG_NOSILENTUPDATE=1
RUN --mount=type=cache,target=/buildroot/dl \
<<EOT
    set -e
    make BR2_EXTERNAL=/external
    chmod +x /buildroot/prepare-final.sh
    /buildroot/prepare-final.sh
    if [ ${clean_buildroot} -eq 1 ]; then
        make clean
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
