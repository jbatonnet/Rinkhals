import os

# Detect current platform
_using_micropython = None
_target_library = None

try:
    import micropython

    _using_micropython = True
    _target_library = 'lvgl-arm-linux-uclibc.so'
except:
    _using_micropython = False

    try:
        import cffi
        import platform

        architecture = platform.architecture()
        if architecture[1] == 'WindowsPE':
            _target_library = 'lvgl-x64-windows.dll'
        elif architecture[1] == 'ELF':
            _target_library = 'lvgl-arm-linux-uclibc.so'
    except:
        pass

if _using_micropython is None or _target_library is None:
    raise Exception('Current platform is not supported')

# Find the library
def exists(path):
    try:
        os.stat(path)
        return True
    except:
        return False

_library_path = f'{os.getcwd()}/{_target_library}'
if not exists(_library_path):
    _library_path = f'{os.path.dirname(os.path.realpath(__file__))}/{_target_library}'
if not exists(_library_path):
    raise Exception(f'Unable to find library {_target_library}')

# Load the library
if _using_micropython:
    import ffi
    _lvgl = ffi.open(_library_path)
else:
    from cffi import FFI
    ffi = FFI()
    _lvgl = ffi.dlopen(_library_path)



# General
if not _using_micropython:
    ffi.cdef("""
        void lv_init(void);
        bool lv_is_initialized(void);
        void lv_tick_inc(uint32_t tick_period);
        uint32_t lv_timer_handler(void);
    """)

