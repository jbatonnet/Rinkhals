import os

class Version:

    # Parses the common plugin version from the setup.py file.
    # Throws if the file can't be found or the version string can't be found.
    # This logic is shared with the moonraker installer!
    @staticmethod
    def GetPluginVersion(repoRoot):
        # Since OctoPrint says the version must be in the setup.py file, we share the same file to reduce any duplication.
        setupFilePath = os.path.join(repoRoot, "setup.py")
        if os.path.exists(setupFilePath) is False:
            raise Exception("Failed to find our repo root setup file to parse the version string. Expected Path: "+setupFilePath)

        # Read the file, find the version string.
        expectedVersionKey = "plugin_version"
        versionLine = None
        with open(setupFilePath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for l in lines:
                if l.startswith(expectedVersionKey):
                    versionLine = l
                    break

        # Make sure we found it.
        if versionLine is None:
            raise Exception("Failed to find a line that starts with '"+expectedVersionKey+"' in setup file: "+setupFilePath)

        # Parse the line
        firstQuote = versionLine.find('"')
        if firstQuote == -1:
            raise Exception("Failed to first quote in version line '"+versionLine+"'")
        firstQuote += 1 # Move past it
        secondQuote = versionLine.find('"', firstQuote)
        if secondQuote == -1:
            raise Exception("Failed to second quote in version line '"+versionLine+"'")

        # Parse the version string
        return versionLine[firstQuote:secondQuote]
