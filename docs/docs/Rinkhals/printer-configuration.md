---
title: Printer configuration
---

!!! danger

    I strongly advise not modifying the stock printer configuration. Rinkhals offers additional protection you don't have while modifying directly your printer configuration. I won't offer any support and your printer might not work properly or not boot anymore.

Many users want to change their Klipper printer configuration (the `printer.cfg` file).

Please note that Anycubic and thus Rinkhals use GoKlipper, a Go reimplementation of Klipper that does not support the same level of tweaking that you would be able to do with vanilla Klipper.
If you modify the printer.cfg, your printer might not boot properly or show error 11407 (meaning GoKlipper could not start, usually because of a broken configuration).

Before starting, here is a link to known stock printer configurations: [https://github.com/jbatonnet/Rinkhals/tree/master/files/3-rinkhals/home/rinkhals/printer_data/config](https://github.com/jbatonnet/Rinkhals/tree/master/files/3-rinkhals/home/rinkhals/printer_data/config)

And here is a link to stock firmwares you can flash to restore your printer:

[https://rinkhals.thedju.net/](https://rinkhals.thedju.net/)

## Stock firmware configuration

- Configuration location: `/userdata/app/gk/printer.cfg`
- To modify it, you'll need SSH / ADB access and modify it. Reboot the printer to see the results.

If you break something, restore the configuration or reflash stock firmware using the links above.

## Rinkhals configuration system

!!! warning

    I provided the ability to use custom configuration because people asked for it, but I'm not responsible for what you do or how you brick your printer this way! I personally don't use customizations and I'm quite happy this way. You are now warned!

Rinkhals does not use the stock printer configuration file in `/userdata/app/gk/printer.cfg`, instead it embeds the stock configuration for your printer and generated a configuration dynamically based on different customizations.

- Embedded stock configuration: `/useremain/rinkhals/<VERSION>/home/rinkhals/printer_data/config/printer.K3_2.3.7.1.cfg` (for example)
- Rinkhals customizations: `/useremain/rinkhals/<VERSION>/home/rinkhals/printer_data/printer.rinkhals.cfg` (for example)
- User customizations: `/useremain/home/rinkhals/printer_data/printer.custom.cfg`

The first one is the printer default with a [include printer.rinkhals.cfg] at the end

The second has Fluidd customizations with a [include /useremain/home/rinkhals/printer_data/config/printer.custom.cfg] at the end

The third one will be able to be used for user customizations. This is the only one that will be persisted accross Firmware and Rinkhals versions.

- A file at `/useremain/home/rinkhals/printer_data/printer.generated.cfg` will be generated at every Rinkhals startup, combining the files listed above to create a single file for GoKlipper.

- Please note that files in `/useremain/rinkhals/<VERSION>` will get updated with each Rinkhals versions, whereas files in `/useremain/home/rinkhals` will be kept, making user customizations persistent across versions.

## I got 11407 or my printer doesn't boot anymore

First read all the warnings everywhere, and the information above provide ways to restore your printer.

Error 11407 is GoKlipper not being able to start on your printer. There are two main reasons for this issue to appear:

- The printer configuration file (printer.cfg or printer.custom.cfg) was modified. In this case, you need to restore it to a working state either by undoing your change or by restoring the default.
- A second bed mesh was saved (`printer_mutable.cfg`) and GoKlipper only support one default mesh. In this case, your need to either remove the second mesh and leave the default one or delete the printer_mutable.cfg file to restore the default configuration. Please note that last versions of Rinkhals try to prevent this case from happening.

Now here are some additional tools I built in Rinkhals to help those situations:

- If Rinkhals doesn't start properly, it will disable itself. Next reboot you'll be back to stock firmware.
- Rinkhals tries to detect if GoKlipper is stuck or crashes. In those cases it will disable itself.
- If Rinkhals is disabled, you can place a `.enable-rinkhals` file at the root of a USB drive, and reboot. It will force Rinkhals to try to start again, but it might crash and disable itself again.
- You can have a `printer.custom.cfg` at the root of a USB drive. During startup, Rinkhals will copy and override the user customizations with the ones provided.
- I provide multiple SWU tools to get SSH, restore the config and more: [https://github.com/jbatonnet/Rinkhals/actions/workflows/build-swu-tools.yml](https://github.com/jbatonnet/Rinkhals/actions/workflows/build-swu-tools.yml)

So with all that you're left with some solutions:

<div class="annotate" markdown>
- When Rinkhals is disabled, it still starts ADB as a backup access(1). You could use it to connect to PRINTER_IP:5555, get a shell and modify your printer.custom.cfg and/or printer_mutable.cfg
- You can use the SSH SWU tool at all times to get SSH access and change your config
- If you want to iterate over printer config changes, you can have a USB drive with 2 files at the root:
    - `printer.custom.cfg`: it will replace the one on your printer during startup, this way you can easily modify it
    - `.enable-rinkhals`: it will force Rinkhals to start even if it was disabled
- You can use the config-reset SWU tool to reset the configuration to stock and restart. It might not be enough in some circumstances however.
</div>

1. Please note that ADB is not started on the KS1, as it lacks ADB in it's firmware

Finally, you can always connect using SSH or ADB and fully reset Rinkhals config:

- `rm -rf /useremain/home/rinkhals`