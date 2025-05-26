---
title: Network activity
---

## Open ports

- **22**: SSH
- **80**: HTTP / Dynamic (Mainsail, Fluidd, ...)
- **2222**: SSH (only with the tools or installer)
- **4408**: HTTP / Fluidd
- **4409**: HTTP / Mainsail
- **5555**: ADB (not on KS1)
- **5800**: HTTP / VNC web interface
- **5900**: VNC
- **7125**: HTTP / Moonraker
- **8080+**: HTTP / mjpg-streamer for each connected camera (8080, 8081, ...)
- **9883**: MQTT / Mochi internal server

## Outgoing activity

### HTTPS

Those URLs are repositories and mirrors for system / Rinkhals updates. They are used explicitely by Rinkhals when checking for updates.

- [https://github.com/jbatonnet/Rinkhals](https://github.com/jbatonnet/Rinkhals): To check / download Rinkhals updates
- [https://rinkhals.meowcat285.com](https://rinkhals.meowcat285.com): To check / download system updates
- [https://cdn.cloud-universe.anycubic.com/attachment](https://cdn.cloud-universe.anycubic.com/attachment): To download official updates

And soon:

- [https://github.com/jbatonnet/Rinkhals.apps](https://github.com/jbatonnet/Rinkhals.apps): As a trusted repository to check / download new apps

### MQTT

Live connection to Anycubic public MQTT servers. Used for OTA updates, remote control using Anycubic apps.
Anycubic firmware is connecting to them when LAN mode is disabled. Rinkhals Installer uses them to detect new (not yet mirrored) updates.

- ssl://mqtt.anycubic.com:8883: Used for China
- ssl://mqtt-universe.anycubic.com:8883: Used globally

### Apps

- [Cloud2LAN bridge](https://github.com/jbatonnet/Rinkhals.apps/tree/master/apps/cloud2lan-bridge)
    - MQTT servers listed above to simulate cloud features
- [Discovery helper](https://github.com/jbatonnet/Rinkhals.apps/tree/master/apps/discovery-helper)
    - Local IGMP / SSDP
- [Moonraker](https://github.com/jbatonnet/Rinkhals/tree/master/files/4-apps/home/rinkhals/apps/40-moonraker)
    - Update manager

And other apps for their respective services:

- [Cloudflare Tunnel](https://github.com/jbatonnet/Rinkhals.apps/tree/master/apps/cloudflare-tunnel)
- [OctoApp](https://github.com/jbatonnet/Rinkhals.apps/tree/master/apps/octoapp)
- [OctoEverywhere](https://github.com/jbatonnet/Rinkhals.apps/tree/master/apps/octoeverywhere)
- [Remote Debugging](https://github.com/jbatonnet/Rinkhals.apps/tree/master/apps/remote-debugging) (ngrok)
- [Tailscale](https://github.com/jbatonnet/Rinkhals.apps/tree/master/apps/tailscale)
