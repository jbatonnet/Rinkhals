# Rinkhals

Rinkhals is a custom firmware for some Anycubic Kobra 3D printers (specifically the ones running Kobra OS, see below for the details).

The goal of this project is to expand existing Anycubic features with better compatibility, apps and more.
I will likely not support all use cases, like running vanilla Klipper or your specific feature / plugin.

By using Rinkhals, you will keep all stock Anycubic features (print screen, Anycubic tools, calibration, ...) and get even more, like:
- Mainsail, Fluidd (with Moonraker)
- USB camera support in Mainsail, Fluidd
- Prints from Orca will show the print screen
- SSH access for customization (user: **root**, password: **rockchip**)
- OTA Rinkhals updates
- [Apps system](https://github.com/jbatonnet/Rinkhals.apps) (OctoEverywhere, Cloudflare, Tailscale, ...)

Latest version will likely support the two latest firmwares from Anycubic, unless specified. For older firmware please check older releases.
Here are the suported printers and firmwares with latest Rinkhals release:
| Model  | Tested firmwares | Notes |
| -- | -- | -- |
| Kobra 3 (+ combo) | `2.4.0` `2.4.0.4` |
| Kobra 2 Pro | `3.1.2.3` | Only with mainboard [Trigorilla Spe **B** v1.0.x](https://1coderookie.github.io/Kobra2ProInsights/hardware/mainboard/#trigorilla_spe_b_v10x-stock-new-revision). `3.1.4` is buggy |
| Kobra S1 (+ combo) | `2.5.2.3` `2.5.3.1` |
| Kobra 3 Max (+ combo) | `2.4.6` `2.4.6.5` |

In case you're wondering this project is named after rinkhals, a sub-species of Cobras ... Kobra ... Rinkhals 👏

You can join the Rinkhals community on Discord: https://discord.gg/3mrANjpNJC

Since people have been asking, I accept donations but please remember that I work on Rinkhals for fun and not for the money. I will not accept donations to work on specific bugs or features.


<p align="center">
    <img width="48" src="https://github.com/jbatonnet/Rinkhals/blob/master/icon.png?raw=true" />
</p>


## Rinkhals installation

> [!WARNING]
> **Make sure you're confident tweaking your printer and you understand what you're doing. I'm not responsible if you brick your printer (even if there's some [documentation](https://jbatonnet.github.io/Rinkhals/Kobra%20Printers/recover-boot-issues/) about that)**

> [!CAUTION]
> Many users want to change their Klipper printer configuration (the printer.cfg file). I strongly advise not modifying the stock printer configuration. Rinkhals offers additional protection you don't have while modifying directly your printer configuration. **I won't offer any support** and **your printer might not work properly or not boot anymore**. Check the documentation for more information: [Printer configuration](https://jbatonnet.github.io/Rinkhals/Rinkhals/printer-configuration/)

A [quick start guide](https://jbatonnet.github.io/Rinkhals/guides/rinkhals-quick-start/) is available to get Rinkhals up and running on your printer.

There are two options to install Rinkhals:
1. Use the provided Rinkhals installer (named **install-*.swu**)
2. Install the raw swu directly (named **update-*.swu**)

Either way, you'll need to:
- Download the release / file you want from the [Releases](https://github.com/jbatonnet/Rinkhals/releases) page
- Rename the downlaoded SWU file as **update.swu**
- Copy it in a directory named **aGVscF9zb3Nf** on a FAT32 USB drive
- Plug the USB drive in your printer



More detailed information about the Rinkhals installer are available in the [documentation](https://jbatonnet.github.io/Rinkhals/Rinkhals/rinkhals-installer/)

For more information about installation, firmware updates and details about specific situations, go to https://jbatonnet.github.io/Rinkhals/Rinkhals/installation-and-firmware-updates/


## Touch UI

After installation, Rinkhals provides a touch UI accessible from the printer screen when you tap the Settings icon, then tap Rinkhals.

This UI allows you to manage installed apps, trigger an OTA update, reboot your printer and much more. This will allow you to customize your experience and keep the printer memory as low as needed based on your needs.

<p align="center">
    <!-- <img width="192" src="./.github/images/screenshot-settings.png"> -->
    <img width="192" src="./.github/images/screenshot-rinkhals-main.png">
    <img width="192" src="./.github/images/screenshot-rinkhals-apps.png">
    <img width="192" src="./.github/images/screenshot-rinkhals-app.png">
    <img width="192" src="./.github/images/screenshot-rinkhals-ota.png">
    <!-- <img width="192" src="./.github/images/screenshot-rinkhals-advanced.png"> -->
</p>

## Apps system

An apps system is provided in Rinkhals. It allows for the users to easily add some features to their printer. Some default ones are provided and other are available on separate repos like:
- https://github.com/jbatonnet/Rinkhals.apps (Tailscale, Cloudflare, OctoApp companion, some progress on vanilla Klipper, ...)
- https://github.com/basvd/Rinkhals.WebUI (a web interface for Rinkhals)

Instructions on how to install or develop apps are on the other repo as well.


<p align="center">
    <img width="48" src="https://github.com/jbatonnet/Rinkhals/blob/master/icon.png?raw=true" />
</p>


## Rinkhals Installer

From the release pages, you'll find the installer-\*.swu files for your printer model. This is an interactive touch tool to install and update Rinkhals and system firmware updates.

You can find more information in [the documentation](https://jbatonnet.github.io/Rinkhals/Rinkhals/rinkhals-installer/)

## Documentation / Known issues

The [documentation](https://jbatonnet.github.io/Rinkhals) is a collection of documentation, reverse engineering and notes about the printer and development, don't forget to [check it out](https://jbatonnet.github.io/Rinkhals)!

If your printer shows a 11407 error, check the documentation there: [Read about error 11407](https://jbatonnet.github.io/Rinkhals/Rinkhals/faq/#my-printer-is-stuck-with-error-11407)

## SWU tools

> [!NOTE]
> Those tools are also available through the Rinkhals installer touch UI ([documentation](https://jbatonnet.github.io/Rinkhals/Rinkhals/rinkhals-installer/))

This repo contains some tools you can use **no matter what firmware you are using**. It is a set of scripts packaged in a SWU file.

From the [Releases](https://github.com/jbatonnet/Rinkhals/releases) page, identify the tools.zip file for your printer.
Extract it, copy the SWU file you want as **update.swu** on a FAT32 USB drive in a **aGVscF9zb3Nf** directory, plug the USB drive in your printer and it just works.
You will ear two beeps, the second one will tell you that the tool completed its work. There is no need to reboot afterwards.

Here are the tools available:
- **SSH**: get a SSH server running on port **2222**, even on stock firmware
- **Backup partitions**: creates a dump of your userdata and useremain partition on the USB drive
- **Debug bundle**: creates a zip file with printer and configuration information on the USB drive to ease debugging
- **Rinkhals uninstall**: uninstall Rinkhals completely from your printer
- **Clean Rinkhals**: Removes old Rinkhals versions from your printer (keeps 3 versions including the current one)

<p align="center">
    <img width="48" src="https://github.com/jbatonnet/Rinkhals/blob/master/icon.png?raw=true" />
</p>


## Development

> [!WARNING]
> If you develop on Windows like me, don't forget to disable Git's autocrlf function, as this repo contains Linux scripts running on Linux machines.<br />
> Run `git config core.autocrlf false` **BEFORE** cloning the repo

You will need either a Linux machine or a Windows machine with Docker.
Read the documentation and join us on Discord to discuss development!


## Thanks

Thanks to the following projects/persons:
- utkabobr (https://github.com/utkabobr/DuckPro-Kobra3)
- systemik (https://github.com/systemik/Kobra3-Firmware)
- Anycubic for the cool printer and the few OSS items (https://github.com/ANYCUBIC-3D/Kobra)
- Icon created by Freepik - Flaticon (https://www.flaticon.com/free-icon/cobra_375098)
- moosbewohner for Kobra 2 Pro support (https://github.com/moosbewohner/Rinkhals)
- Kalenell and woswai1337 for Kobra S1 support

Thanks to the project and apps contributors, including the persons below and many more:
- Matthias Goebl (https://github.com/matgoebl)
- Tobias Göbel (https://github.com/kubax)
- dan3805 (https://github.com/dan3805)
- basvd (https://github.com/basvd)
- Meowcat285 (https://github.com/Meowcat285)
