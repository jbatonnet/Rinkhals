import os
import platform

from cffi import FFI

ffi = FFI()

_architecture = platform.architecture()
_path = f'{os.getcwd()}/work/lvgl'

if _architecture[1] == 'WindowsPE':
    _lvgl = ffi.dlopen(_path + '/lvgl-x64-windows.dll')
elif _architecture[1] == 'ELF':
    _lvgl = ffi.dlopen(_path + '/lvgl-arm-linux-uclibc.so')


# General
ffi.cdef("""
    void lv_init(void);
    bool lv_is_initialized(void);
    void lv_tick_inc(uint32_t tick_period);
    uint32_t lv_timer_handler(void);
""")

# Display and Input device
ffi.cdef("""
    typedef void lv_display_t;
    typedef void lv_indev_t;
         
    typedef enum {
        LV_DISPLAY_ROTATION_0 = 0,
        LV_DISPLAY_ROTATION_90,
        LV_DISPLAY_ROTATION_180,
        LV_DISPLAY_ROTATION_270
    } lv_display_rotation_t;
         
    typedef enum {
        LV_DISPLAY_RENDER_MODE_PARTIAL,
        LV_DISPLAY_RENDER_MODE_DIRECT,
        LV_DISPLAY_RENDER_MODE_FULL,
    } lv_display_render_mode_t;
         
    typedef struct {
        int32_t x1;
        int32_t y1;
        int32_t x2;
        int32_t y2;
    } lv_area_t;
         
    typedef void (*lv_display_flush_cb_t)(lv_display_t * disp, const lv_area_t * area, uint8_t * px_map);
         
    lv_display_t *lv_windows_create_display(const wchar_t *title, int32_t hor_res, int32_t ver_res, int32_t zoom_level, bool allow_dpi_override, bool simulator_mode);
    lv_indev_t *lv_windows_acquire_pointer_indev(lv_display_t *display);
    lv_indev_t *lv_windows_acquire_keypad_indev(lv_display_t *display);
    lv_indev_t *lv_windows_acquire_encoder_indev(lv_display_t *display);
         
    lv_display_t* lv_linux_fbdev_create();

    void lv_indev_set_display(lv_indev_t * indev, struct _lv_display_t * disp);
         
    lv_display_t * lv_display_create(int32_t hor_res, int32_t ver_res);
    void lv_display_set_buffers(lv_display_t * disp, void * buf1, void * buf2, uint32_t buf_size, lv_display_render_mode_t render_mode);
    void lv_display_set_rotation(lv_display_t * disp, lv_display_rotation_t rotation);
    void lv_display_set_flush_cb(lv_display_t * disp, lv_display_flush_cb_t flush_cb);
""")

LV_DISPLAY_ROTATION_0 = _lvgl.LV_DISPLAY_ROTATION_0
LV_DISPLAY_ROTATION_90 = _lvgl.LV_DISPLAY_ROTATION_90
LV_DISPLAY_ROTATION_180 = _lvgl.LV_DISPLAY_ROTATION_180
LV_DISPLAY_ROTATION_270 = _lvgl.LV_DISPLAY_ROTATION_270

LV_DISPLAY_RENDER_MODE_PARTIAL = _lvgl.LV_DISPLAY_RENDER_MODE_PARTIAL
LV_DISPLAY_RENDER_MODE_DIRECT = _lvgl.LV_DISPLAY_RENDER_MODE_DIRECT
LV_DISPLAY_RENDER_MODE_FULL = _lvgl.LV_DISPLAY_RENDER_MODE_FULL

# Objects
ffi.cdef("""
    typedef void lv_obj_t;
         
    typedef enum {
        LV_ALIGN_DEFAULT = 0,
        LV_ALIGN_TOP_LEFT,
        LV_ALIGN_TOP_MID,
        LV_ALIGN_TOP_RIGHT,
        LV_ALIGN_BOTTOM_LEFT,
        LV_ALIGN_BOTTOM_MID,
        LV_ALIGN_BOTTOM_RIGHT,
        LV_ALIGN_LEFT_MID,
        LV_ALIGN_RIGHT_MID,
        LV_ALIGN_CENTER,
        LV_ALIGN_OUT_TOP_LEFT,
        LV_ALIGN_OUT_TOP_MID,
        LV_ALIGN_OUT_TOP_RIGHT,
        LV_ALIGN_OUT_BOTTOM_LEFT,
        LV_ALIGN_OUT_BOTTOM_MID,
        LV_ALIGN_OUT_BOTTOM_RIGHT,
        LV_ALIGN_OUT_LEFT_TOP,
        LV_ALIGN_OUT_LEFT_MID,
        LV_ALIGN_OUT_LEFT_BOTTOM,
        LV_ALIGN_OUT_RIGHT_TOP,
        LV_ALIGN_OUT_RIGHT_MID,
        LV_ALIGN_OUT_RIGHT_BOTTOM,
    } lv_align_t;
         
    lv_obj_t * lv_obj_create(lv_obj_t * parent);
    void lv_obj_align(lv_obj_t * obj, lv_align_t align, int32_t x_ofs, int32_t y_ofs);
         
    lv_obj_t * lv_button_create(lv_obj_t * parent);
         
    lv_obj_t * lv_label_create(lv_obj_t * parent);
    void lv_label_set_text(lv_obj_t * obj, const char * text);
         
    void lv_screen_load(struct _lv_obj_t * scr);
""")
      
