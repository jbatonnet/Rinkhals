#!/bin/bash



#
# OctoApp for Klipper!
#
# Use this script to install the plugin on a normal device or a Creality device, or to install the companion!
# For a companion install, use the -companion argument.
#
# Simply run ./install.sh from the git repo root directory to get started!
#
# If you need help, feel free to contact us at hello@octoapp.eu
#





#
# The responsibility of this script is to bootstrap the setup by installing the required system libs,
# virtual environment, and py requirements. The core of the setup logic is done by the PY install script.
#

# Set this to terminate on error.
set -e


#
# First things first, we need to detect what kind of OS we are running on. The script works by default with all
# Debian OSs, but some printers with embedded computers run strange embedded OSs, that have a lot of restrictions.
# These must stay in sync with update.sh and uninstall.sh!
#

# The K1 and K1 Max run an OS called Buildroot. We detect that by looking at the os-release file.
# Quick note about bash vars, to support all OSs, we use the most compilable var version. This means we use ints
# where 1 is true and 0 is false, and we use comparisons like this [[ $IS_K1_OS -eq 1 ]]
IS_K1_OS=0
if grep -Fqs "ID=buildroot" /etc/os-release
then
    IS_K1_OS=1
    # On the K1, we always want the path to be /usr/data
    # /usr/share has very limited space, so we don't want to use it.
    # This is also where the github script installs moonraker and everything.
    HOME="/usr/data"
fi

# Next, we try to detect if this OS is the Sonic Pad OS.
# The Sonic Pad runs openwrt. We detect that by looking at the os-release file.
IS_SONIC_PAD_OS=0
if grep -Fqs "sonic" /etc/openwrt_release
then
    IS_SONIC_PAD_OS=1
    # On the K1, we always want the path to be /usr/share, this is where the rest of the klipper stuff is.
    HOME="/usr/share"
fi


# Get the root path of the repo, aka, where this script is executing
OCTOAPP_REPO_DIR=$(readlink -f $(dirname "$0"))

# This is the root of where our py virtual env will be. Note that all OctoApp instances share this same
# virtual environment. This how the rest of the system is, where all other services, even with multiple instances, share the same
# virtual environment. I probably wouldn't have done it like this, but we have to create this before we know what instance we are targeting, so it's fine.
OCTOAPP_ENV="${HOME}/octoapp-env"

# Note that this is parsed by the update process to find and update required system packages on update!
# On update THIS SCRIPT ISN'T RAN, only this line is parsed out and used to install / update system packages.
# For python packages, the `requirements.txt` package is used on update.
# This var name MUST BE `PKGLIST`!!
#
# The python requirements are for the installer and plugin
# The virtualenv is for our virtual package env we create
# The curl requirement is for some things in this bootstrap script.
PKGLIST="python3 python3-pip virtualenv curl"
# For the Creality OS, we only need to install these.
# We don't override the default name, since that's used by the Moonraker installer
# Note that we DON'T want to use the same name as above (not even in this comment) because some parsers might find it.
SONIC_PAD_DEP_LIST="python3 python3-pip"
CREALITY_DEP_LIST="python3 python3-pillow python3-pip"


#
# Console Write Helpers
#
c_default=$(echo -en "\e[39m")
c_green=$(echo -en "\e[92m")
c_yellow=$(echo -en "\e[93m")
c_magenta=$(echo -en "\e[35m")
c_red=$(echo -en "\e[91m")
c_cyan=$(echo -en "\e[96m")

log_header()
{
    echo -e "${c_magenta}$1${c_default}"
}

log_important()
{
    echo -e "${c_yellow}$1${c_default}"
}

log_error()
{
    log_blank
    echo -e "${c_red}$1${c_default}"
    log_blank
}

log_info()
{
    echo -e "${c_green}$1${c_default}"
}

log_blue()
{
    echo -e "${c_cyan}$1${c_default}"
}

log_blank()
{
    echo ""
}