# Display and Input device
if not _using_micropython:
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
            
        typedef enum {
            LV_INDEV_TYPE_NONE,
            LV_INDEV_TYPE_POINTER,
            LV_INDEV_TYPE_KEYPAD,
            LV_INDEV_TYPE_BUTTON,
            LV_INDEV_TYPE_ENCODER,
        } lv_indev_type_t;
            
        typedef void (*lv_display_flush_cb_t)(lv_display_t * disp, const lv_area_t * area, uint8_t * px_map);
            
        lv_display_t *lv_windows_create_display(const wchar_t *title, int32_t hor_res, int32_t ver_res, int32_t zoom_level, bool allow_dpi_override, bool simulator_mode);
        lv_indev_t *lv_windows_acquire_pointer_indev(lv_display_t *display);
        lv_indev_t *lv_windows_acquire_keypad_indev(lv_display_t *display);
        lv_indev_t *lv_windows_acquire_encoder_indev(lv_display_t *display);
            
        lv_display_t* lv_linux_fbdev_create();
        void lv_linux_fbdev_set_file(lv_display_t * disp, const char * str);
        lv_indev_t *lv_evdev_create(lv_indev_type_t indev_type, const char *dev_path);
        void lv_evdev_set_swap_axes(lv_indev_t *indev, bool swap_axes);
        void lv_evdev_set_calibration(lv_indev_t *indev, int min_x, int min_y, int max_x, int max_y);

        void lv_indev_set_display(lv_indev_t * indev, struct _lv_display_t * disp);
            
        lv_display_t * lv_display_create(int32_t hor_res, int32_t ver_res);
        void lv_display_set_buffers(lv_display_t * disp, void * buf1, void * buf2, uint32_t buf_size, lv_display_render_mode_t render_mode);
        void lv_display_set_rotation(lv_display_t * disp, lv_display_rotation_t rotation);
        void lv_display_set_flush_cb(lv_display_t * disp, lv_display_flush_cb_t flush_cb);
    """)

DISPLAY_ROTATION_0 = _lvgl.LV_DISPLAY_ROTATION_0
DISPLAY_ROTATION_90 = _lvgl.LV_DISPLAY_ROTATION_90
DISPLAY_ROTATION_180 = _lvgl.LV_DISPLAY_ROTATION_180
DISPLAY_ROTATION_270 = _lvgl.LV_DISPLAY_ROTATION_270

DISPLAY_RENDER_MODE_PARTIAL = _lvgl.LV_DISPLAY_RENDER_MODE_PARTIAL
DISPLAY_RENDER_MODE_DIRECT = _lvgl.LV_DISPLAY_RENDER_MODE_DIRECT
DISPLAY_RENDER_MODE_FULL = _lvgl.LV_DISPLAY_RENDER_MODE_FULL

INDEV_TYPE_NONE = _lvgl.LV_INDEV_TYPE_NONE
INDEV_TYPE_POINTER = _lvgl.LV_INDEV_TYPE_POINTER
INDEV_TYPE_KEYPAD = _lvgl.LV_INDEV_TYPE_KEYPAD
INDEV_TYPE_BUTTON = _lvgl.LV_INDEV_TYPE_BUTTON
INDEV_TYPE_ENCODER = _lvgl.LV_INDEV_TYPE_ENCODER

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
      
ALIGN_DEFAULT = _lvgl.LV_ALIGN_DEFAULT
ALIGN_TOP_LEFT = _lvgl.LV_ALIGN_TOP_LEFT
ALIGN_TOP_MID = _lvgl.LV_ALIGN_TOP_MID
ALIGN_TOP_RIGHT = _lvgl.LV_ALIGN_TOP_RIGHT
ALIGN_BOTTOM_LEFT = _lvgl.LV_ALIGN_BOTTOM_LEFT
ALIGN_BOTTOM_MID = _lvgl.LV_ALIGN_BOTTOM_MID
ALIGN_BOTTOM_RIGHT = _lvgl.LV_ALIGN_BOTTOM_RIGHT
ALIGN_LEFT_MID = _lvgl.LV_ALIGN_LEFT_MID
ALIGN_RIGHT_MID = _lvgl.LV_ALIGN_RIGHT_MID
ALIGN_CENTER = _lvgl.LV_ALIGN_CENTER
ALIGN_OUT_TOP_LEFT = _lvgl.LV_ALIGN_OUT_TOP_LEFT
ALIGN_OUT_TOP_MID = _lvgl.LV_ALIGN_OUT_TOP_MID
ALIGN_OUT_TOP_RIGHT = _lvgl.LV_ALIGN_OUT_TOP_RIGHT
ALIGN_OUT_BOTTOM_LEFT = _lvgl.LV_ALIGN_OUT_BOTTOM_LEFT
ALIGN_OUT_BOTTOM_MID = _lvgl.LV_ALIGN_OUT_BOTTOM_MID
ALIGN_OUT_BOTTOM_RIGHT = _lvgl.LV_ALIGN_OUT_BOTTOM_RIGHT
ALIGN_OUT_LEFT_TOP = _lvgl.LV_ALIGN_OUT_LEFT_TOP
ALIGN_OUT_LEFT_MID = _lvgl.LV_ALIGN_OUT_LEFT_MID
ALIGN_OUT_LEFT_BOTTOM = _lvgl.LV_ALIGN_OUT_LEFT_BOTTOM
ALIGN_OUT_RIGHT_TOP = _lvgl.LV_ALIGN_OUT_RIGHT_TOP
ALIGN_OUT_RIGHT_MID = _lvgl.LV_ALIGN_OUT_RIGHT_MID
ALIGN_OUT_RIGHT_BOTTOM = _lvgl.LV_ALIGN_OUT_RIGHT_BOTTOM






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

def linux_fbdev_create():
    result = _lvgl.lv_linux_fbdev_create()
    return display(result) if result else None
def linux_fbdev_set_file(disp, str) -> None:
    _lvgl.lv_linux_fbdev_set_file(disp._pointer, str.encode('utf-8'))
def evdev_create(indev_type, dev_path):
    result = _lvgl.lv_evdev_create(indev_type, dev_path.encode('utf-8'))
    return indev(result) if result else None
def evdev_set_swap_axes(indev, swap_axes: bool) -> None:
    _lvgl.lv_evdev_set_swap_axes(indev._pointer, swap_axes)
def evdev_set_calibration(indev, min_x, min_y, max_x, max_y) -> None:
    _lvgl.lv_evdev_set_calibration(indev._pointer, min_x, min_y, max_x, max_y)
    
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
