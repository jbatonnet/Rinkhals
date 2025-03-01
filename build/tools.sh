#!/bin/sh

build_swu() {
    KOBRA_MODEL_CODE=$1
    UPDATE_DIRECTORY=${2:-/tmp/update_swu}
    SWU_PATH=${3:-/build/dist/update.swu}

    SWU_DIR=$(dirname $SWU_PATH)
    SWU_NAME=$(basename $SWU_PATH)

    mkdir -p $SWU_DIR/update_swu
    rm -rf $SWU_DIR/update_swu/*

    cd $UPDATE_DIRECTORY
    tar -czf $SWU_DIR/update_swu/setup.tar.gz --exclude='setup.tar.gz' .

    rm -f $SWU_PATH
    cd $SWU_DIR

    if [ "$KOBRA_MODEL_CODE" = "K2P" ] || [ "$KOBRA_MODEL_CODE" = "K3" ]; then
        zip -P U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w= -r $SWU_NAME update_swu
    elif [ "$KOBRA_MODEL_CODE" = "KS1" ]; then
        zip -P U2FsdGVkX1+lG6cHmshPLI/LaQr9cZCjA8HZt6Y8qmbB7riY -r $SWU_NAME update_swu
    else
        echo "Unknown Kobra model code: $KOBRA_MODEL_CODE"
        exit 1
    fi
}
