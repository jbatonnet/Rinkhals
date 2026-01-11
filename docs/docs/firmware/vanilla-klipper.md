---
title: Vanilla Klipper
---

## K2P Support

Working on the K2P:

- App and config are provided here: [https://github.com/jbatonnet/Rinkhals.apps/blob/master/apps/vanilla-klipper](https://github.com/jbatonnet/Rinkhals.apps/blob/master/apps/vanilla-klipper)

## K3 and KS1 Support

Vanilla Klipper is now working for KS1 and K3 printers. However, they require a current klipper-base and some driver additions which are not yet merged into the main branch of the Rinkhals vanilla-klipper APP builds. Without these updates, you may encounter startup errors (e.g., Error Code 22 on the printer display).

### Current Workaround

An updated klipper base with the necessary driver additions exists on the `feature/anycubic-klippy` branch of the Rinkhals.Apps repository, but it is not yet merged to master:

- [https://github.com/jbatonnet/Rinkhals.Apps/tree/feature/anycubic-klippy](https://github.com/jbatonnet/Rinkhals.Apps/tree/feature/anycubic-klippy)

Alternatively, for KS1/K3 vanilla-klipper APP builds, you can use this repository which contains the necessary klipper base and driver patches:

- [https://github.com/Kobra-S1/vanilla-klipper-swu](https://github.com/Kobra-S1/vanilla-klipper-swu)

### Ported Drivers

The following drivers have been ported from Go to Python and are available in the dev branch:

- **lis2dw12**: [lis2dw12.py](https://github.com/Kobra-S1/klipper-kobra-s1/blob/Kobra-S1-Dev/klippy/extras/lis2dw12.py) (ported from [extras_lis2dw12.go](https://github.com/ANYCUBIC-3D/Kobra3/blob/main/klipper-go/project/extras_lis2dw12.go))
- **cs1237**: [cs1237.py](https://github.com/Kobra-S1/klipper-kobra-s1/blob/Kobra-S1-Dev/klippy/extras/cs1237.py) (ported from [cs1237.go](https://github.com/ANYCUBIC-3D/Kobra3/blob/main/klipper-go/project/cs1237.go))
- **probe_ks1**: [probe_ks1.py](https://github.com/Kobra-S1/klipper-kobra-s1/blob/Kobra-S1-Dev/klippy/extras/probe_ks1.py)

Development branch: [https://github.com/Kobra-S1/klipper-kobra-s1/tree/Kobra-S1-Dev](https://github.com/Kobra-S1/klipper-kobra-s1/tree/Kobra-S1-Dev)

### leviQ3 Driver

There is no leviQ3 port available, as this is closed-source IP of Anycubic. However, probing is still possible using the `probe_ks1` driver, which supports generic Klipper nozzle probing.

## Tunneled Klipper for SBCs

An alternative Rinkhals APP build is available that allows running vanilla Klipper on SBCs like the Raspberry Pi 4/5. This utilizes a Rinkhals "tunnel" app which tunnels the serial MCU communication between the printer and RPi via OTG USB Serial Gadget mode.

More information: [https://github.com/Kobra-S1/vanilla-klipper-swu/blob/main/tunneled-klipper.md](https://github.com/Kobra-S1/vanilla-klipper-swu/blob/main/tunneled-klipper.md)