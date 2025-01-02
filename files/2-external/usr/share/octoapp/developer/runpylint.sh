cd ..
echo "Testing OctoApp Module..."
pylint ./octoapp/
echo "Testing OctoPrint Module..."
pylint ./octoprint_octoapp/
echo "Testing Moonraker Module..."
pylint ./moonraker_octoapp/
echo "Testing Moonraker Installer Module..."
pylint ./moonraker_installer/