---
title: gkapi / Internal MQTT server documentation
---


## General information

Use any MQTT client to connect to:

- Host: [YOUR_PRINTER_IP]
- Port: 2883
- User: userFfWiIvys
- Pass: jUWjRQZwUUlrHOQ

## Topics information

- Commands sent from the slicer: `anycubic/anycubicCloud/v1/slicer/printer/20024/[YOUR_PRINTER_ID]`

- Commands sent from the web: `anycubic/anycubicCloud/v1/web/printer/20024/[YOUR_PRINTER_ID]`

- Information from the printer: `anycubic/anycubicCloud/v1/printer/public/20024/[YOUR_PRINTER_ID]`

## Commands

### Get printer information

Publish to `anycubic/anycubicCloud/v1/slicer/printer/20024/[YOUR_PRINTER_ID]/info:`

```json
{
    "type": "info",
    "action": "query",
    "msgid": "02fd3987-a2ff-244e-7c95-7fe257a9ef70",
    "timestamp": 1660201929871
}
```

Reports from `anycubic/anycubicCloud/v1/printer/public/20024/[YOUR_PRINTER_ID]/info/report`:

```json
{
    "type": "info",
    "action": "report",
    "timestamp": 100107,
    "msgid": "747b3bf5-6c54-45a7-97bb-67507d78d160",
    "state": "done",
    "code": 200,
    "msg": "done",
    "data":
    {
        "printerName": "My Kobra 3",
        "urls":
        {
            "fileUploadurl": "http://[YOUR_PRINTER_IP]:18910/gcode_upload?s=OCL9W949OatvcjBvtmcerIbwT9k6TG7b",
            "rtspUrl": "http://[YOUR_PRINTER_IP]:18088/flv",
        },
        "project": null,
        "model": "Anycubic Kobra 3",
        "ip": "[YOUR_PRINTER_IP]",
        "version": "2.3.5.3",
        "state": "free",
        "temp":
        {
            "curr_hotbed_temp": 23,
            "curr_nozzle_temp": 28,
            "target_hotbed_temp": 0,
            "target_nozzle_temp": 0,
        },
        "print_speed_mode": 2,
        "fan_speed_pct": 0,
        "aux_fan_speed_pct": 0,
        "box_fan_level": 0,
    },
}
```

### Change bed temperature

Publish to `anycubic/anycubicCloud/v1/web/printer/20024/[YOUR_PRINTER_ID]/print`:

```json
{
    "type": "print",
    "action": "update",
    "timestamp": 1733257941899,
    "msgid": "b2d0a5b0-b1b5-11ef-8e80-67dea82d3a00",
    "data": {
        "taskid": "492102245",
        "settings": {
            "target_hotbed_temp": 60
        }
    }
}
```

### Change nozzle temperature

Publish to `anycubic/anycubicCloud/v1/web/printer/20024/[YOUR_PRINTER_ID]/print`:

```json
{
    "type": "print",
    "action": "update",
    "timestamp": 1733257941899,
    "msgid": "b2d0a5b0-b1b5-11ef-8e80-67dea82d3a00",
    "data": {
        "taskid": "492102245",
        "settings": {
            "target_nozzle_temp": 211
        }
    }
}
```

### Turn cam light on/off

Publish to `anycubic/anycubicCloud/v1/web/printer/20024/[YOUR_PRINTER_ID]/light`:

On:

```json
{
    "type": "light",
    "action": "control",
    "timestamp": 1733258023447,
    "msgid": "e36be270-b1b5-11ef-8e80-67dea82d3a00",
    "data": {
        "type": 3,
        "status": 1,
        "brightness": 100
    }
}
```

Off:

```json
{
    "type": "light",
    "action": "control",
    "timestamp": 1733257985156,
    "msgid": "cc992440-b1b5-11ef-8e80-67dea82d3a00",
    "data": {
        "type": 3,
        "status": 0,
        "brightness": 0
    }
}
```

### Turn head light on/off

!!! note

    This might not apply to the KS1, as it lacks a head light

Publish to `anycubic/anycubicCloud/v1/web/printer/20024/[YOUR_PRINTER_ID]/light`:

