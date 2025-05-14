---
title: Rinkhals Installer
---

Starting from release 20250514_01, Rinkhals is released as a stadard SWU update file and an Installer tool.

The installer allows you to
- Quickly install / update / uninstall Rinkhals versions
- Update your printer firmware
- Perform some operations using tools (debug bundle, reset configuration, backups, ...)
- Collect some diagnostics in case something seems wrong and provide known fixes

The installer takes about 10s to start. Once started, a SSH server will be listening on port 2222.

## Install & Updates

To install last Rinkhals version:
Home > Install & Updates > Rinkhals / Manage > Click on latest > Download > Install

You can enable test versions to list beta / testing version from GitHub. Those will be anounced on the Discord server.

## Tools

- Generate a Debug Bundle > Generate a ZIP of useful logs / states of your pritner on the USB drive
- Reset Rinkhals configuration > Create a backup of your configuration on the USB drive and resets printer, moonraker and other configurations to default
- Backup partitions > Create a backup of /userdata and /useremain partitions (excluding gcodes, Rinkhals and other less important things) on the USB drive
- Clean old Rinkhals > Remove older Rinkhals versions, keeping only the last 3 version including the currently running one
- Uninstall Rinkhals > Completely remove Rinkhals files and configuration and revert back to stock firmware

## Diagnostics

-