LV_ALIGN_DEFAULT = _lvgl.LV_ALIGN_DEFAULT
LV_ALIGN_TOP_LEFT = _lvgl.LV_ALIGN_TOP_LEFT
LV_ALIGN_TOP_MID = _lvgl.LV_ALIGN_TOP_MID
LV_ALIGN_TOP_RIGHT = _lvgl.LV_ALIGN_TOP_RIGHT
LV_ALIGN_BOTTOM_LEFT = _lvgl.LV_ALIGN_BOTTOM_LEFT
LV_ALIGN_BOTTOM_MID = _lvgl.LV_ALIGN_BOTTOM_MID
LV_ALIGN_BOTTOM_RIGHT = _lvgl.LV_ALIGN_BOTTOM_RIGHT
LV_ALIGN_LEFT_MID = _lvgl.LV_ALIGN_LEFT_MID
LV_ALIGN_RIGHT_MID = _lvgl.LV_ALIGN_RIGHT_MID
LV_ALIGN_CENTER = _lvgl.LV_ALIGN_CENTER
LV_ALIGN_OUT_TOP_LEFT = _lvgl.LV_ALIGN_OUT_TOP_LEFT
LV_ALIGN_OUT_TOP_MID = _lvgl.LV_ALIGN_OUT_TOP_MID
LV_ALIGN_OUT_TOP_RIGHT = _lvgl.LV_ALIGN_OUT_TOP_RIGHT
LV_ALIGN_OUT_BOTTOM_LEFT = _lvgl.LV_ALIGN_OUT_BOTTOM_LEFT
LV_ALIGN_OUT_BOTTOM_MID = _lvgl.LV_ALIGN_OUT_BOTTOM_MID
LV_ALIGN_OUT_BOTTOM_RIGHT = _lvgl.LV_ALIGN_OUT_BOTTOM_RIGHT
LV_ALIGN_OUT_LEFT_TOP = _lvgl.LV_ALIGN_OUT_LEFT_TOP
LV_ALIGN_OUT_LEFT_MID = _lvgl.LV_ALIGN_OUT_LEFT_MID
LV_ALIGN_OUT_LEFT_BOTTOM = _lvgl.LV_ALIGN_OUT_LEFT_BOTTOM
LV_ALIGN_OUT_RIGHT_TOP = _lvgl.LV_ALIGN_OUT_RIGHT_TOP
LV_ALIGN_OUT_RIGHT_MID = _lvgl.LV_ALIGN_OUT_RIGHT_MID
LV_ALIGN_OUT_RIGHT_BOTTOM = _lvgl.LV_ALIGN_OUT_RIGHT_BOTTOM






## Cute interface
def init() -> None:
    _lvgl.lv_init()
def is_initialized() -> bool:
    return _lvgl.lv_is_initialized()

def tick_inc(tick_period):
    _lvgl.lv_tick_inc(tick_period)
def task_handler():
    return _lvgl.lv_timer_handler()
def timer_handler():
    return _lvgl.lv_timer_handler()

def windows_create_display(title, hor_res, ver_res, zoom_level=100, allow_dpi_override=False, simulator_mode=True):
    result = _lvgl.lv_windows_create_display(ffi.new("wchar_t[]", title), hor_res, ver_res, zoom_level, allow_dpi_override, simulator_mode)
    return display(result) if result else None
def windows_acquire_pointer_indev(display):
    result = _lvgl.lv_windows_acquire_pointer_indev(display._pointer)
    return indev(result) if result else None

def linux_fbdev_create() -> None:
    return _lvgl.lv_linux_fbdev_create()

def screen_load(scr) -> None:
    return _lvgl.lv_screen_load(scr._pointer)

class display:
    _pointer = None

    def __init__(self, pointer):
        self._pointer = pointer

    def set_buffers(self, buf1, buf2, buf_size, render_mode):
        _lvgl.lv_display_set_buffers(self._pointer, buf1, buf2 or ffi.NULL, buf_size, render_mode)

    def set_rotation(self, rotation):
        _lvgl.lv_display_set_rotation(self._pointer, rotation)

    def set_flush_cb(self, flush_cb):
        def wrap_flush_cb(external_flush_cb):
            def flush_cb():
                pass
            return ffi.callback('void(*)(void *, lv_area_t *, uint8_t *)', flush_cb)
        _lvgl.lv_display_set_flush_cb(self._pointer, wrap_flush_cb(flush_cb))

class indev:
    _pointer = None

    def __init__(self, pointer):
        self._pointer = pointer

    def set_display(self, display) -> None:
        _lvgl.lv_indev_set_display(self._pointer, display._pointer)

class obj:
    _pointer = None

    def __init__(self, parent = None):
        self._pointer = _lvgl.lv_obj_create(parent._pointer if parent else ffi.NULL)

    def align(self, align, x_ofs, y_ofs):
        _lvgl.lv_obj_align(self._pointer, align, x_ofs, y_ofs)

class button(obj):
    def __init__(self, parent = None):
        self._pointer = _lvgl.lv_button_create(parent._pointer if parent else ffi.NULL)

class label(obj):
    def __init__(self, parent = None):
        self._pointer = _lvgl.lv_label_create(parent._pointer if parent else ffi.NULL)

    def set_text(self, text):
        _lvgl.lv_label_set_text(self._pointer, text.encode('utf-8'))
