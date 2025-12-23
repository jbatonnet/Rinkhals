---
title: Simplyprint support
---

!!! note

    This page should probally be rewritten at some point


## Installing Rinkhals on Anycubic Kobra 3 for SimplyPrint

### Introduction
[//]: # (Writers note: This definitely needs to be rewritten, Rinkhals isn't just for the K3 anymore!)
This guide provides step-by-step instructions for installing **Rinkhals**, a custom firmware with **Moonraker** support, on the **Anycubic Kobra 3** printer. Once installed, the printer can be integrated with **SimplyPrint**, a cloud-based 3D printing management service. Follow this guide carefully to ensure a smooth installation process.

## 1. Download Rinkhals
1. Head to the [Rinkhals GitHub releases page](https://github.com/jbatonnet/Rinkhals/releases).
2. Download the latest release of Rinkhals.

## 2. Prepare the USB Drive
1. Format a USB drive as **FAT32** (MBR, GPT is not supported)
2. Create a directory named `aGVscF9zb3Nf` on the USB drive.

## 3. Install Rinkhals on the Printer
[//]: # (Writers note: Should this be rephrased? Step 1 (Download Rinkhals) already says to download it)
1. Download the version of Rinkhals you want to install.
2. Copy the `update.swu` file into the `aGVscF9zb3Nf` directory on the USB drive.
[//]: # (Writers note: This also needs to be changed)
3. Plug the USB drive into the **Anycubic Kobra 3** printer.
4. You should hear a **beep**, indicating the printer detected the update file.
5. Wait about 20 seconds while the printer prepares the update.
6. A progress bar will appear on the screen.

### Understanding the Installation Result
- **Success**: If the progress bar turns **green** and you hear **two beeps**, the printer will reboot, and **Rinkhals is successfully installed**.
- **Failure**: If the progress bar turns red and you hear **three beeps**, the installation failed. However, the printer should still function normally. You can check for more details in the `aGVscF9zb3Nf/install.log` file on the USB drive.

## 4. Enable SimplyPrint Service
To enable **SimplyPrint**, follow the official [SimplyPrint setup guide](https://simplyprint.io/setup-guide#klipper:3).

## Conclusion
[//]: # (Writers note: Also needs to be updated)
By following this guide, you have successfully installed **Rinkhals** firmware on your **Anycubic Kobra 3** and enabled SimplyPrint functionality. This allows you to take advantage of enhanced features and remote management for your 3D printer. If you encounter any issues, consult the installation logs or the respective support forums.

[//]: # (Writers note: I removed the contribution section, as that's covered in contribute-to-development.md. Also removed footer because it's not consistent with style in other pages)