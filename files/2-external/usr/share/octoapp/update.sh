#!/bin/bash



#
# OctoApp for Klipper!
#
# This script works for any setup of OctoApp, the normal plugin install, companion install, or a Creality install.
# The script will automatically find all OctoApp instances on this device and update them.
#
# If you need help, feel free to contact us at hello@octoapp.eu
#


# These must stay in sync with ./install.sh!
IS_K1_OS=0
if grep -Fqs "ID=buildroot" /etc/os-release
then
    IS_K1_OS=1
fi
IS_SONIC_PAD_OS=0
if grep -Fqs "sonic" /etc/openwrt_release
then
    IS_SONIC_PAD_OS=1
fi

c_default=$(echo -en "\e[39m")
c_green=$(echo -en "\e[92m")
c_yellow=$(echo -en "\e[93m")
c_magenta=$(echo -en "\e[35m")
c_red=$(echo -en "\e[91m")
c_cyan=$(echo -en "\e[96m")

echo ""
echo ""
echo -e "${c_yellow}Starting an OctoApp update!${c_default}"
echo ""
echo ""

# Since our cron update script runs as root and git commands have to be ran by the owner,
# when we run the git commands, we need to make sure we are the right user.
runAsRepoOwner()
{
    # For the sonic pad and k1, we can't use stat or whoami, but there's only one user anyways, root.
    # So always just run it.
    if [[ $IS_SONIC_PAD_OS -eq 1 ]] || [[ $IS_K1_OS -eq 1 ]]
    then
        eval $1
        return
    fi

    updateScriptOwner=$(stat -c %U update.sh)
    if [[ $(whoami) == *${updateScriptOwner}* ]]; then
        eval $1
    else
        repoDir=$(realpath $(dirname "$0"))
        sudo su - ${updateScriptOwner} -c "cd ${repoDir} && $1"
    fi
}

# Pull the repo to get the top of master.
echo "Updating repo and fetching the latest released tag..."
runAsRepoOwner "git fetch --tags"

# Find the latest tag, just for stats now.
# We have to make sure we are on the master branch or the Moonraker updater won't work.
# The Moonraker updater will pull to master on to the latest tag, but we don't do that for now.
latestTaggedCommit=$(runAsRepoOwner "git rev-list --tags --max-count=1")
latestTag=$(runAsRepoOwner "git describe --tags ${latestTaggedCommit}")
currentGitStatus=$(runAsRepoOwner "git describe")
echo "Latest git tag found ${latestTag}, current status ${currentGitStatus}"

# Reset any local changes and pull the head of master.
runAsRepoOwner "git reset --hard --quiet"
runAsRepoOwner "git checkout master --quiet"
runAsRepoOwner "git pull --quiet"

# Our installer script has all of the logic to update system deps, py deps, and the py environment.
# So we use it with a special flag to do updating.
echo "Running the update..."
if [[ $IS_K1_OS -eq 1 ]]
then
    sh ./install.sh -update
else
    ./install.sh -update
fi