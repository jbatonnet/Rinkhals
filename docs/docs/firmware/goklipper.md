---
title: GoKlipper
---

GoKlipper is Anycubic Klipper reimplementation in Go.

Source code for Kobra 3: [https://github.com/ANYCUBIC-3D/Kobra3/tree/main/klipper-go](https://github.com/ANYCUBIC-3D/Kobra3/tree/main/klipper-go)

## Debug logs

The `gklib` log level can be set to 'debug' for more detailed logging by changing `/userdata/app/gk/config/api.cfg`:

```json
    "sys":{
        "logLevel":"debug"
    },
```

Note: existing properties of the 'sys' section have been omitted but should obviously be left unchanged.

Logs are written to: `/var/log/gklib.log`

## Profiler

The `gklib` application includes a profiler which can be enabled from `/userdata/app/gk/config/api.cfg` by adding the following section:
```json
    "pprof":{
        "enable":true
    },
```

The profiler has a web interface at `:6060/debug`, which lets you inspect threads, heap, goroutines and more, as well as running CPU profile or trace which can be downloaded and analyzed with tools.

See the [Go diagnostics documentation](https://go.dev/doc/diagnostics) and the [`pprof` library](https://github.com/google/pprof) for more information.

