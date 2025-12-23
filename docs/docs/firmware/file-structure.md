---
title: File structure
---

## Partitions

The system uses A/B partitions

- /dev/mmcblk0p1 : env
- /dev/mmcblk0p2 : idblock
- /dev/mmcblk0p3 : uboot_a
- /dev/mmcblk0p4 : uboot_b
- /dev/mmcblk0p5 : misc
- /dev/mmcblk0p6 : boot_a
- /dev/mmcblk0p7 : boot_b
- /dev/mmcblk0p8 : system_a
- /dev/mmcblk0p9 : system_b
- /dev/mmcblk0p10 : oem_a
- /dev/mmcblk0p11 : oem_b
- /dev/mmcblk0p12 : userdata
- /dev/mmcblk0p13 : ac_lib_a
- /dev/mmcblk0p14 : ac_lib_b
- /dev/mmcblk0p15 : ac_app_a
- /dev/mmcblk0p16 : ac_app_b
- /dev/mmcblk0p17 : useremain

## udev rules

In `/lib/udev/rules.d`:
- 61-udisk-auto-mount.rules : Rule to autostart /userdata/channel.sh on USB drive mount

## Kobra startup sequence

* `/etc/init.d/rcS` : Rockchip init.d startup script
    * `/etc/init.d/S20linkmount` : Symlinks in `/dev/block/by-name` + Apply A/B to `/oem`, `/ac_lib` and `/ac_app` + Mount `/userdata` and `/useremain`
    * `/etc/init.d/S90_app_run` : Main startup for the printer
        * `/userdata/app/kenv/run.sh`
            * `/userdata/app/gk/start.sh` : Kill wpa_supplicant, adbs and start Anycubic binaries
                * `/userdata/app/gk/gklib` : GoKlipper, Anycubic reimplementation of Klipper in Go ([https://github.com/ANYCUBIC-3D/Kobra3/tree/main/klipper-go](https://github.com/ANYCUBIC-3D/Kobra3/tree/main/klipper-go))
                * `/userdata/app/gk/gkapi` : Anycubic API service, cloud and local printing services + Mochi MQTT server when lan mode is enabled
                * `/userdata/app/gk/gkcam` : Anycubic camera process to stream video to Anycubic clients
                * `/userdata/app/gk/K3SysUi` : Anycubic screen / touch UI binary + starts wpa_supplicant
                * `/useremain/rinkhals/start-rinkhals.sh` : Rinkhals entrypoint, checking for selected version
                    * `/useremain/rinkhals/[VERSION]/start.sh`
                    * `/useremain/rinkhals/[VERSION]/tools.sh`
    * `/etc/init.d/S95dbus` : Start dbus
    * `/etc/init.d/S99_bootcontrol`
        * `/usr/bin/rk_ota` : Makes sure system has booted properly

## Rinkhals startup sequence

* `/useremain/rinkhals/start-rinkhals.sh`
    * `/useremain/rinkhals/[VERSION]/start.sh` : Rinkhals startup routine
        * Sources `/useremain/rinkhals/[VERSION]/tools.sh`
        * Check for compatible printer and firmware
        * Creates `/useremain/rinkhals/.disable-rinkhals`
        * Kills gklib, gkapi, gkcam and K3SysUi
        * Makes sure permissions are correct
        * Creates the system overlay for /lib, /usr, /bin, /sbin, /opt and /etc
        * Syncs time with `/useremain/rinkhals/[VERSION]/opt/rinkhals/scripts/ntpclient.sh`
        * Mount paths for gcode / config compatibility
        * Patch Anycubic binaries in place
        * Restarts gklib, gkapi, gkcam and K3SysUi
        * Restore original binaries after startup so stock firmware stays clean
        * Checks if gklib has crashed or is stuck
        * List apps, check if they are enabled and start them in order
        * Removes `/useremain/rinkhals/.disable-rinkhals`
    * `/useremain/rinkhals/<VERSION>/stop.sh` : Called in case of startup failure
        * Stops apps
        * Removes system overlay
        * Calls `/userdata/app/gk/start.sh`