#
# It's important for consistency that the repo root is in set $HOME for the K1 and Sonic Pad
# To enforce that, we will move the repo where it should be.
ensure_creality_os_right_repo_path()
{
    # TODO - re-enable this for the  || [[ $IS_K1_OS -eq 1 ]] after the github script updates.
    if [[ $IS_SONIC_PAD_OS -eq 1 ]]
    then
        # Due to the K1 shell, we have to use grep rather than any bash string contains syntax.
        if echo $OCTOAPP_REPO_DIR |grep "$HOME" - > /dev/null
        then
            return
        else
            log_info "Current path $OCTOAPP_REPO_DIR"
            log_error "For the Creality devices the OctoApp repo must be cloned into $HOME/octoapp"
            log_important "Moving the repo and running the install again..."
            cd $HOME
            # Send errors to null, if the folder already exists this will fail.
            git clone https://github.com/crysxd/OctoApp-Plugin octoapp 2>/dev/null || true
            cd $HOME/octoapp
            # Ensure state
            git reset --hard
            git checkout release
            git pull
            # Run the install, if it fails, still do the clean-up of this repo.
            if [[ $IS_K1_OS -eq 1 ]]
            then
                sh ./install.sh "$@" || true
            else
                ./install.sh "$@" || true
            fi
            installExit=$?
            # Delete this folder.
            rm -fr $OCTOAPP_REPO_DIR
            # Take the user back to the new install folder.
            cd $HOME
            # Exit.
            exit $installExit
        fi
    fi
}

#
# Logic to create / update our virtual py env
#
ensure_py_venv()
{
    log_header "Checking Python Virtual Environment For OctoApp..."
    # If the service is already running, we can't recreate the virtual env so if it exists, don't try to create it.
    # Note that we check the bin folder exists in the path, since we mkdir the folder below but virtualenv might fail and leave it empty.
    OCTOAPP_BIN_PATH="$OCTOAPP_ENV/bin"
    if [ -d $OCTOAPP_BIN_PATH ]; then
        # This virtual env refresh fails on some devices when the service is already running, so skip it for now.
        # This only refreshes the virtual environment package anyways, so it's not super needed.
        #log_info "Virtual environment found, updating to the latest version of python."
        #python3 -m venv --upgrade "${OCTOAPP_ENV}"
        return 0
    fi

    log_info "No virtual environment found, creating one now."
    mkdir -p "${OCTOAPP_ENV}"
    if [[ $IS_K1_OS -eq 1 ]]
    then
        # The K1 requires we setup the virtualenv like this.
        if [[ -f /opt/bin/python3 ]]
        then
            virtualenv -p /opt/bin/python3 --system-site-packages "${OCTOAPP_ENV}"
        else
            python3 /usr/lib/python3.8/site-packages/virtualenv.py -p /usr/bin/python3 --system-site-packages "${OCTOAPP_ENV}"
        fi
    else
        # Everything else can use this more modern style command.
        virtualenv -p /usr/bin/python3 --system-site-packages "${OCTOAPP_ENV}"
    fi
}

#
# Logic to make sure all of our required system packages are installed.
#
install_or_update_system_dependencies()
{
    log_header "Checking required system packages are installed..."

    if [[ $IS_K1_OS -eq 1 ]]
    then
        # The K1 by default doesn't have any package manager. In some cases
        # the user might install opkg via the 3rd party moonraker installer script.
        # But in general, PY will already be installed, so there's no need to try.
        # On the K1, the only we thing we ensure is that virtualenv is installed via pip.
        if [[ -f /opt/bin/opkg ]]
        then
            /opt/bin/opkg update || true
            /opt/bin/opkg install ${CREALITY_DEP_LIST}
        fi
        pip3 install --trusted-host pypi.python.org --trusted-host pypi.org --trusted-host=files.pythonhosted.org --no-cache-dir virtualenv
    elif [[ $IS_SONIC_PAD_OS -eq 1 ]]
    then
        # The sonic pad always has opkg installed, so we can make sure these packages are installed.
        opkg update || true
        opkg install ${SONIC_PAD_DEP_LIST}
        pip3 install virtualenv
    else
        log_important "You might be asked for your system password - this is required to install the required system packages."

        # It seems a lot of printer control systems don't have the date and time set correctly, and then the fail
        # getting packages and other downstream things. We will will use our HTTP API to set the current UTC time.
        # Note that since cloudflare will auto force http -> https, we use https, but ignore cert errors, that could be
        # caused by an incorrect date.
        # Note some companion systems don't have curl installed, so this will fail.
        # KEEP WITH OCTOEVERYWHERE!
        sudo date -s `curl --insecure 'https://octoeverywhere.com/api/util/date' 2>/dev/null` || true

        # These we require to be installed in the OS.
        # Note we need to do this before we create our virtual environment
        sudo apt update || true
        sudo apt install --yes ${PKGLIST}

        # The PY lib Pillow depends on some system packages that change names depending on the OS.
        # The easiest way to do this was just to try to install them and ignore errors.
        # Most systems already have the packages installed, so this only fixes edge cases.
        # Notes on Pillow deps: https://pillow.readthedocs.io/en/latest/installation.html
        log_info "Ensuring zlib is install for Pillow, it's ok if this package install fails."
        sudo apt install --yes zlib1g-dev 2> /dev/null || true
        sudo apt install --yes zlib-devel 2> /dev/null || true
    fi

    log_info "System package install complete."
}

