#
# Main Dockerfile for building Rinkhals
#
# This multi-stage Dockerfile includes all steps to go from a clean repository to an installable SWU package.
# Note: Buildkit and buildx are required, but should already be enabled by default in most nonlegacy Docker installations.
#
# Enable QEMU for ARMv7 stages (needed once per session):
# - docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
#
# Building with local filesystem output (https://docs.docker.com/build/exporters/local-tar/):
# - docker build --output type=local,dest=./build/dist .
#
# Building a release:
# - docker build --build-arg RINKHALS_VERSION=yyyymmdd_nn --output type=local,dest=./build/dist .
#
# Making quick changes to buildroot during development:
# - Copy `.config`, `busybox.config`, `external/` from `/build/1-buildroot` to `/build/1-buildroot/rebuild`
# - Make changes in the copied files
# - Rebuild packages using the build-arg `rebuild`:
# - docker build --build-arg clean_buildroot=0 --build-arg rebuild=lv_micropython --output type=local,dest=./build/dist .
# - Note that `clean_buildroot=0` will require a full rebuild the first time, because the intermediate files are normally deleted to save space
# - When done, copy back your changes to the original files
# - Do a normal build to verify your results
#
# Debugging/inspecting a specific stage:
# - docker build --target <stage>
# - Take note of the image hash in the output
# - docker run --rm -it <hash> sh
#
# Deploying a development build to a printer:
# - docker build --output type=local,dest=./build/dist .
# - docker run --rm -it -e KOBRA_IP=x.x.x.x --mount type=bind,source=.\build,target=/build --entrypoint=/bin/sh rclone/rclone:1.69.1 /build/deploy-dev.sh
# - Note: On Linux/macOS, use `--mount type=bind,source=./build,target=/build` instead of `--mount type=bind,source=.\build,target=/build`
#
# Seeding cache for Github Actions:
# - docker login ghcr.io <etc...>
# - docker buildx create --name rinkhals-builder --driver docker-container
# - docker build --builder rinkhals-builder --cache-to type=registry,mode=max,ref=ghcr.io/jbatonnet/rinkhals:buildcache --output type=cacheonly .
# - Note: Using a different builder requires a full rebuild, so make it default for development if you want to avoid that.
#
# Note: On Windows, all files copied to Docker will have +x set by default (due to WSL). To avoid inconsistency in cache keys between Windows and
# Linux (Github), run the build from the WSL filesystem (i.e. `/home` not `/mnt/c`).
#


ARG BASE_IMAGE=debian:12.11


###############################################################
# buildroot-base and luckfox-base are built by separate pipelines
# By default they are sourced from ghcr.io, but the can be built locally using BASE_REPOSITORY=rinkhals

ARG BUILDROOT_BASE=ghcr.io/jbatonnet/rinkhals/buildroot-base:latest
ARG LUCKFOX_BASE=ghcr.io/jbatonnet/rinkhals/luckfox-base:latest

FROM ${BUILDROOT_BASE} AS buildroot-base
FROM ${LUCKFOX_BASE} AS luckfox-base


###############################################################
# rinkhals-base is the base for Rinkhals overlay fs
# It combines mostly the root fs from Buildroot and some additional drivers from luckfox

FROM ${BASE_IMAGE} AS rinkhals-base

# Copy part of rootfs from Buildroot
COPY --from=buildroot-base /bin /files/1-buildroot/bin
COPY --from=buildroot-base /etc /files/1-buildroot/etc
COPY --from=buildroot-base /lib /files/1-buildroot/lib
COPY --from=buildroot-base /sbin /files/1-buildroot/sbin
COPY --from=buildroot-base /usr /files/1-buildroot/usr

# Rename busybox (to avoid conflict with stock) and update all symlinks
RUN <<EOT
    set -e
    mv /bundle/rinkhals/bin/busybox /bundle/rinkhals/bin/busybox.rinkhals
    find /bundle/ -type l -exec sh -c '
        for link; do
            target=$(readlink "$link")
            if [ "$(basename "$target")" = "busybox" ]; then
                dir=$(dirname "$target")
                newtarget="$dir/busybox.rinkhals"
                newtarget="${newtarget#./}"
                ln -snf "$newtarget" "$link"
            fi
        done
        ' sh {} +
EOT

