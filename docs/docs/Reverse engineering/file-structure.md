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
```mermaid
graph LR
    A["/etc/init.d/rcS : Rockchip init.d startup script"] --> B["/etc/init.d/S20linkmount : Symlinks in /dev/block/by-name + Apply A/B to /oem, /ac_lib and /ac_app + Mount /userdata and /useremain"];
    A --> C["/etc/init.d/S90_app_run : Main startup for the printer"];
    C --> D["/userdata/app/kenv/run.sh"];
    D --> E["/userdata/app/gk/start.sh : Kill wpa_supplicant, adbs and start Anycubic binaries"];
    E --> F["/userdata/app/gk/gklib : GoKlipper, Anycubic reimplementation of Klipper in Go ([https://github.com/ANYCUBIC-3D/Kobra3/tree/main/klipper-go](https://github.com/ANYCUBIC-3D/Kobra3/tree/main/klipper-go))"];
    E --> G["/userdata/app/gk/gkapi : Anycubic API service, cloud and local printing services + Mochi MQTT server when lan mode is enabled"];
    E --> H["/userdata/app/gk/gkcam : Anycubic camera process to stream video to Anycubic clients"];
    E --> I["/userdata/app/gk/K3SysUi : Anycubic screen / touch UI binary + starts wpa_supplicant"];
    C --> J["/useremain/rinkhals/start-rinkhals.sh : Rinkhals entrypoint, checking for selected version"];
    J --> K["/useremain/rinkhals/[VERSION]/start.sh"];
    J --> L["/useremain/rinkhals/[VERSION]/tools.sh"];
    A --> M["/etc/init.d/S95dbus : Start dbus"];
    A --> N["/etc/init.d/S99_bootcontrol"];
    N --> O["/usr/bin/rk_ota : Makes sure system has booted properly"];
```

## Rinkhals startup sequence
```mermaid
graph LR
    A["/useremain/rinkhals/start-rinkhals.sh"] --> B["/useremain/rinkhals/[VERSION]/start.sh : Rinkhals startup routine"];
    B --> B1["Sources /useremain/rinkhals/[VERSION]/tools.sh"];
    B --> B2["Check for compatible printer and firmware"];
    B --> B3["Creates /useremain/rinkhals/.disable-rinkhals"];
    B --> B4["Kills gklib, gkapi, gkcam and K3SysUi"];
    B --> B5["Makes sure permissions are correct"];
    B --> B6["Creates the system overlay for /lib, /usr, /bin, /sbin, /opt and /etc"];
    B --> B7["Syncs time with /useremain/rinkhals/[VERSION]/opt/rinkhals/scripts/ntpclient.sh"];
    B --> B8["Mount paths for gcode / config compatibility"];
    B --> B9["Patch Anycubic binaries in place"];
    B --> B10["Restarts gklib, gkapi, gkcam and K3SysUi"];
    B --> B11["Restore original binaries after startup so stock firmware stays clean"];
    B --> B12["Checks if gklib has crashed or is stuck"];
    B --> B13["List apps, check if they are enabled and start them in order"];
    B --> B14["Removes /useremain/rinkhals/.disable-rinkhals"];
    A --> C["/useremain/rinkhals/[VERSION]/stop.sh : Called in case of startup failure"];
    C --> C1["Stops apps"];
    C --> C2["Removes system overlay"];
    C --> C3["Calls /userdata/app/gk/start.sh"];
```