#
# Logic to install or update the virtual env and all of our required packages.
#
install_or_update_python_env()
{
    # Now, ensure the virtual environment is created.
    ensure_py_venv

    # Update pip if needed - we added a note because this takes a while on the sonic pad.
    log_info "Updating PIP if needed... (this can take a few seconds or so)"
    if [[ $IS_K1_OS -eq 1 ]]
    then
        "${OCTOAPP_ENV}"/bin/python -m pip install --trusted-host pypi.python.org --trusted-host pypi.org --trusted-host=files.pythonhosted.org --no-cache-dir --upgrade pip
    else
        "${OCTOAPP_ENV}"/bin/python -m pip install --upgrade pip
    fi

    # Finally, ensure our plugin requirements are installed and updated.
    log_info "Installing or updating required python libs..."
    if [[ $IS_K1_OS -eq 1 ]]
    then
        "${OCTOAPP_ENV}"/bin/pip3 install --trusted-host pypi.python.org --trusted-host pypi.org --trusted-host=files.pythonhosted.org -q -r "${OCTOAPP_REPO_DIR}"/requirements.txt
    else
        "${OCTOAPP_ENV}"/bin/pip3 install -q -r "${OCTOAPP_REPO_DIR}"/requirements.txt
    fi
    log_info "Python libs installed."

    if [[ $IS_K1_OS -ne 1 ]]
    then
        log_info "Attempting to install optinal python libs..."
         "${OCTOAPP_ENV}"/bin/pip3 install -q -r "${OCTOAPP_REPO_DIR}"/requirements_try.txt || PIP_FAILED="true"
        if [ "$PIP_FAILED" = "true" ]
        then 
            log_error "Failed to install optional python libraries. Optional end-to-end encryption for Android notification is not possible. Continuing..." 
        else
            log_info "Python libs installed."  
        fi;
    fi;
}

#
# Logic to ensure the user isn't trying to use this script to setup in OctoPrint.
#
check_for_octoprint()
{
    if [[ $IS_SONIC_PAD_OS -eq 1 ]] || [[ $IS_K1_OS -eq 1 ]]
    then
        # Skip, there's no need and we don't have curl.
        return
    else
        # Do a basic check to see if OctoPrint is running on the standard port.
        # This obviously doesn't work for all OctoPrint setups, but it works for the default ones.
        if curl -s "http://127.0.0.1:5000" >/dev/null ; then
            log_important "Just a second... OctoPrint was detected!"
            log_blank
            log_important "This install script is used to install OctoApp for Mainsail, Fluidd, Moonraker, etc."
            log_important "If you want to install OctoApp for OctoPrint, you need to use OctoPrint's Plugin Manager, found in OctoPrint's web settings UI."
            log_blank
            read -p       "Do you want to continue this setup for Mainsail, Fluidd, Moonraker, etc? [y/n]: " -e result
            log_blank
            if [ "${result^^}" != "Y" ] ; then
                log_info "Stopping install process."
                exit 0
            fi
        fi
    fi
}

