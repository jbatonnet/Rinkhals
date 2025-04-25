import os
import lvgl as lv

lv.init()

DEBUG_RENDERING = False
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

# Constants
COLOR_PRIMARY = lv.color_make(0, 128, 255)
COLOR_BACKGROUND = lv.palette_darken(lv.PALETTE.GREY, 4)
COLOR_TEXT = lv.color_white()
COLOR_SECONDARY = lv.color_make(96, 96, 96)
COLOR_DANGER = lv.color_make(255, 64, 64)
COLOR_SUBTITLE = lv.color_make(160, 160, 160)
COLOR_DISABLED = lv.color_make(176, 176, 176)
COLOR_SHADOW = lv.color_make(96, 96, 96)
COLOR_DEBUG = lv.color_make(255, 0, 255)

GLOBAL_PADDING = lv.dpx(10)
TITLE_BAR_HEIGHT = lv.dpx(65)

# Assets
font_text = lv.tiny_ttf_create_file(SCRIPT_PATH + '/AlibabaSans-Regular.ttf', int(lv.dpx(19)))
font_title = lv.tiny_ttf_create_file(SCRIPT_PATH + '/AlibabaSans-Regular.ttf', int(lv.dpx(22)))
font_subtitle = lv.tiny_ttf_create_file(SCRIPT_PATH + '/AlibabaSans-Regular.ttf', int(lv.dpx(16)))
font_icon = lv.tiny_ttf_create_file(SCRIPT_PATH + '/MaterialIcons-Regular.ttf', int(lv.dpx(32)))

# Shared styles
style_debug = lv.style()
if style_debug:
    if DEBUG_RENDERING:
        style_debug.set_border_color(COLOR_DEBUG)
        style_debug.set_border_width(1)
        style_debug.set_border_side(lv.BORDER_SIDE.FULL)

style_screen = lv.style()
if style_screen:
    style_screen.set_bg_color(COLOR_BACKGROUND)
    style_screen.set_text_font(font_text)
    style_screen.set_text_color(COLOR_TEXT)
    style_screen.set_pad_all(GLOBAL_PADDING)
    style_screen.set_radius(0)
    
style_panel = lv.style()
if style_panel:
    style_panel.set_bg_color(COLOR_BACKGROUND)
    style_panel.set_text_font(font_text)
    style_panel.set_text_color(COLOR_TEXT)
    style_panel.set_pad_all(GLOBAL_PADDING)
    style_panel.set_radius(0)
    style_panel.set_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT)
    style_panel.set_border_width(0)

style_label_title = lv.style()
if style_label_title:
    style_label_title.set_text_font(font_title)

style_label_subtitle = lv.style()
if style_label_subtitle:
    style_label_subtitle.set_text_font(font_subtitle)
    style_label_subtitle.set_text_color(COLOR_SUBTITLE)
    style_label_subtitle.set_max_width(lv.pct(100))

style_label_text = lv.style()
if style_label_text:
    style_label_text.set_max_width(lv.pct(100))

style_button = lv.style()
if style_button:
    style_button.set_bg_color(lv.color_lighten(COLOR_BACKGROUND, 24))
    style_button.set_border_color(lv.color_lighten(COLOR_BACKGROUND, 72))
    style_button.set_border_width(1)
    style_button.set_border_side(lv.BORDER_SIDE.FULL)
    style_button.set_shadow_width(0)
    style_button.set_radius(lv.dpx(8))
    style_button.set_pad_hor(lv.dpx(10))
    style_button.set_height(lv.dpx(65))
    style_button.set_min_width(lv.dpx(65))
    style_button.set_text_align(lv.TEXT_ALIGN.CENTER)
    style_button.set_width(lv.SIZE_CONTENT)

style_button_icon = lv.style()
if style_button_icon:
    style_button_icon.set_bg_color(COLOR_BACKGROUND)
    style_button_icon.set_border_width(0)
    style_button_icon.set_shadow_width(0)
    style_button_icon.set_size(lv.dpx(65), lv.dpx(65))
    style_button_icon.set_text_align(lv.TEXT_ALIGN.CENTER)
    style_button_icon.set_text_font(font_icon)

style_button_pressed = lv.style()
if style_button_pressed:
    style_button_pressed.set_bg_color(lv.color_lighten(COLOR_BACKGROUND, 96))

style_button_disabled = lv.style()
if style_button_disabled:
    style_button_disabled.set_recolor(COLOR_BACKGROUND)
    style_button_disabled.set_text_color(lv.color_darken(COLOR_TEXT, 64))

style_title_bar = lv.style()
if style_title_bar:
    style_title_bar.set_height(TITLE_BAR_HEIGHT + 2)
    style_title_bar.set_width(lv.pct(100))
    style_title_bar.set_pad_all(0)

