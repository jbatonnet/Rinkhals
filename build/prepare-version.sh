#!/bin/sh

set -e

SCRIPT_DIRECTORY=$(dirname $0)
BASE_DIRECTORY=$(dirname $SCRIPT_DIRECTORY)

get_printer_model_name() {
    case "$1" in
        "K2P") echo "Kobra 2 Pro" ;;
        "K3") echo "Kobra 3" ;;
        "K3M") echo "Kobra 3 Max" ;;
        "K3V2") echo "Kobra 3 V2" ;;
        "KS1") echo "Kobra S1" ;;
        "KS1M") echo "Kobra S1 Max" ;;
    esac
}
get_printer_swu_password() {
    case "$1" in
        "K2P") echo "U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w=" ;;
        "K3") echo "U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w=" ;;
        "K3M") echo "4DKXtEGStWHpPgZm8Xna9qluzAI8VJzpOsEIgd8brTLiXs8fLSu3vRx8o7fMf4h6" ;;
        "K3V2") echo "U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w=" ;;
        "KS1") echo "U2FsdGVkX1+lG6cHmshPLI/LaQr9cZCjA8HZt6Y8qmbB7riY" ;;
        "KS1M") echo "U2FsdGVkX1+lG6cHmshPLI/LaQr9cZCjA8HZt6Y8qmbB7riY" ;;
    esac
}

MANIFEST_PATH=$BASE_DIRECTORY/files/3-rinkhals/manifest.json
MANIFEST=$(cat $MANIFEST_PATH | sed -r 's/^\s*\/\/.*//')


################
# Create patches

PRINTER_MODEL_CODES=$(echo $MANIFEST | jq -r ".supported_models | keys[]")
for PRINTER_MODEL_CODE in $PRINTER_MODEL_CODES; do
    echo "Processing $PRINTER_MODEL_CODE..."

    SUPPORTED_VERSIONS=$(echo $MANIFEST | jq -r ".supported_models.$PRINTER_MODEL_CODE[]")

    FIRMWARE_REPOSITORY=$(echo $MANIFEST | jq -r ".firmware_repositories.$PRINTER_MODEL_CODE")
    FIRMWARE_REPOSITORY_MANIFEST=$(curl -s $FIRMWARE_REPOSITORY | jq -cr .)
    FIRMWARE_REPOSITORY_MANIFEST=$(echo $FIRMWARE_REPOSITORY_MANIFEST | tr -d '\n')

    PRINTER_SWU_PASSWORD=$(get_printer_swu_password $PRINTER_MODEL_CODE)

    for SUPPORTED_VERSION in $SUPPORTED_VERSIONS; do
        echo "  $SUPPORTED_VERSION:"

        VERSION_MANIFEST=$(echo $FIRMWARE_REPOSITORY_MANIFEST | jq -cr ".firmwares[] | select(.version == \"$SUPPORTED_VERSION\")" | tr -dc '[[:print:]]')
        if [ -z "$VERSION_MANIFEST" ]; then
            echo "    No SWU found for ${PRINTER_MODEL_CODE}_${SUPPORTED_VERSION}"
            #exit 1
            continue
        fi

        TMP_VERSION_DIRECTORY=$BASE_DIRECTORY/build/tmp/versions
        mkdir -p $TMP_VERSION_DIRECTORY

        VERSION_PATH=${TMP_VERSION_DIRECTORY}/${PRINTER_MODEL_CODE}_${SUPPORTED_VERSION}.swu
        if [ ! -f $VERSION_PATH ]; then
            VERSION_MD5=$(echo $VERSION_MANIFEST | jq -r ".md5")
            VERSION_URL=$(echo $VERSION_MANIFEST | jq -r ".url")

            echo "    Downloading $VERSION_URL to $VERSION_PATH..."
            curl -s -o $VERSION_PATH $VERSION_URL

            CALCULATED_MD5=$(md5sum $VERSION_PATH | awk '{ print $1 }')
            if [ "$CALCULATED_MD5" != "$VERSION_MD5" ]; then
                echo "    MD5 checksum mismatch for $VERSION_PATH (expected $VERSION_MD5 but got $CALCULATED_MD5)"
                break
            fi
        fi

        VERSION_DIRECTORY=${TMP_VERSION_DIRECTORY}/${PRINTER_MODEL_CODE}_${SUPPORTED_VERSION}
        if [ ! -f $VERSION_DIRECTORY/update_swu/.complete ]; then
            unzip -o -P "$PRINTER_SWU_PASSWORD" $VERSION_PATH -d $VERSION_DIRECTORY
            tar zxf $VERSION_DIRECTORY/update_swu/setup.tar.gz -C $VERSION_DIRECTORY/update_swu
            touch $VERSION_DIRECTORY/update_swu/.complete
        fi

        # Patch K3SysUi
        DEST_K3SYSUI_PATH=$BASE_DIRECTORY/files/3-rinkhals/opt/rinkhals/patches/K3SysUi.${PRINTER_MODEL_CODE}_${SUPPORTED_VERSION}
        if [ ! -f $DEST_K3SYSUI_PATH ]; then
            cp -f $VERSION_DIRECTORY/update_swu/app/K3SysUi $DEST_K3SYSUI_PATH
        fi

        python $BASE_DIRECTORY/files/3-rinkhals/opt/rinkhals/scripts/create-patch.py $DEST_K3SYSUI_PATH

        # Patch gkapi
        DEST_GKAPI_PATH=$BASE_DIRECTORY/files/3-rinkhals/opt/rinkhals/patches/gkapi.${PRINTER_MODEL_CODE}_${SUPPORTED_VERSION}
        if [ ! -f $DEST_GKAPI_PATH ]; then
            cp -f $VERSION_DIRECTORY/update_swu/app/gkapi $DEST_GKAPI_PATH
        fi
        
        python $BASE_DIRECTORY/files/3-rinkhals/opt/rinkhals/scripts/create-patch.py $DEST_GKAPI_PATH

        # TODO: Hash printer.cfg

    done

