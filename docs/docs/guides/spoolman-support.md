---
title: Spoolman support
---

[https://discord.com/channels/1332498592539345069/1332500553833517148/1354581748977238107](https://discord.com/channels/1332498592539345069/1332500553833517148/1354581748977238107)

`moonraker.custom.conf`

```
[spoolman]
server: https://spoolman.domain
sync_rate: 5
```

`printer.custom.cfg`

```
[gcode_macro SET_SPOOL]
gcode:
    {{ action_call_remote_method("spoolman_set_active_spool", params) }}

[gcode_macro M555]
gcode:
    SET_SPOOL SPOOL_ID={{ params.S }}
```

and per filament in Orca on in the filament start code

```gcode
; filament start gcode
M555 S=5
```