log_blank
log_blank
log_blank
echo "ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAog
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAuLi4uLiAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAuJ14iOklJSUlJSUlJSTssImAnLiAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAuJyI7SUlJSTssLCIiXl4i
Iiw6SUlJSUk6Xi4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICciSUlJOyJgJy4uLi4uLi4uLi4uLi4nYF4sSUlJO2AuICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgJyxJSUkiYC4u
Li4uLi4uLi4uLi4uLi4uLi4uLi5gOklJSV4gICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAg
ICAgICAgICAgICAgICAgICAgICAgICAgXklJSSInLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi5g
OklJOycgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAu
LElJOicuLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi5eSUlJYCAgICAgICAgICAgICAgICAg
ICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgOklJLC4uLi4uLi4uLi4uLi4uLi4uLi4u
Li4uLi4uLi4uLi4uLmBJSUlgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAg
ICAgICAgICAgIklJOi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uYElJSS4gICAg
ICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgLklJSWAuLi4uLi4uLi4u
Li4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4sSUksICAgICAgICAgICAgICAgICAgICAgICAKICAg
ICAgICAgICAgICAgICAgICAgIGBJSTsuLi4uLi4uLi4uLidgJy4uLi4uLi4uLi4nYCcuLi4uLi4u
Li4uYElJSS4gICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICBeSUk7
Li4uLi4uLi4uJzpJSUlJYC4uLi4uLmA7SUlJOicuLi4uLi4uLmBJSUkuICAgICAgICAgICAgICAg
ICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgYElJSS4uLi4uLi4uLmBJSUlJSSwuLi4uLi4i
SUlJSUlgLi4uLi4uLi5eSUk7ICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAg
ICAgICAgIC5JSUlgLi4uLi4uLi4uYCIsLF4uLi4uLi4uLmAsLCJgLi4uLi4uLi4uO0lJXiAgICAg
ICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgXklJOi4uLi4uLi4uLi4u
Li4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uYElJSS4gICAgICAgICAgICAgICAgICAgICAgIAogICAg
ICAgICAgICAgICAgICAgICAgIC5JSUknLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4u
LixJSSwgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgO0lJ
YC4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi47SUlgICAgICAgICAgICAgICAgICAg
ICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgIDpJSV4uLi4uLi4uLi4uLi4uLi4uLi4uLi4u
Li4uLi4uLi4uLi4uSUlJYCAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAg
ICAgICAgICBJSUlgLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLjpJSV4gICAgICAg
ICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICBgSUk7Li4uLi4uLi4uLi4u
Li4uLi4uLi4uLi4uLi4uLi4uLi4uLi5eSUk7LiAgICAgICAgICAgICAgICAgICAgICAgCiAgICAg
ICAgIGAiXi4gICAgICAgICAuO0lJXi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4u
LjtJSV4gICAgICAgICAgYCIiLiAgICAgICAgIAogICAgICAgICAiSUlJXi4gICAgICAgLElJOi4u
Li4nJy4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLmAnLi5gSUlJYCAgICAgICAnOklJOy4gICAg
ICAgICAKICAgICAgICAgICc6SUlJIicuICAnOklJOicuLmA7SUknLi4uLi4uLi4uLi4uLi4uLi4u
Li4uLi4uLjpJSSwuLmBJSUkiLiAgLmA6SUlJXiAgICAgICAgICAgCiAgICAgICAgICAgICcsSUlJ
SUlJSUlJIi4uLl5JSUleLi4uXl4nLi4uLi4nYGBgJy4uLi4nLCwnLi4nO0lJLCcuJyxJSUlJSUlJ
STpeLiAgICAgICAgICAgIAogICAgICAgICAgICAgLi5gXiwsLCJgLi4uJzpJSTtgLi4nO0lJIi4u
YCxJSUlJSUk6YC4uXklJOycuLi4sSUk7YC4uJ2AiLCIiYCcuLi4gICAgICAgICAgICAKICAgICAg
ICAgICAgIC4uLi4uLi4uLi4nIklJSSIuLi5gO0lJIi4uIklJSV4nJ147SUk6Jy4sSUk7Jy4uLmA7
SUk6YC4uLi4uLi4uLi4uICAgICAgICAgICAgCiAgICAgICAgICAgICAuJy4uLi4uJ2AsSUlJLCcu
Li5eSUlJXi4uLElJOy4gICAgLiJJSTtgLiJJSTtgLi4uLiJJSUk7XmAuLi4uLicnICAgICAgICAg
ICAgIAogICAgICAgICAgICA6SUk7Oiw6SUlJSTteJy4uLicsSUk7YC4uIklJOy4gICAgICAgXklJ
SScuXklJSSwnLi4uLmA6SUlJSUk7O0lJSWAgICAgICAgICAgICAKICAgICAgICAgICAgLmAiOjtJ
OzoiXicuLi4uLl5JSUksJy4uIklJOy4gICAgICAgICAiSUk7Jy4nLElJSSInLi4uLidgXiwsOiws
XicgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgLi4uLi4uLi5gIklJSTtgLi4nLElJOy4g
ICAgICAgICAgICJJSTtgLi5gOklJSSxeJy4uLi4uLi4uICAgICAgICAgICAgICAgIAogICAgICAg
ICAgICAgICAgYCIiIiIsLDtJSUlJLGAuLiciSUlJIi4gICAgICAgICAgICAgYElJSSwnLi4nXjpJ
SUlJOzo6Ojo7O14gICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICJJSUlJSTs6LF5gLi4u
YCxJSUksLiAgICAgICAgICAgICAgICAuIklJSSxgLi4uJ2BeIiw6Ojo6LCInICAgICAgICAgICAg
ICAgCiAgICAgICAgICAgICAgICAgICAgLi4uLi4uLi4nO0lJO14uICAgICAgICAgICAgICAgICAg
ICAuIklJSUknLi4uICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICdgJyAgICAgICAgICAgICAgICAgICAgICAgICAgJ2BgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCg==
" | base64 -d 2> /dev/null || true 
log_blank
log_header "                                   OctoApp For Klipper "
log_header "                            Based on the OctoEverywhere Plugin"
log_blank
log_blank

