import os
import time
import evdev

def log(message):
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + message, flush = True)

touch_device = evdev.InputDevice('/dev/input/event0')

ui = evdev.UInput.from_device(touch_device)
ui = evdev.UInput()
e = evdev.ecodes

def touch(x, y):
    ui.write(e.EV_ABS, e.ABS_X, x)
    ui.write(e.EV_ABS, e.ABS_Y, y)
    ui.syn()
    ui.write(e.EV_KEY, e.BTN_TOUCH, 1)
    ui.syn()
    time.sleep(0.1)
    ui.write(e.EV_KEY, e.BTN_TOUCH, 0)
    ui.syn()

ui.write(e.EV_ABS, e.ABS_X, 50)
ui.write(e.EV_ABS, e.ABS_Y, 50)
ui.write(e.EV_KEY, e.BTN_TOUCH, 1)
ui.syn()

time.sleep(0.1)
ui.write(e.EV_KEY, e.BTN_TOUCH, 0)
ui.syn()

ui.close()
