#
# Main Dockerfile for building Rinkhals
#
# This multi-stage Dockerfile includes all steps to go from a clean repository to an installable SWU package.
# Note: Buildkit is required, but should already be enabled in most Docker installations.
#
# Enable QEMU for ARMv7 stages (needed once per session):
# - docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
#
# Building with local filesystem output (https://docs.docker.com/build/exporters/local-tar/):
# - docker build --output type=local,dest=./build/dist .
#
# Building a release:
# - docker build --build-arg version=yyyymmdd_nn --output type=local,dest=./build/dist .
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
# - docker run --rm -it -e KOBRA_IP=x.x.x.x --mount type=bind,ro,source=.\build,target=/build --entrypoint=/bin/sh rclone/rclone:1.69.1 /build/deploy-dev.sh
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

###############################################################
# buildroot builds the root filesystem and core packages
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
        libncurses5-dev libdevmapper-dev libsystemd-dev libssl-dev libfdt-dev && \
    rm -rf /var/lib/apt/lists/*

# Sometimes Buildroot needs proper locale, e.g. when using a toolchain based on glibc
RUN locale-gen en_US.utf8

ADD https://gitlab.com/buildroot.org/buildroot.git#2023.02.6 /buildroot
WORKDIR /buildroot

# Patch buildroot to enable the gcc package (and change a few others)
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
        rm -rf /buildroot/dl
        make clean
    fi
EOT

###############################################################
# buildroot-rebuild rebuilds selected buildroot packages
FROM buildroot-build AS buildroot-rebuild
ARG rebuild=""
ARG clean_buildroot

# Use files from rebuild/ (if it exists) to rebuild without invalidating the base image
# Note: pattern matching 'rebuil[d]' is a trick to copy-if-exists
COPY ./build/1-buildroot/rebuil[d]/.config /buildroot/
COPY ./build/1-buildroot/rebuil[d]/busybox.config /buildroot/
COPY ./build/1-buildroot/rebuil[d]/external/ /external/

# Perform dirclean and rebuild for selected packages
# https://buildroot.org/downloads/manual/manual.html#rebuild-pkg
ENV KCONFIG_NOSILENTUPDATE=1
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

###############################################################
# build-python-armv7 builds Python dependencies that require ARMv7 compilation
FROM --platform=linux/arm/v7 ghcr.io/jbatonnet/armv7-uclibc:rinkhals AS build-python-armv7

COPY ./build/2-python/get-packages.sh /build/2-python/get-packages.sh
RUN --mount=type=cache,sharing=locked,target=/root/.cache/pip \
    chmod +x /build/2-python/get-packages.sh && \
    /build/2-python/get-packages.sh

###############################################################
# build-base provides the basis for common build steps
FROM debian:12.10 AS build-base
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
# prepare-bundle collects all files and prepares a bundle
FROM build-base AS prepare-bundle

COPY --from=buildroot-rebuild /files/1-buildroot/ /bundle/rinkhals/
COPY --from=build-python-armv7 /files/2-python/ /bundle/rinkhals/
COPY --from=app-mainsail /files/4-apps/ /bundle/rinkhals/
COPY --from=app-fluidd /files/4-apps/ /bundle/rinkhals/
COPY --from=app-moonraker /files/4-apps/ /bundle/rinkhals/
COPY --from=app-moonraker-armv7 /files/4-apps/ /bundle/rinkhals/
COPY ./files/3-rinkhals /bundle/rinkhals/
COPY ./files/4-apps /bundle/rinkhals/
COPY ./files/*.* /bundle/

# Remove everything but shell patches
RUN find /bundle/rinkhals/opt/rinkhals/patches -type f ! -name "*.sh" -exec rm {} +

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

# Validate and set Rinkhals version
ARG version="dev"
RUN <<EOT
    set -e
    if [ -z "$version" ] || {
        [ "$version" != "dev" ] &&
        ! echo "$version" | grep -Eq '^[0-9]{8}_[0-9]{2}$' &&
        ! echo "$version" | grep -Eq '^[0-9a-f]{40}$'
    } || {
        echo "$version" | grep -Eq '^[0-9]{8}_[0-9]{2}$' &&
        ! date -d "$(echo "$version" | cut -d'_' -f1)" +"%Y%m%d" >/dev/null 2>&1
    }; then
        echo "Invalid version (must be 'yyyymmdd_nn', Git commit ID, or 'dev'): $version"
        exit 1
    else
        echo "$version" > /bundle/.version
        echo "$version" > /bundle/rinkhals/.version
    fi
EOT

###############################################################
# files-export creates the files export image
FROM scratch AS files-export
COPY --from=prepare-bundle /bundle/ /

###############################################################
# build-swu
FROM prepare-bundle AS build-swu
COPY ./build/tools.sh /
RUN <<EOT
    set -e
    . /tools.sh
    mkdir -p /swu
    prepare_tgz /bundle /swu
    compress_swu K3 /swu/update-k2p-k3.swu &
    compress_swu KS1 /swu/update-ks1.swu &
    wait $(jobs -p)
EOT

###############################################################
# swu-export creates the firmware updates export image
FROM scratch AS swu-export
COPY --from=build-swu /swu/ /
