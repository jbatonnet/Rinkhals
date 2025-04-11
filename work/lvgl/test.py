import asyncio
import time

import lvgl as lv
import lv_utils


MODE = 'windows'

def init():
    lv.init()

    if MODE == 'windows':
        disp = lv.windows_create_display('Rinkhals', 272, 480)
        touch = lv.windows_acquire_pointer_indev(disp)
        touch.set_display(disp)

    elif MODE == 'linux':
        disp = lv.linux_fbdev_create()
        lv.linux_fbdev_set_file(disp, '/dev/fb0')

        rot = lv.LV_DISPLAY_ROTATION_270
        disp.set_rotation(rot)

        touch = lv.evdev_create(lv.INDEV_TYPE.POINTER, '/dev/input/event0')
        touch.set_display(disp)

        # TODO Fine-tune calibration
        TOUCH_MAX_X = 460
        TOUCH_MAX_Y = 25
        TOUCH_MIN_X = 25
        TOUCH_MIN_Y = 235

        lv.evdev_set_calibration(touch, TOUCH_MIN_X, TOUCH_MIN_Y, TOUCH_MAX_X, TOUCH_MAX_Y)

def main():
    
    def debug_event(event):
        print(event)

    scr = lv.obj()

    btn = lv.button(scr)
    btn.align(lv.LV_ALIGN_CENTER, 0, 0)
    label = lv.label(btn)
    label.set_text('Hello Rinkhals!')

    minbtn = lv.button(scr)
    minbtn.align(lv.LV_ALIGN_TOP_LEFT, 0, 0)
    minp = lv.label(minbtn)
    minp.set_text('0,0')

    maxbtn = lv.button(scr)
    maxbtn.align(lv.LV_ALIGN_BOTTOM_RIGHT, 0, 0)
    maxp = lv.label(maxbtn)
    maxp.set_text('272,480')

    lv.screen_load(scr)


def loop_sync():
    while True:
        lv.tick_inc(16)
        lv.timer_handler()
        time.sleep(0.016)
async def loop_async():
    lv_utils.event_loop(asynchronous=True)
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    init()
    main()
    #asyncio.run(loop_async())
    loop_sync()