# Clean /etc except for ssl
RUN <<EOT
    for dir in /files/1-buildroot/etc/*; do
        [ "$dir" = "/files/1-buildroot/etc/ssl" ] && continue
        rm -rf "$dir"
    done
EOT

# Create certificate bundle
RUN cat /files/1-buildroot/etc/ssl/certs/*.pem > /files/1-buildroot/etc/ssl/cert.pem

# Clean GCC copies
RUN rm -rf /files/1-buildroot/usr/bin/arm-buildroot-linux-uclibcgnueabihf-*

# Clean linux modules
RUN rm -rf /files/1-buildroot/lib/modules

# Clean python files
RUN rm -rf /files/1-buildroot/usr/lib/python3.11/site-packages/*
RUN rm -rf /files/1-buildroot/usr/lib/python3.*/site-packages/*
RUN find /files/1-buildroot/usr/lib/python3.* -name '*.pyc' -type f -delete

# Copy additional drivers from Luckfox
COPY --from=luckfox-base /etc/ko /files/1-buildroot/etc/ko


###############################################################
# build-python-armv7 builds Python dependencies that require ARMv7 compilation

FROM --platform=linux/arm/v7 ghcr.io/jbatonnet/armv7-uclibc:rinkhals AS build-python-armv7

COPY ./build/2-python/get-packages.sh /build/2-python/get-packages.sh
RUN --mount=type=cache,sharing=locked,target=/root/.cache/pip \
    chmod +x /build/2-python/get-packages.sh && \
    /build/2-python/get-packages.sh


###############################################################
# build-base provides the basis for common build steps

FROM ${BASE_IMAGE} AS build-base

ENV DEBIAN_FRONTEND=noninteractive

# Install common utilities
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        wget sed rsync zip unzip ca-certificates && \
    rm -rf /var/lib/apt/lists/*


###############################################################
# app-mainsail prepares Mainsail app files

FROM build-base AS app-mainsail

COPY ./build/4-apps/25-mainsail/* /build/
COPY ./files/4-apps/home/rinkhals/apps/25-mainsail/app.json /files/4-apps/home/rinkhals/apps/25-mainsail/app.json
RUN chmod +x /build/get-mainsail.sh && \
    /build/get-mainsail.sh


###############################################################
# app-fluidd prepares Fluidd app files

FROM build-base AS app-fluidd

COPY ./build/4-apps/26-fluidd/* /build/
COPY ./files/4-apps/home/rinkhals/apps/26-fluidd/app.json /files/4-apps/home/rinkhals/apps/26-fluidd/app.json
RUN chmod +x /build/get-fluidd.sh && \
    /build/get-fluidd.sh


###############################################################
# app-moonraker prepares Moonraker app files

FROM build-base AS app-moonraker

COPY ./build/4-apps/40-moonraker/* /build/
COPY ./files/4-apps/home/rinkhals/apps/40-moonraker/app.json /files/4-apps/home/rinkhals/apps/40-moonraker/app.json
RUN chmod +x /build/get-moonraker.sh && \
    /build/get-moonraker.sh


###############################################################
# app-moonraker-armv7 builds Moonraker dependencies that require ARMv7 compilation

FROM --platform=linux/arm/v7 ghcr.io/jbatonnet/armv7-uclibc:rinkhals AS app-moonraker-armv7

COPY --from=app-moonraker /files/4-apps/ /files/4-apps/
COPY ./build/4-apps/40-moonraker/get-packages.sh /build/4-apps/40-moonraker/get-packages.sh

RUN --mount=type=cache,sharing=locked,target=/root/.cache/pip \
    chmod +x /build/4-apps/40-moonraker/get-packages.sh && \
    /build/4-apps/40-moonraker/get-packages.sh


###############################################################
# app-remote-display prepares Remote Display app files

FROM build-base AS app-remote-display

COPY ./build/4-apps/50-remote-display/* /build/
COPY ./files/4-apps/home/rinkhals/apps/50-remote-display/index.vnc /files/4-apps/home/rinkhals/apps/50-remote-display/index.vnc
COPY ./files/4-apps/home/rinkhals/apps/50-remote-display/app.json /files/4-apps/home/rinkhals/apps/50-remote-display/app.json
RUN chmod +x /build/get-novnc.sh && \
    /build/get-novnc.sh


###############################################################
# build-swu-installer builds the Installer tool SWU files

FROM build-base AS build-swu-installer

COPY ./build/swu-tools/installer/ /build/swu-tools/installer/
COPY ./build/*.* /build/
COPY --from=rinkhals-base /files/1-buildroot/ /files/1-buildroot/
COPY --from=build-python-armv7 /files/2-python/ /files/2-python/
COPY ./files/3-rinkhals/ /files/3-rinkhals/
COPY ./files/*.* /files/

RUN chmod +x /build/swu-tools/installer/build-swu.sh
RUN KOBRA_MODEL_CODE=K3 /build/swu-tools/installer/build-swu.sh /swu/installer-k2p-k3.swu
RUN KOBRA_MODEL_CODE=K3M /build/swu-tools/installer/build-swu.sh /swu/installer-k3m.swu
RUN KOBRA_MODEL_CODE=KS1 /build/swu-tools/installer/build-swu.sh /swu/installer-ks1.swu


###############################################################
# build-swu-tools builds the tools SWU files

FROM build-base AS build-swu-tools

COPY ./build/swu-tools/ /build/swu-tools/
COPY ./build/*.* /build/
COPY --from=rinkhals-base /files/1-buildroot/ /files/1-buildroot/
COPY --from=build-python-armv7 /files/2-python/ /files/2-python/
COPY ./files/3-rinkhals/ /files/3-rinkhals/
COPY ./files/*.* /files/

RUN <<EOT
    set -e
    chmod +x /build/swu-tools/*/build-swu.sh
    for tool in $(ls /build/swu-tools/); do
        if [ "$tool" = "installer" ]; then
            continue
        fi
        KOBRA_MODEL_CODE=K3 /build/swu-tools/$tool/build-swu.sh /swu/${tool}-k2p-k3.swu
        KOBRA_MODEL_CODE=K3M /build/swu-tools/$tool/build-swu.sh /swu/${tool}-k3m.swu
        KOBRA_MODEL_CODE=KS1 /build/swu-tools/$tool/build-swu.sh /swu/${tool}-ks1.swu
    done
    cd /swu
    for suffix in k2p-k3 k3m ks1; do
        zip -j "tools-${suffix}.zip" *.swu -i "*-${suffix}.swu"
    done
