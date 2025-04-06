import lvgl as lv
import lv_utils
import time
import uasyncio

lv.init()

disp = lv.linux_fbdev_create()
lv.linux_fbdev_set_file(disp, '/dev/fb0')

def debug_event(event):
    print(event)

rot = lv.DISPLAY_ROTATION._270
disp.set_rotation(rot)

touch = lv.evdev_create(lv.INDEV_TYPE.POINTER, '/dev/input/event0')
touch.set_display(disp)

# TODO Fine-tune calibration
TOUCH_MAX_X = 460
TOUCH_MAX_Y = 25
TOUCH_MIN_X = 25
TOUCH_MIN_Y = 235

lv.evdev_set_calibration(touch, TOUCH_MIN_X, TOUCH_MIN_Y, TOUCH_MAX_X, TOUCH_MAX_Y)

scr = lv.obj()

btn = lv.button(scr)
btn.align(lv.ALIGN.CENTER, 0, 0)
label = lv.label(btn)
label.set_text('Hello Rinkhals!')

minbtn = lv.button(scr)
minbtn.align(lv.ALIGN.TOP_LEFT, 0, 0)
minp = lv.label(minbtn)
minp.set_text('0,0')

maxbtn = lv.button(scr)
maxbtn.align(lv.ALIGN.BOTTOM_RIGHT, 0, 0)
maxp = lv.label(maxbtn)
maxp.set_text('272,480')

lv.screen_load(scr)

event_loop = lv_utils.event_loop(asynchronous=True)

uasyncio.Loop.run_forever()
