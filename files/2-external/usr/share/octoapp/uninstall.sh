#!/bin/bash



#
# OctoApp for Klipper!
#
# This script works for any setup of OctoApp, the normal plugin install, companion install, or a Creality install.
# The script will automatically find all OctoApp instances on this device and help you remove them.
#
# If you need help, feel free to contact us at hello@octoapp.eu
#


# These must stay in sync with ./install.sh!
IS_K1_OS=0
if grep -Fqs "ID=buildroot" /etc/os-release
then
    IS_K1_OS=1
fi

c_default=$(echo -en "\e[39m")
c_green=$(echo -en "\e[92m")
c_yellow=$(echo -en "\e[93m")
c_magenta=$(echo -en "\e[35m")
c_red=$(echo -en "\e[91m")
c_cyan=$(echo -en "\e[96m")

echo ""
echo ""
echo -e "${c_yellow}Starting The OctoApp Uninstaller${c_default}"
echo ""
echo ""

# Our installer script has all of the logic to update system deps, py deps, and the py environment.
# So we use it with a special flag to do updating.
if [[ $IS_K1_OS -eq 1 ]]
then
    sh ./install.sh -uninstall
else
    ./install.sh -uninstall
fi