#
# TODO Document usage in header
#
# Needed once on host for build-armv7:
# docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
#
# Use with local filesystem output: https://docs.docker.com/build/exporters/local-tar/
# docker build --output type=tar,dest=./bundle.tar .
#
# Note: This multi-stage Dockerfile is intended to be built with Buildkit enabled for best performance
#

###############################################################
# buildroot builds the root filesystem and core packages
FROM debian:12.8 AS buildroot
ENV DEBIAN_FRONTEND=noninteractive

# Install buildroot dependencies
# https://buildroot.org/downloads/manual/manual.html#requirement
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        which sed make binutils build-essential diffutils gcc g++ bash patch gzip bzip2 perl tar cpio unzip rsync file bc findutils wget \
        python3 libncurses5 git mercurial ca-certificates \
        locales whois vim bison flex \
        libncurses5-dev libdevmapper-dev libsystemd-dev libssl-dev libfdt-dev && \
    rm -rf /var/lib/apt/lists/*

# Sometimes Buildroot needs proper locale, e.g. when using a toolchain based on glibc
RUN locale-gen en_US.utf8

ADD https://gitlab.com/buildroot.org/buildroot.git#2023.02.6 /buildroot
WORKDIR /buildroot

# Patch buildroot to enable the gcc package (and change a few others)
COPY ./build/1-buildroot/gcc-target.patch /buildroot/
RUN git apply ./gcc-target.patch

# Make using bind mounted Buildroot config and external tree
# - This prevents layer cache invalidation on changes, so a complete rebuild is not automatically required
# - Use `docker build --target buildroot-rebuild` instead to rebuild specific packages
# - Use `docker build --no-cache-filter buildroot` to invalidate the cache for a complete rebuild
ENV KCONFIG_NOSILENTUPDATE=1
RUN --mount=type=bind,source=./build/1-buildroot/.config,target=/buildroot/.config \
    --mount=type=bind,source=./build/1-buildroot/busybox.config,target=/buildroot/busybox.config \
    --mount=type=bind,source=./build/1-buildroot/external,target=/external \
    make BR2_EXTERNAL=/external

COPY ./build/1-buildroot/prepare-final.sh /buildroot/
RUN /buildroot/prepare-final.sh


###############################################################
# buildroot-rebuild rebuilds selected buildroot packages
FROM buildroot AS buildroot-rebuild
ARG rebuild=""

# Invalidates cache when files are changed, so make rebuild is executed
# https://buildroot.org/downloads/manual/manual.html#rebuild-pkg
COPY ./build/1-buildroot/.config /buildroot/.config
COPY ./build/1-buildroot/busybox.config /buildroot/busybox.config
COPY ./build/1-buildroot/external/ /external/
ENV KCONFIG_NOSILENTUPDATE=1
RUN if [ -n "$rebuild" ]; then \
        echo "Rebuilding packages: $rebuild" && \
        echo $rebuild | tr ',' ' ' | while read -r p; do \
            make ${p}-dirclean && \
            make ${p}-rebuild; \
        done; \
    else \
        echo "No packages to rebuild"; \
    fi

COPY ./build/1-buildroot/prepare-final.sh /buildroot/
RUN /buildroot/prepare-final.sh


###############################################################
# build-armv7 builds dependencies that require custom compilation
FROM --platform=linux/arm/v7 ghcr.io/jbatonnet/armv7-uclibc:rinkhals AS build-armv7

COPY ./build/2-python/get-packages.sh /build/2-python/get-packages.sh
COPY ./build/4-apps/40-moonraker/get-packages.sh /build/4-apps/40-moonraker/get-packages.sh

# Execute all scripts named get-packages.sh (for python and apps)
RUN --mount=type=cache,target=/root/.cache/pip \
    find /build -type f -name get-packages.sh -exec sh {} \;


###############################################################
# build-base provides the basis for common build steps
FROM debian:12.8 AS build-base
ENV DEBIAN_FRONTEND=noninteractive

# Install common utilities
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        wget sed rsync unzip ca-certificates && \
    rm -rf /var/lib/apt/lists/*


###############################################################
# app-mainsail prepares Mainsail app files
FROM build-base AS app-mainsail
COPY ./build/4-apps/25-mainsail/* /build/
COPY ./files/4-apps/home/rinkhals/apps/25-mainsail/app.json /files/4-apps/home/rinkhals/apps/25-mainsail/app.json
RUN /build/get-mainsail.sh


###############################################################
# app-fluidd prepares Fluidd app files
FROM build-base AS app-fluidd
COPY ./build/4-apps/26-fluidd/* /build/
COPY ./files/4-apps/home/rinkhals/apps/26-fluidd/app.json /files/4-apps/home/rinkhals/apps/26-fluidd/app.json
RUN /build/get-fluidd.sh


###############################################################
# app-moonraker prepares Moonraker app files
FROM build-base AS app-moonraker
COPY ./build/4-apps/40-moonraker/* /build/
COPY ./files/4-apps/home/rinkhals/apps/40-moonraker/app.json /files/4-apps/home/rinkhals/apps/40-moonraker/app.json
RUN /build/get-moonraker.sh


###############################################################
# file-bundle collects all files for distribution
FROM scratch AS file-bundle
COPY --from=buildroot /files/1-buildroot/ /
COPY --from=buildroot-rebuild /files/1-buildroot/ /
COPY --from=build-armv7 /files/2-python/ /
COPY --from=build-armv7 /files/4-apps/ /
COPY --from=app-mainsail /files/4-apps/ /
COPY --from=app-fluidd /files/4-apps/ /
COPY --from=app-moonraker /files/4-apps/ /
COPY ./files/3-rinkhals /
COPY ./files/4-apps /
COPY ./files/*.* /


###############################################################
# swu-bundle
#FROM build-base AS swu-bundle
