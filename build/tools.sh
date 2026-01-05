#!/bin/sh

prepare_tgz() {
    UPDATE_DIRECTORY=${1:-/tmp/update_swu}
    SWU_DIR=${2:-/build/dist}

    mkdir -p $SWU_DIR/update_swu
    rm -rf $SWU_DIR/update_swu/*

    cd $UPDATE_DIRECTORY
    tar -cf $SWU_DIR/update_swu/setup.tar --exclude='setup.tar' .
    gzip $SWU_DIR/update_swu/setup.tar

    md5sum $SWU_DIR/update_swu/setup.tar.gz | awk '{ print $1 }' > $SWU_DIR/update_swu/setup.tar.gz.md5
}
compress_swu() {
    KOBRA_MODEL_CODE=$1
    SWU_PATH=${2:-/build/dist/update.swu}

    SWU_DIR=$(dirname $SWU_PATH)
    SWU_NAME=$(basename $SWU_PATH)

    rm -f $SWU_PATH
    cd $SWU_DIR

    if [ "$KOBRA_MODEL_CODE" = "K2P" ] || [ "$KOBRA_MODEL_CODE" = "K3" ] || [ "$KOBRA_MODEL_CODE" = "K3V2" ]; then
        zip -0 -P U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w= -r $SWU_NAME update_swu
    elif [ "$KOBRA_MODEL_CODE" = "KS1" ] || [ "$KOBRA_MODEL_CODE" = "KS1M" ]; then
        zip -0 -P U2FsdGVkX1+lG6cHmshPLI/LaQr9cZCjA8HZt6Y8qmbB7riY -r $SWU_NAME update_swu
    elif [ "$KOBRA_MODEL_CODE" = "K3M" ]; then
        zip -0 -P 4DKXtEGStWHpPgZm8Xna9qluzAI8VJzpOsEIgd8brTLiXs8fLSu3vRx8o7fMf4h6 -r $SWU_NAME update_swu
    else
        echo "Unknown Kobra model code: $KOBRA_MODEL_CODE"
        exit 1
    fi
}

build_swu() {
    KOBRA_MODEL_CODE=$1
    UPDATE_DIRECTORY=${2:-/tmp/update_swu}
    SWU_PATH=${3:-/build/dist/update.swu}

    SWU_DIR=$(dirname $SWU_PATH)

    prepare_tgz $UPDATE_DIRECTORY $SWU_DIR
    compress_swu $KOBRA_MODEL_CODE $SWU_PATH
}