style_checkbox = lv.style()
if style_checkbox:
    style_checkbox.set_size(lv.dpx(55), lv.dpx(55))
    style_checkbox.set_bg_color(lv.color_lighten(COLOR_BACKGROUND, 24))
    style_checkbox.set_border_color(lv.color_lighten(COLOR_BACKGROUND, 72))
    style_checkbox.set_border_width(1)
    style_checkbox.set_min_width(0)
    style_checkbox.set_text_font(font_icon)
    style_checkbox.set_radius(lv.dpx(8))


# Styled objects
def screen():
    result = lv.obj(None)
    result.add_style(style_screen, lv.STATE.DEFAULT)
    result.add_style(style_debug, lv.STATE.DEFAULT)
    return result

def panel(parent):
    result = lv.obj(parent)
    result.add_style(style_panel, lv.STATE.DEFAULT)
    result.add_style(style_debug, lv.STATE.DEFAULT)
    
    def clear_event_cb():
        obj_clear_event_cb(result)
    result.clear_event_cb = clear_event_cb

    return result

def button(parent):
    result = lv.button(parent)
    result.add_style(style_button, lv.STATE.DEFAULT)
    result.add_style(style_button_pressed, lv.STATE.PRESSED)
    result.add_style(style_button_disabled, lv.STATE.DISABLED)
    result.add_style(style_debug, lv.STATE.DEFAULT)
    
    result_label = lv.label(result)
    result_label.set_text('')
    result_label.center()

    def clear_event_cb():
        obj_clear_event_cb(result)
    result.clear_event_cb = clear_event_cb

    def set_text(text):
        result_label.set_text(text)
    result.set_text = set_text

    return result

def button_icon(parent):
    result = button(parent)
    result.add_style(style_button_icon, lv.STATE.DEFAULT)
    result.add_style(style_debug, lv.STATE.DEFAULT)
    return result

def checkbox(parent):
    result = button(parent)
    result.add_style(style_checkbox, lv.STATE.DEFAULT)
    result.add_style(style_debug, lv.STATE.DEFAULT)

    result_label = lv.label(result)
    result_label.center()
    result_label.set_text('')

    def set_checked(enabled):
        result.set_style_text_opa(lv.OPA.COVER if enabled else lv.OPA.TRANSP, lv.STATE.DEFAULT)
    result.set_checked = set_checked

    def set_text(text):
        result_label.set_text(text)
    result.set_text = set_text

    return result

def image(parent):
    result = lv.image(parent)
    result.add_style(style_debug, lv.STATE.DEFAULT)
    return result

def label(parent):
    result = lv.label(parent)
    result.add_style(style_label_text, lv.STATE.DEFAULT)
    result.add_style(style_debug, lv.STATE.DEFAULT)
    result.set_long_mode(lv.LABEL_LONG_MODE.CLIP)
    return result

def title(parent):
    result = lv.label(parent)
    result.add_style(style_label_title, lv.STATE.DEFAULT)
    result.add_style(style_debug, lv.STATE.DEFAULT)
    return result

def subtitle(parent):
    result = lv.label(parent)
    result.add_style(style_label_subtitle, lv.STATE.DEFAULT)
    result.add_style(style_debug, lv.STATE.DEFAULT)
    result.set_long_mode(lv.LABEL_LONG_MODE.CLIP)
    return result

def title_bar(parent):
    result = panel(parent)
    result.add_style(style_title_bar, lv.STATE.DEFAULT)
    result.add_style(style_debug, lv.STATE.DEFAULT)
    return result

def flex_container(parent, flow = lv.FLEX_FLOW.COLUMN, align = lv.FLEX_ALIGN.START):
    result = panel(parent)
    result.set_flex_flow(flow)
    result.set_flex_align(lv.FLEX_ALIGN.START, align, align)

    if flow == lv.FLEX_FLOW.COLUMN:
        result.set_style_pad_left(GLOBAL_PADDING, lv.STATE.DEFAULT)
        result.set_style_pad_right(GLOBAL_PADDING, lv.STATE.DEFAULT)
        result.set_style_pad_row(GLOBAL_PADDING, lv.STATE.DEFAULT)
    elif flow == lv.FLEX_FLOW.ROW:
        result.set_style_pad_top(GLOBAL_PADDING, lv.STATE.DEFAULT)
        result.set_style_pad_bottom(GLOBAL_PADDING, lv.STATE.DEFAULT)
        result.set_style_pad_column(GLOBAL_PADDING, lv.STATE.DEFAULT)

    return result


# Helpers
def scale_image(image, size):
    scaling = size * 256 // image.get_self_width()
    image.set_size(size, size)
    image.set_scale(scaling)

def obj_clear_event_cb(obj: lv.obj):
    count = obj.get_event_count()
    for i in range(count):
        event_dsc = obj.get_event_dsc(0)
        cb = event_dsc.get_cb()
        obj.remove_event_cb(cb)

class lock:
    def __enter__(self):
        lv.lock()
    def __exit__(self, exc_type, exc_value, traceback):
        lv.unlock()
