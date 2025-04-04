import time
import lvgl as lv


SCREEN_WIDTH = 272
SCREEN_HEIGHT = 480


lv.init()



display = lv.disp_create(SCREEN_WIDTH, SCREEN_HEIGHT)
lv.disp_set_default(display)

def flush_callback(display, area, source):
    pass

lv.disp_set_flush_cb(display, flush_callback)

buffer = bytearray(SCREEN_WIDTH * SCREEN_HEIGHT * 4)
lv.disp_set_draw_buffers(display, buffer, None, len(buffer), lv.LV_DISPLAY_RENDER_MODE_DIRECT)
lv.disp_set_draw_buffers(display, buffer, None, len(buffer), lv.LV_DISPLAY_RENDER_MODE_DIRECT)




start = time.time()
    
while True:
    stop = time.time()
    diff = int((stop * 1000) - (start * 1000))
    if diff >= 1:
        start = stop
        lv.tick_inc(diff)
        lv.task_handler()