done


################
# Adjust the supported printers (README, tools.sh, ...)

cat $BASE_DIRECTORY/files/3-rinkhals/tools.sh | grep -vF " && SUPPORTED=1" > $BASE_DIRECTORY/files/3-rinkhals/tools.sh.tmp
mv -f $BASE_DIRECTORY/files/3-rinkhals/tools.sh.tmp $BASE_DIRECTORY/files/3-rinkhals/tools.sh

PRINTER_MODEL_CODES=$(echo $MANIFEST | jq -r ".supported_models | keys[]")
for PRINTER_MODEL_CODE in $PRINTER_MODEL_CODES; do
    PRINTER_MODEL_NAME=$(get_printer_model_name $PRINTER_MODEL_CODE)
    SUPPORTED_VERSIONS=$(echo $MANIFEST | jq -r ".supported_models.$PRINTER_MODEL_CODE[]")

    # README.md
    SUPPORTED_VERSIONS_FORMATTED=$(echo $SUPPORTED_VERSIONS | awk 'BEGIN { FS=" "; OFS="` `" } {$1=$1} 1')
    sed -i -r "s/(\| $PRINTER_MODEL_NAME[^\|]+\|)[^\|]+\|/\1 \`$SUPPORTED_VERSIONS_FORMATTED\` |/" $BASE_DIRECTORY/README.md

    # tools.sh
    for SUPPORTED_VERSION in $SUPPORTED_VERSIONS; do
        SUPPORT_LINE='[ "$KOBRA_MODEL_CODE" = "'$PRINTER_MODEL_CODE'" ] \&\& [ "$KOBRA_VERSION" = "'$SUPPORTED_VERSION'" ] \&\& SUPPORTED=1'
        SED_LINE='s|SUPPORTED=0|SUPPORTED=0\n    '$SUPPORT_LINE'|'
        sed -i "$SED_LINE" $BASE_DIRECTORY/files/3-rinkhals/tools.sh
    done
done
