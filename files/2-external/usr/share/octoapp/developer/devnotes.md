
## Setup The Pre-Commit Hooks
- `pip install pre-commit`
- `pre-commit install`

## For PY 3
- Use `python3 -m venv py3venv` to create an environment in the current dir
- Use `source py3venv/bin/activate` to activate
- Pip install deps from the setup.py file
- Pip install octoprint (to make F5 debugging easier)
- In VS, open the "select python interpreter" dialog and pick the environment.


## For PY 2
- Use `virtualenv py2venv` to create an env
- Use `source py2venv/bin/activate` to activate
- Pip install deps from the setup.py file
- Pip install octoprint (to make F5 debugging easier)
- In VS, open the "select python interpreter" dialog and pick the environment.


## For Moonraker
- Install into moonraker using the normal install script
- Open VS code, point it to the device, and open the repo folder
- Set the virt env in VS code to be the one created by the install script.
- Use F5 to debug and run


## Before checking in:
- Run in py2 env
- Run in py3 env
- Make sure http works, ws works (printer console), webcam works (stream and snapshot)

## OctoPi Useful Commands
- tail -f ./.octoprint/logs/octoprint.log
- source ./oprint/bin/activate

### For notes about shared dependencies with OctoPrint, see setup.py

<br/>
<br/>
<br/>

# Plugin Development Details


This repo contains code shared by both OctoPrint and Moonraker. Ideally most of the logic lives in the octoapp module, and thus is shared. Any code that's specific to Moonraker or OctoPrint, is found in the octoprint_ or moonraker_ modules.

## Major OctoPrint and Moonraker Differences

The biggest difference between OctoPrint and Moonraker is how the repo is set up and how it's ran.

### OctoPrint Setup

OctoPrint installs and sets up the plugin using the setup.py file. The setup process is all handled by OctoPrint control by the user via the UI. OctoPrint will clone the head of master, install the required python packages from the setup.py file, and then restart to run the plugin. All the information about the OctoPrint server port, webcam details, and such are all able to be pulled from OctoPrint in the plugin code.

### Moonraker Setup

Moonraker currently requires the user to do a more advance setup. Either the user is required to ssh into the device, clone the repo, and then run the install script, or a tool like KIAUH can be used.

The install script must manually install all required system and python packages. It also must figure out the current Moonraker, Mailsail, crowsnest, and Fluidd configs to create the OctoApp config. Finally must setup and run the systemd service that will run the OctoApp host.

### OctoPrint Update

For updates, the user is notified via a web message when there's an update. The update process uses the GitHub releases to find and pull updates. When the repo is updated to the latest release tag, the PY packages required by OctoPrint are updated/installed and the system restarts.

### Moonraker Update

For updates, first our plugin needs to register with Fluidd and Mailsail to be kept track of. The update manager will follow a branch, and will inform users if the current commit they are on is different than the head of the branch.

On update, the repo is pulled to the head of the branch. The install.sh script is then parsed, looking for a `PKGLIST` var. If found, the system packages required will be installed/updated to the versions specified. For python packages, the update process will use the requirements.txt file in the repo to install/update python packages required into the virtual environment. Note that the install.sh script IS NOT ran for updates.

### OctoPrint Host

OctoPrint hosts our plugin in the same process. The octoprint_octoapp module has all of the required files and extensions that OctoPrint requires. Since we are hosted in OctoPrint, we have to share the process, but we also get a lot of runtime nice things for free.

### Moonraker Host

For moonraker, we aren't in process, we run as our own service. The moonraker_octoapp module is responsible for setting up the environment required, and hosting the common OctoApp logic.