# These are helpful for debugging.
if [[ $IS_SONIC_PAD_OS -eq 1 ]]
then
    echo "Running in Sonic Pad OS mode"
fi
if [[ $IS_K1_OS -eq 1 ]]
then
    echo "Running in K1 and K1 Max OS mode"
fi

# Before anything, make sure this repo is cloned into the correct path on Creality OS devices.
# If this is Creality OS and the path is wrong, it will re-clone the repo, run the install again, and exit.
ensure_creality_os_right_repo_path

# Next, make sure our required system packages are installed.
# These are required for other actions in this script, so it must be done first.
install_or_update_system_dependencies

# Check that OctoPrint isn't found. If it is, we want to check with the user to make sure they are
# not trying to setup OctoApp for OctoPrint.
check_for_octoprint

# Now make sure the virtual env exists, is updated, and all of our currently required PY packages are updated.
install_or_update_python_env

# Before launching our PY script, set any vars it needs to know
# Pass all of the command line args, so they can be handled by the PY script.
# Note that USER can be empty string on some systems when running as root. This is fixed in the PY installer.
USERNAME=${USER}
USER_HOME=${HOME}
CMD_LINE_ARGS=${@}
PY_LAUNCH_JSON="{\"OCTOAPP_REPO_DIR\":\"${OCTOAPP_REPO_DIR}\",\"OCTOAPP_ENV\":\"${OCTOAPP_ENV}\",\"USERNAME\":\"${USERNAME}\",\"USER_HOME\":\"${USER_HOME}\",\"CMD_LINE_ARGS\":\"${CMD_LINE_ARGS}\"}"
log_info "Bootstrap done. Starting python installer..."

# Now launch into our py setup script, that does everything else required.
# Since we use a module for file includes, we need to set the path to the root of the module
# so python will find it.
export PYTHONPATH="${OCTOAPP_REPO_DIR}"

# We can't use pushd on Creality OS, so do this.
CURRENT_DIR=${pwd}
cd ${OCTOAPP_REPO_DIR} > /dev/null

# Disable the PY cache files (-B), since they will be written as sudo, since that's what we launch the PY
# installer as. The PY installer must be sudo to write the service files, but we don't want the
# complied files to stay in the repo with sudo permissions.
if [[ $IS_SONIC_PAD_OS -eq 1 ]] || [[ $IS_K1_OS -eq 1 ]]
then
    # Creality OS only has a root user and we can't use sudo.
    ${OCTOAPP_ENV}/bin/python3 -B -m moonraker_installer ${PY_LAUNCH_JSON}
else
    sudo ${OCTOAPP_ENV}/bin/python3 -B -m moonraker_installer ${PY_LAUNCH_JSON}
fi

cd ${CURRENT_DIR} > /dev/null

# Check the output of the py script.
retVal=$?
if [ $retVal -ne 0 ]; then
    log_error "Failed to complete setup. Error Code: ${retVal}"
fi

# Note the rest of the user flow (and terminal info) is done by the PY script, so we don't need to report anything else.
exit $retVal
