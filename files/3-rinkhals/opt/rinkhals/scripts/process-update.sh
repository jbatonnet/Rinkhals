#!/bin/sh

SCRIPT_DIRECTORY=$(dirname $0)


# TODO: Loop through printers
# TODO: Check update
# TODO: Download update
# TODO: Check MD5
# TODO: Add release notes to the docs
# TODO: Add compatibility to tools.sh
# TODO: Adjust README compatibility table
# TODO: Hash printer.cfg


# 0x1F628E70311F52D934E851D232F66DA3
UPDATE_FILE=/mnt/d/Sync/Julien/Projects/Kobra/KS1/Firmwares/KS1_2.5.6.0.swu
UPDATE_PASSWORD="U2FsdGVkX1+lG6cHmshPLI/LaQr9cZCjA8HZt6Y8qmbB7riY"

# 0x1F628E70311F52D934E851D232F66DA3
#UPDATE_FILE=/mnt/d/Sync/Julien/Projects/Kobra/K3M/Firmwares/K3M_2.4.8.4.swu
#UPDATE_PASSWORD="4DKXtEGStWHpPgZm8Xna9qluzAI8VJzpOsEIgd8brTLiXs8fLSu3vRx8o7fMf4h6"

# 0x1F628E70311F52D934E851D232F66DA3
#UPDATE_FILE=/mnt/d/Sync/Julien/Projects/Kobra/K3V2/Firmwares/K3V2_1.0.7.3.swu
#UPDATE_PASSWORD="U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w="


################
# Extract update

UPDATE_NAME=$(basename $UPDATE_FILE)
UPDATE_NAME=${UPDATE_NAME%.swu}

UPDATE_DIRECTORY=/tmp/rinkhals/updates/$UPDATE_NAME

rm -rf $UPDATE_DIRECTORY
mkdir -p $UPDATE_DIRECTORY
unzip -o -P $UPDATE_PASSWORD $UPDATE_FILE -d $UPDATE_DIRECTORY
tar zxf $UPDATE_DIRECTORY/update_swu/setup.tar.gz -C $UPDATE_DIRECTORY/update_swu


################
# Create patch

#cp $UPDATE_DIRECTORY/update_swu/app/K3SysUi $UPDATE_DIRECTORY/K3SysUi.$UPDATE_NAME
#python $SCRIPT_DIRECTORY/create-patch.py $UPDATE_DIRECTORY/K3SysUi.$UPDATE_NAME

cp $UPDATE_DIRECTORY/update_swu/app/K3SysUi $SCRIPT_DIRECTORY/../patches/K3SysUi.$UPDATE_NAME
python $SCRIPT_DIRECTORY/create-patch.py $SCRIPT_DIRECTORY/../patches/K3SysUi.$UPDATE_NAME


# TODO: Add release notes
# TODO: Create a JSON file with versions metadata
