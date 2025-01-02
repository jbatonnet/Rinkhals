# coding=utf-8


#
# This is not an installer script!
# If you're trying to install OctoApp for Klipper, you want to use the ./install.sh script!
#
# This PY script is required for the OctoPrint plugin install process.
#
# If you need help, feel free to contact us at hello@octoapp.eu
#

# The plugin's identifier, has to be unique
plugin_identifier = "octoapp"

# The plugin's python package, should be "octoprint_<plugin identifier>", has to be unique
plugin_package = "octoprint_octoapp"

# The plugin's human readable name. Can be overwritten within OctoPrint's internal data via __plugin_name__ in the
# plugin module
plugin_name = "OctoApp"

# The plugin's version. Can be overwritten within OctoPrint's internal data via __plugin_version__ in the plugin module
# Note that this is also parsed by the moonraker module to pull the version, so the string and format must remain the same!
plugin_version = "2.1.6"

# The plugin's description. Can be overwritten within OctoPrint's internal data via __plugin_description__ in the plugin
# module
plugin_description = """The Companion Plugin for OctoApp"""

# The plugin's author. Can be overwritten within OctoPrint's internal data via __plugin_author__ in the plugin module
plugin_author = "Christian Würthner"

# The plugin's author's mail address.
plugin_author_email = "hello@octoapp.eu"

# The plugin's homepage URL. Can be overwritten within OctoPrint's internal data via __plugin_url__ in the plugin module
plugin_url = "https://github.com/crysxd/OctoApp-Plugin/"

# The plugin's license. Can be overwritten within OctoPrint's internal data via __plugin_license__ in the plugin module
plugin_license = "AGPLv3"

# Any additional requirements besides OctoPrint should be listed here.
#
# On 4/13/2023 we updated to only support PY3, which frees us up from a lot of package issues. A lot the packages we depend on only support PY3 now.
#
# websocket_client
# 	For the websocket_client, some older versions seem to have a thread issue that causes the 24 hour disconnect logic to fail, and eventually makes the thread limit get hit.
# 	Version 1.4.0 also has an SSL error in it. https://github.com/websocket-client/websocket-client/issues/857
#	Update: We also found a bug where the ping timer doesn't get cleaned up: https://github.com/websocket-client/websocket-client/pull/918
#   Thus we need version 1.6.0 or higher.
# dnspython
#	We depend on a feature that was released with 2.3.0, so we need to require at least that.
#
# Other lib version notes:
#   pillow - We don't require a version of pillow because we don't want to mess with other plugins and we use basic, long lived APIs.\
#   certifi - We use to keep certs on the device that we need for let's encrypt. So we want to keep it fresh.
#   rsa - OctoPrint 1.5.3 requires RAS>=4.0, so we must leave it at 4.0.
#   httpx - Is an asyncio http lib. It seems to be required by dnspython, but dnspython doesn't enforce it. We had a user having an issue that updated to 0.24.0, and it resolved the issue.
#   urllib3 - There is a bug with parsing headers in versions older than 1.26.? (https://github.com/diyan/pywinrm/issues/269). At least 1.26.6 fixes it, ubt we decide to just stick with a newer version.
#
# Note! These also need to stay in sync with requirements.txt, for the most part they should be the exact same!
plugin_requires = ["pillow", "dnspython>=2.3.0", "pycryptodome>=3.15.0"]

### --------------------------------------------------------------------------------------------------------------------
### More advanced options that you usually shouldn't have to touch follow after this point
### --------------------------------------------------------------------------------------------------------------------

# Additional package data to install for this plugin. The sub folders "templates", "static" and "translations" will
# already be installed automatically if they exist. Note that if you add something here you'll also need to update
# MANIFEST.in to match to ensure that python setup.py sdist produces a source distribution that contains all your
# files. This is sadly due to how python's setup.py works, see also http://stackoverflow.com/a/14159430/2028598
plugin_additional_data = []

# Any additional python packages you need to install with your plugin that are not contained in <plugin_package>.*
# For OctoApp, we need to include or common packages shared between hosts, so OctoPrint copies them into the package folder as well.
plugin_additional_packages = [ "octoapp", "octoapp.Proto" ]

# Any python packages within <plugin_package>.* you do NOT want to install with your plugin
plugin_ignored_packages = []

# Additional parameters for the call to setuptools.setup. If your plugin wants to register additional entry points,
# define dependency links or other things like that, this is the place to go. Will be merged recursively with the
# default setup parameters as provided by octoprint_setuptools.create_plugin_setup_parameters using
# octoprint.util.dict_merge.
#
# Example:
#     plugin_requires = ["someDependency==dev"]
#     additional_setup_parameters = {"dependency_links": ["https://github.com/someUser/someRepo/archive/master.zip#egg=someDependency-dev"]}
additional_setup_parameters = {}

########################################################################################################################

from setuptools import setup

try:
	import octoprint_setuptools
except:
	print("Could not import OctoPrint's setuptools, are you sure you are running that under "
	      "the same python installation that OctoPrint is installed under?")
	import sys
	sys.exit(-1)

setup_parameters = octoprint_setuptools.create_plugin_setup_parameters(
	identifier=plugin_identifier,
	package=plugin_package,
	name=plugin_name,
	version=plugin_version,
	description=plugin_description,
	author=plugin_author,
	mail=plugin_author_email,
	url=plugin_url,
	license=plugin_license,
	requires=plugin_requires,
	additional_packages=plugin_additional_packages,
	ignored_packages=plugin_ignored_packages,
	additional_data=plugin_additional_data
)

if len(additional_setup_parameters):
	from octoprint.util import dict_merge
	setup_parameters = dict_merge(setup_parameters, additional_setup_parameters)

setup(**setup_parameters)
