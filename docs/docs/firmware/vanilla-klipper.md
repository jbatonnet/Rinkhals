---
title: Vanilla Klipper
---

Working on the K2P:

- App and config are provided here: [https://github.com/jbatonnet/Rinkhals.apps/blob/master/apps/vanilla-klipper](https://github.com/jbatonnet/Rinkhals.apps/blob/master/apps/vanilla-klipper

)

For K3 and KS1, some drivers are missing. Here is the patch I applied to the default config to make Klipper start: [https://github.com/jbatonnet/Rinkhals.apps/blob/047a7736451d4e8da64910ad9adc34384710ac73/apps/vanilla-klipper/printer.klipper_K3.cfg.patch](https://github.com/jbatonnet/Rinkhals.apps/blob/047a7736451d4e8da64910ad9adc34384710ac73/apps/vanilla-klipper/printer.klipper_K3.cfg.patch)

The following drivers are missing

- lis2dw12: [klipper-go/project/extras_lis2dw12.go](https://github.com/ANYCUBIC-3D/Kobra3/blob/main/klipper-go/project/extras_lis2dw12.go)
- leviQ3: [klipper-go/project/leviQ3.go](https://github.com/ANYCUBIC-3D/Kobra3/blob/main/klipper-go/project/leviQ3.go)
- cs1237: [klipper-go/project/cs1237.go](https://github.com/ANYCUBIC-3D/Kobra3/blob/main/klipper-go/project/cs1237.go)