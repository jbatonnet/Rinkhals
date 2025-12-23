---
title: Installation and firmware updates
---

Check this page to better understand what is Rinkhals and how it works: [How Does Rinkhals work?](installation-and-firmware-updates.md)


## Firmware installation + SWU tools

On the Kobra series of 3D printer, it's possible to sideload .swu files to install or execute things. For example, official updates are provided as .swu files, similar to Rinkhals and other firmwares.

### For all printers except the Kobra 2 Pro:
1. Format a USB drive as FAT32 (partition table must be MBR, GPT won’t work)
2. Create a directory named `aGVscF9zb3Nf` (older versions use another name, not covered here)
3. Copy your .swu file as `update.swu` in the `aGVscF9zb3Nf` directory
4. Plug the USB drive in the printer
5. You should hear a beep, meaning the printer detected the update file and started the process
6. The rest depends on what you try to install, as described in sections below


### For the Kobra 2 series printers:
1. Format a USB drive as FAT32 (partition table must be MBR, GPT won’t work)
2. Create a directory named `update`
3. Copy your .swu file as `update.swu` in the `update` directory
4. Plug the USB drive in the printer
5. Navigate using the touch UI to Settings --> More settings --> About Machine
6. Click the orange arrow next to `Firmware version`

!!! note "Special note for Kobra 2 Pro [Mainbord Trigorilla Spe B v1.0.x] with Firmware 3.1.4"
    There are a number of issues with stock firmware 3.1.4 on the Kobra 2 Pro. You will need to downgrade to firmware 3.1.2.3 in order to install Rinkhals.

    Follow those steps to downgrade to 3.1.2.3:

    - Download firmware from here: [https://rinkhals.thedju.net/](https://rinkhals.thedju.net/)
    - Format a USB drive as FAT32 (using MBR, GPT won’t work)
    - Create a directory named `update`
    - Rename `K2P_3.1.2.3.swu` to `update.swu`
    - Copy the `update.swu` file in the update directory
    - Plug the USB drive in the printer
    - Go to "About Machine" in the printer menu
    - Click on the arrow next to the version number
    - Confirm, wait for the installation to complete
    - Then follow the Rinkhals installation steps listed above

## Stock firmware installation

- Download the stock firmware you want to install from this share: [https://rinkhals.thedju.net/](https://rinkhals.thedju.net/)
- Follow the installation steps above for your printer model
- After a couple of minutes, you will hear 2 beeps and the printer will reboot with your chosen firmware


## Rinkhals installation

- Make sure your printer firmware is supported (as described on the home page and on the releases page)
- Download the version of Rinkhals you want to install from the [Releases](https://github.com/jbatonnet/Rinkhals/releases)
- Follow the installation steps above

### If you have a Kobra 3 series printer:

- After about 20 seconds (the time for the printer to prepare the update), you will see a progress bar on the screen
    - If the progress bar turns green and you hear 2 beeps, the printer reboots and Rinkhals is installed
    - If the progress bar turns red and you ear 3 beeps, the installation failed but everything should still work as usual. You will then find more information in the `aGVscF9zb3Nf/install.log` file on the USB drive

### If you have a Kobra 2 series printer:

- The printer will reboot twice and beep both times.
    - If you have a Rinkhals icon in the settings tab then Rinkhals is installed.
    - If you don't have Rinkhals icon in the settings tab:
        - First test if Moonsail is running on `http://YOUR_PRINTER_IP` if not then the installation failed.


## How to uninstall Rinkhals

To quickly uninstall Rinkhals, use the Rinkhals installer as instructed on the home page.

To uninstall it manually:
1. **Disable Rinkhals** by disabling from the touch UI or by creating a .disable-rinkhals file on a USB drive or at this location: /useremain/rinkhals/.disable-rinkhals
2. **Reboot your printer**, it will boot the stock firmware
3. If you want, you can **delete Rinkhals** by deleting the /useremain/rinkhals directory


## How to deal with Anycubic firmware updates

!!! warning
    First, make sure the latest version of Rinkhals supports the new firmware you want to install. If it's not supported, don't create issues or ask for ETAs as there are good chances I'm already working on it. If you want more information, you can join the Discord server on the home page and participate in testing.

For now, it's important to apply the official Anycubic update first, and then apply a compatible Rinkhals version.

In the future, Rinkhals might be able to directly apply system update and/or survive official updates.

See the following section for more information.