On:

```json
{
    "type": "light",
    "action": "control",
    "timestamp": 1733258054565,
    "msgid": "f5f81d50-b1b5-11ef-8e80-67dea82d3a00",
    "data": {
        "type": 1,
        "status": 1,
        "brightness": 100
    }
}
```

Off:

```json
{
    "type": "light",
    "action": "control",
    "timestamp": 1733258054565,
    "msgid": "f5f81d50-b1b5-11ef-8e80-67dea82d3a00",
    "data": {
        "type": 1,
        "status": 0,
        "brightness": 0
    }
}
```

### Adjust print speed

Publish to `anycubic/anycubicCloud/v1/web/printer/20024/[YOUR_PRINTER_ID]/print`:

Slow:

```json
{
    "type": "print",
    "action": "update",
    "timestamp": 1733258087225,
    "msgid": "096fa290-b1b6-11ef-8e80-67dea82d3a00",
    "data": {
        "taskid": "492102245",
        "settings": {
            "print_speed_mode": 1
        }
    }
}
```

Standard:

```json
{
    "type": "print",
    "action": "update",
    "timestamp": 1733258087225,
    "msgid": "096fa290-b1b6-11ef-8e80-67dea82d3a00",
    "data": {
        "taskid": "492102245",
        "settings": {
            "print_speed_mode": 2
        }
    }
}
```

Fast:

```json
{
    "type": "print",
    "action": "update",
    "timestamp": 1733258087225,
    "msgid": "096fa290-b1b6-11ef-8e80-67dea82d3a00",
    "data": {
        "taskid": "492102245",
        "settings": {
            "print_speed_mode": 3
        }
    }
}
```

### Enable camera access from VLC / other

Publish to `anycubic/anycubicCloud/v1/web/printer/20024/[YOUR_PRINTER_ID]/video`:

```json
{
    "type": "video",
    "action": "startCapture",
    "timestamp": 1660201929871,
    "msgid": "02fd3987-a2ff-244e-7c95-7fe257a9ef70",
    "data": null
}
```

Then open the stream URL: `http://[YOUR_PRINTER_IP]:18088/flv`

### Start printing

Publish to `anycubic/anycubicCloud/v1/slicer/printer/20024/[YOUR_PRINTER_ID]/print`:

Example:

```json
{
    "type": "print",
    "action": "start",
    "msgid": "02fd3987-a2ff-244e-7c95-7fe257a9ef70",
    "timestamp": 1660201929871,
    "data": {
        "taskid": "-1", // Mandatory
        "url": "<https://anycubic.com/store/aaa.gcode>", // Optional
        "filename": "test_model/FlexibleShark-41m.gcode", // Mandatory
        "md5": "943c0dff568dd508e21af2d894bb6b49", // Optional
        "filepath": null, // Optional
        "filetype": 1, // Mandatory
        "project_type": 1, // Optional
        "filesize": 188000, // Optional
        "ams_settings": { // Optional
            "use_ams": true,
            "ams_box_mapping": [
                {
                    "paint_index": 0,
                    "ams_index": 0,
                    "paint_color": [
                        255,
                        255,
                        255,
                        255
                    ],
                    "ams_color": [
                        255,
                        255,
                        255,
                        255
                    ],
                    "material_type": "PLA"
                }
            ]
        },
        "task_settings": { // Optional
            "auto_leveling": 0,
            "vibration_compensation": 0,
            "ai_settings": {
                "status": 0,
                "count": 468,
                "type": 723012352
            }
        }
    }
}
```

Minimal:

```json
{
    "type": "print",
    "action": "start",
    "msgid": "02fd3987-a2ff-244e-7c95-7fe257a9ef70",
    "timestamp": 1660201929871,
    "data": {
        "taskid": "-1",
        "filename": "test_model/FlexibleShark-41m.gcode",
        "filetype": 1
    }
}
```

### Stop current print

```json
{
    "type": "print",
    "action": "stop",
    "timestamp": 1733337112202,
    "msgid": "07fe2ea0-b26e-11ef-94d0-7925260ebe40",
    "data": {
        "taskid": "-1"
    }
}
```