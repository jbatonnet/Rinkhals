---
title: Network activity
---

## Open ports

- **22**: SSH
- **71**: Anycubic Orca compatibility API (octoprint compat), moved from port 80
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

- [https://github.com](https://github.com): To check / download Rinkhals updates
- [https://api.github.com](https://api.github.com): To check Rinkhals updates
- [https://raw.githubusercontent.com](https://raw.githubusercontent.com): As a trusted repository to check / download new apps
- [https://cdn.meowcat285.com](https://cdn.meowcat285.com): To check / download system updates
- [https://cdn.cloud-universe.anycubic.com](https://cdn.cloud-universe.anycubic.com): To download official updates

### MQTT

Live connection to Anycubic public MQTT servers. Used for OTA updates, remote control using Anycubic apps.
Anycubic firmware is connecting to them when LAN mode is disabled. Rinkhals Installer uses them to detect new (not yet mirrored) updates.

- ssl://mqtt.anycubic.com:8883: Used for China
- ssl://mqtt-universe.anycubic.com:8883: Used globally

### NTP

NTP client for syncing time. It will check DHCP lease for an advertised NTP server, and if none is advertised will use pool.ntp.org.

- **123/UDP** to either:
  - A local NTP server advertised by DHCP from your router
  - pool.ntp.org

### DNS

DNS uses 1.1.1.1 (Cloudflare DNS) and 8.8.8.8 (Google DNS) using standard port 53/UDP. It does not appear to support DoT or DoH. The stock firmware does not appear to use the DNS servers advertised by DHCP.

- **53/UDP**: To 1.1.1.1
- **53/UDP**: To 8.8.8.8

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
