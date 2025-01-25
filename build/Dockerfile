# docker build -t ghcr.io/jbatonnet/rinkhals/build -f build/Dockerfile build
# docker push ghcr.io/jbatonnet/rinkhals/build

FROM debian:12.8

RUN apt update && \
    apt install -y git wget jq rclone zip xz-utils python3 python3-pip texinfo && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --no-cache-dir pwntools

ARG BINUTILS_VERSION=2.38
ARG BINUTILS_ARCH=arm

RUN cd /tmp && \
    wget -nc https://ftp.gnu.org/gnu/binutils/binutils-$BINUTILS_VERSION.tar.gz && \
    tar xf binutils-$BINUTILS_VERSION.tar.gz && \
        \
    mkdir binutils-build && \
    cd binutils-build && \
        \
    export AR=ar && \
    export AS=as && \
        \
    ../binutils-$BINUTILS_VERSION/configure \
        --prefix=/usr/local \
        --target=$BINUTILS_ARCH-unknown-linux-gnu \
        --disable-static \
        --disable-multilib \
        --disable-werror \
        --disable-nls && \
        \
    MAKE=gmake && \
    hash gmake || MAKE=make && \
        \
    $MAKE -j clean all && \
    $MAKE install && \
        \
    rm -rf binutils-$BINUTILS_VERSION.tar.gz binutils-$BINUTILS_VERSION binutils-build
