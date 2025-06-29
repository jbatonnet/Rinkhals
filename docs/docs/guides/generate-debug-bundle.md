---
title: How to generate a debug bundle?
---

## What is a debug bundle?

A debug bundle is a ZIP file containing all recent logs and information about your printer. It is really useful when trying to diagnose a situation as it usually captures all the details needed to understand your printer model, context and the traces of the actions leading to a specific issue or situation.

Debug bundle are usually safe to share publicly. No private or sensitive information are voluntarily collected during its generation. Please note that if some apps are logging some URLs or token in their main log file, this one might be collected and end up in the bundle. In this case it's the app developer responsibility not to log the secret information or log it where it won't be collected.

Rinkhals developers might ask you to generate one if you report an issue during testing or general usage. You can either generate it and send it to them or send individual logs if you prefer, but the logs collection has been automated to help the developers.

## How to generate it?

There are 2 ways to generate a debug bundle:

### 1. Using the Rinkhals Installer

Refer to [this page](../Rinkhals/rinkhals-installer.md#tools) to use the Debug Bundle tool from the installer.

### 2. Using the Debug Bundle SWU tool

A SWU tool to directly collect a Debug Bundle on a connected USB drive is also provided.
To use it, go to [GitHub releases](https://github.com/jbatonnet/Rinkhals/releases) and download the tools-*.zip for your printer. Extract the ZIP file and get the debug bundle SWU file.

Then you can follow the same steps as during a [manual installation](../Rinkhals/installation-and-firmware-updates.md). Copy the SWU as update.swu in a `aGVscF9zb3Nf` directory on a FAT32 USB drive, plug it in your printer.

Once running you'll hear 2 beeps, the first one for the tool startup and the second one for its completion.

## Content

A debug bundle contains:

- Rinkhals
    - Installation log
    - Current version
    - Installation size
    - For each installed version
        - Startup log
        - Anycubic process logs
        - App logs
- Logs in /tmp if any
- General printer information (CPU, Memory, Network config, Kernel info, Disk usage, Current processes, Kernel logs)
- List of installed files, not their content (/userdata, /useremain and static partitions)
- Printer info
    - LAN mode
    - Firmware version
    - Various printer configuration files
- Webcam info (List, Resolutions)

