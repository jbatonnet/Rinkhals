---
title: Boot Issues Recovery
---

!!! warning

    This page might be out of date, if you need assistance, please come ask in the Rinkhals Discord

If you messed up your file structure playing with your printer, you might end up (soft) bricking your printer. In my situation, my printer refused to start, only showing the Anycubic logo with an empty progress bar but nothing more. Some of the system files needed to start were missing, without any possibility of using SSH or ADB in software.

It is possible to recover from this situation and restore the partitions to a bootable state.

You will need to build a special USB cable and access to a Linux machine (Windows might work but neither confirmed nor documented yet).

## Mainboard connection
Follow the guide on this page: [Mainboard connection](mainboard-connection/index.md)

## Restore broken partitions
I uploaded a copy of working partitions to ease the recovery process. It uses 2.3.5.3 firmware and I deleted / changed all the device-specific keys, you will need to provide/restore yours in the files listed below (in the userdata and useremain partitions).

Link to partition backup:
[2.3.5.3](https://1drv.ms/f/c/25a0ae578213b40f/Qg-0E4JXrqAggCUtXhAAAAAAxJkvEgvxqJbI4Q)

##`userdata` partition
I managed to recover form a deletion of everything in the **userdata** partition. This one contains all the startup scripts for your printer to boot and to start Klipper, the UI, everything.

I took the last official update package (2.3.5.3 at the time of writing).

- Unzip the .swu file with this password `U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w=`
- Extract the `setup.tar.gz` file
- There is a `update_shell/update_udisk_init.sh` script, responsible (I guess) to initialize everything from the update itself

I then modified the script to use the path of my partition being modified, and removed all the unecessary parts:

```shell
update_file_path="./update_swu"
to_update_path="./_userdata/app/gk"
to_update_wifi_cfg="./_userdata/wifi_cfg"
to_run_sh_path="./_userdata/app/kenv"
```

I ran the modified script, made sure all the necessary files are present, including specifically:

- `/userdata/app/kenv/run.sh`
- `/userdata/app/gk/start.sh`
- `/userdata/app/gk/gkapi, gkcam, gklib and K3SysUi`
- `/userdata/app/gk/device.ini`

Check that all your machine-specific files are present:

- **`/userdata/app/gk/config/device.ini`**
    - `[cloud_prod]` and `[cloud_global_prod]` / `mechineCode`, `deviceUnionId` and `deviceKey` should be filled properly
- **`/userdata/app/gk/config/device_account.json`**
    - `deviceId`, `username` and `password` should be filled properly
    - deviceId must be the same as `/useremain/dev/device_id`
- **`/useremain/app/gk/cert1 and /useremain/app/gk/cert3`**
    - Printer-specific certificates

Then I wrote back the partition to the motherboard, plugged everything back, and it worked!

Here is a copy of the modified script I used: [reset_userdata.zip](https://github.com/user-attachments/files/18142084/reset_userdata.zip)

##`useremain` partition
Until I have a proper guide, check: [https://github.com/Bushmills/Anycubic-Kobra-3-rooted/discussions/5#discussioncomment-11504611](https://github.com/Bushmills/Anycubic-Kobra-3-rooted/discussions/5#discussioncomment-11504611)

##Other partitions

The other partitions are directly available from the official .swu files:

- Unzip the .swu file with this password `U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w=`
- Extract the `setup.tar.gz` file
- Extract the `update_ota.tar` file

You will see 5 `.img` files.

Those are partition dumps of the other partition you can flash using the method above.