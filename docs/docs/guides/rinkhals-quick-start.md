---
title: Rinkhals quick start guide
---

## To install Rinkhals

### Using the full offline package

- Go to the release page on GitHub: [Rinkhals releases](https://github.com/jbatonnet/Rinkhals/releases)
- Select and download the right update-\*.swu for your printer
- Rename the downloaded SWU file as **update.swu**
- Copy it in a directory named **aGVscF9zb3Nf** on a FAT32 USB drive
- Plug the USB drive in your printer

### Using the Rinkhals installer

!!! note
    The installer you downloaded will still work for future releases. You can leave it on your USB drive and just plug it, even for future releases

You can read more information about the Rinkhals installer on this [page](../Rinkhals/rinkhals-installer.md).

- Go to the release page on GitHub: [Rinkhals releases](https://github.com/jbatonnet/Rinkhals/releases)
- Select and download the right installer-\*.swu for your printer
- Rename the downloaded SWU file as **update.swu**
- Copy it in a directory named **aGVscF9zb3Nf** on a FAT32 USB drive
- Plug the USB drive in your printer
- Wait ~10s for the installer to appear
- Go to Update > Rinkahls > Manage
- Select the version you want to install
- Tap Download then Install


## Find the IP address of your printer

There are 2 options to find your printer IP address. First, make sure the pritner is connected to your Wi-Fi following the on screen instruction or wizard.

### From your printer screen

On your printer touch screen, either:

- Go to Network, then LAN Mode
- Your IP should be shown here

Or:

- Go to Device Information, then Printer Information
- Your IP should be shown here


## To use Mainsail or Fluidd, the web interfaces

Open your browser to http://YOUR_PRINTER_IP to open the web interface (Mainsail by default).
From there you'll be able to control your printer.

Please refer to Mainsail documentation for more information: [https://docs.mainsail.xyz](https://docs.mainsail.xyz)


## To directly print from Orca or OctoApp

Rinkhals supports Orca and OctoApp out of the box. Just add your printer using its IP address.
Then, you should be able to directly upload or print from those software or other similar ones.
