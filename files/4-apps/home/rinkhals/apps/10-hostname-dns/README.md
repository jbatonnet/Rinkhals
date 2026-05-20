# Hostname & DNS

Sets a custom hostname for your printer and advertises it on the local network via mDNS and DHCP. Useful when you have multiple Kobra printers and need to tell them apart.

## How It Works

1. **Hostname** - Sets the system hostname on startup
2. **mDNS (.local)** - Runs a lightweight mDNS responder so you can reach the printer as `hostname.local` from any device on the network (e.g., `ping my-printer.local`)
3. **DHCP** - Restarts the DHCP client with the hostname so your router registers it, making the printer reachable by short name (e.g., `ping my-printer`) and visible in your router's device list

Both mDNS and DHCP propagation are enabled by default.

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Hostname | *(auto-generated)* | Custom hostname for the printer |
| Send hostname via DHCP | True | Restarts `udhcpc` with the hostname so the router registers it for short-name resolution |

## Default Hostname

When no custom hostname is configured, one is auto-generated from the printer model and device ID:

```
kobra-{model}-{device_id_suffix}
```

For example: `kobra-k3-a1b2`, `kobra-ks1-f3e9`

This ensures each printer gets a unique name even without manual configuration.

## Set Custom Hostname Or Disable DHCP Propagation

To set a custom hostname, SSH into the printer and run:

```bash
source /useremain/rinkhals/.current/tools.sh
set_app_property 10-hostname-dns hostname my-printer
```

The hostname is sanitized automatically: converted to lowercase, invalid characters replaced with hyphens, and truncated to 63 characters (DNS limit).

DHCP propagation can be disabled via the Rinkhals UI toggle or via SSH:

```bash
source /useremain/rinkhals/.current/tools.sh
set_app_property 10-hostname-dns dhcp_hostname False
```

Then restart the app (or reboot the printer):

```bash
/useremain/home/rinkhals/apps/10-hostname-dns/app.sh stop
/useremain/home/rinkhals/apps/10-hostname-dns/app.sh start
```

## Dependencies

Python 3 standard library only - no additional packages required.
