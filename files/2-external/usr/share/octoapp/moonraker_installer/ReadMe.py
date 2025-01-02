# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#                                                             READ ME
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# This module is responsible for the remainder of the OctoApp for klipper setup process, after the bash script bootstrapped things.
# The module should only be launched by the install.sh bash script, since the install.sh script bootstraps the install process by setting up
# required system packages, the virtual env, and the python packages required. This install module runs in the same service virtual env.
#
# This module handles all arguments passed the install script. Run ./install.sh -help for details.
#
# The moonraker config file and moonraker service file name can be passed to this script, which will then be used instead of the service discovery
# process. Kiauh will pass these args, since it has the logic for the user to control what instance of moonraker they are targeting.
#
# Info about Kiauh, Klipper, Moonraker, etc. from the Kiauh and Moonraker devs, this is the proper way to setup into the system.
#
# If only one instance of klipper and moonraker is running, thing are very easy.
#
# Service Files:
#    1) Every instance of klipper and moonraker both have their own service files.
#          a) If there is only one instance, the service file name is `moonraker.service`
#          b) If there are multiple instances of klipper and thus moonraker, the service file names will be `moonraker-<number or name>.service` and match `klipper-<number or name>.service`
#                i) These names are set in stone one setup from the install, if the user wanted to change them they would have to re-install.
#    2) Thus OctoApp will follow the same naming convention, in regards to the service file names.
#
# Moonraker Data Folders:
#   1) Every klipper and paired moonraker instance has it's own data folder.
#          a) If there is only one instance, data folder defaults to ~/printer_data
#          b) If there are multiple instances of klipper and thus moonraker, the folders will be ~/<name>_data
#   2) For OctoApp since we setup and target per moonraker instance, all per instances files will be stored in the data folder that matches the targeted instance.
#
#
