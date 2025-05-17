---
title: Apps configuration
---

!!! note "Temporary page"

    These properties will be exposed in the UI soon 

To configure apps, use those commands in CLI (SSH):

``` shell
set_app_property [APP] [PROPERTY] [VALUE]
remove_app_property [APP] [PROPERTY] # Restore propery to default
clear_app_property [APP] # Restore all properties to default
```

A few examples:
``` shell
set_app_property 30-mjpg-streamer resolution 1280x720
set_app_property 40-moonraker mqtt_print_auto_leveling True
```

Depending on the app, you might need to restart it, either using the UI or:
``` shell
[APP_PATH]/app.sh stop
[APP_PATH]/app.sh start
```

Properties are defined by every app in their app.json manifest:

- mjpg-streamer: [https://github.com/jbatonnet/Rinkhals/blob/master/files/4-apps/home/rinkhals/apps/30-mjpg-streamer/app.json](https://github.com/jbatonnet/Rinkhals/blob/master/files/4-apps/home/rinkhals/apps/30-mjpg-streamer/app.json)
- moonraker: [https://github.com/jbatonnet/Rinkhals/blob/master/files/4-apps/home/rinkhals/apps/40-moonraker/app.json](https://github.com/jbatonnet/Rinkhals/blob/master/files/4-apps/home/rinkhals/apps/40-moonraker/app.json)