EOT


###############################################################
# prepare-bundle collects all files and prepares a bundle

FROM build-base AS prepare-bundle

COPY --from=rinkhals-base /files/1-buildroot/ /bundle/rinkhals/
COPY --from=build-python-armv7 /files/2-python/ /bundle/rinkhals/
COPY --from=app-mainsail /files/4-apps/ /bundle/rinkhals/
COPY --from=app-fluidd /files/4-apps/ /bundle/rinkhals/
COPY --from=app-moonraker /files/4-apps/ /bundle/rinkhals/
COPY --from=app-moonraker-armv7 /files/4-apps/ /bundle/rinkhals/
COPY --from=app-remote-display /files/4-apps/ /bundle/rinkhals/
COPY ./files/3-rinkhals /bundle/rinkhals/
COPY ./files/4-apps /bundle/rinkhals/
COPY ./files/*.* /bundle/

# Remove everything but shell patches
RUN find /bundle/rinkhals/opt/rinkhals/patches -type f ! -name "*.sh" -exec rm {} +

# Validate and set Rinkhals version
ARG RINKHALS_VERSION="dev"
RUN <<EOT
    set -e
    if [ -z "$RINKHALS_VERSION" ] || {
        [ "$RINKHALS_VERSION" != "dev" ] &&
        ! echo "$RINKHALS_VERSION" | grep -Eq '^[0-9]{8}_[0-9]{2}(_[a-z0-9_-]+)?$' &&
        ! echo "$RINKHALS_VERSION" | grep -Eq '^[0-9a-f]{40}$'
    } || {
        echo "$RINKHALS_VERSION" | grep -Eq '^[0-9]{8}_[0-9]{2}(_[a-z0-9_-]+)?$' &&
        ! date -d "$(echo "$RINKHALS_VERSION" | cut -d'_' -f1)" +"%Y%m%d" >/dev/null 2>&1
    }; then
        echo "Invalid version (must be 'yyyymmdd_nn', 'yyyymmdd_nn_tag', Git commit ID, or 'dev'): $RINKHALS_VERSION"
        exit 1
    else
        echo "$RINKHALS_VERSION" > /bundle/.version
        echo "$RINKHALS_VERSION" > /bundle/rinkhals/.version
    fi
EOT


###############################################################
# files-export creates the files export image

FROM scratch AS files-export

COPY --from=prepare-bundle /bundle/ /


###############################################################
# build-swu builds the main firmware SWU files

FROM prepare-bundle AS build-swu

COPY ./build/tools.sh /
RUN <<EOT
    set -e
    . /tools.sh
    mkdir -p /swu
    prepare_tgz /bundle /swu
    compress_swu K3 /swu/update-k2p-k3.swu &
    compress_swu KS1 /swu/update-ks1.swu &
    compress_swu K3M /swu/update-k3m.swu &
    wait $(jobs -p)
EOT


###############################################################
# swu-export creates the SWU build export image

FROM scratch AS swu-export

COPY --from=build-swu-installer /swu/ /
COPY --from=build-swu-tools /swu/*.zip /
COPY --from=build-swu /swu/ /
