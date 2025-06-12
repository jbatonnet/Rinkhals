import os
import lvgl as lv

DEBUG_RENDERING = False
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
ASSETS_PATH = os.path.join(SCRIPT_PATH, 'assets')

# Sizes
def get_global_margin(): return lv.dpx(10)
def get_title_bar_height(): return lv.dpx(65)
def get_large_button_height(): return lv.dpx(130)

# Colors and gradients
COLOR_PRIMARY = lv.color_make(0, 128, 255)
COLOR_BACKGROUND = lv.palette_darken(lv.PALETTE.GREY, 4)
COLOR_TEXT = lv.color_white()
COLOR_SECONDARY = lv.color_make(96, 96, 96)
COLOR_DANGER = lv.color_make(255, 64, 64)
COLOR_SUBTITLE = lv.color_make(160, 160, 160)
COLOR_DISABLED = lv.color_make(176, 176, 176)
COLOR_SHADOW = lv.color_make(96, 96, 96)
COLOR_DEBUG = lv.color_make(255, 0, 255)

gradient_background = lv.grad_dsc()
if gradient_background:
    colors = [
        COLOR_BACKGROUND,
        lv.color_mix(COLOR_BACKGROUND, COLOR_PRIMARY, 224)
    ]
    gradient_background.init_stops(colors, None, None, len(colors))
    gradient_background.linear_init(lv.pct(0), lv.pct(0), lv.pct(100), lv.pct(50), lv.GRAD_EXTEND.PAD)

# Fonts
def get_font_text(): return lv.tiny_ttf_create_file(ASSETS_PATH + '/AlibabaSans-Regular.ttf', int(lv.dpx(19)))
def get_font_title(): return lv.tiny_ttf_create_file(ASSETS_PATH + '/AlibabaSans-Regular.ttf', int(lv.dpx(22)))
def get_font_subtitle(): return lv.tiny_ttf_create_file(ASSETS_PATH + '/AlibabaSans-Regular.ttf', int(lv.dpx(16)))
def get_font_icon(): return lv.tiny_ttf_create_file(ASSETS_PATH + '/MaterialIcons-Regular.ttf', int(lv.dpx(32)))
def get_font_icon_small(): return lv.tiny_ttf_create_file(ASSETS_PATH + '/MaterialIcons-Regular.ttf', int(lv.dpx(20)))

# Shared styles
def get_style_debug():
    style_debug = lv.style()

    global DEBUG_RENDERING
    if DEBUG_RENDERING:
        style_debug.set_border_color(COLOR_DEBUG)
        style_debug.set_border_width(1)
        style_debug.set_border_side(lv.BORDER_SIDE.FULL)

    return style_debug
def get_style_screen():
    style_screen = lv.style()
    style_screen.set_bg_grad(gradient_background)
    style_screen.set_bg_opa(lv.OPA.COVER)
    style_screen.set_text_font(get_font_text())
    style_screen.set_text_color(COLOR_TEXT)
    style_screen.set_pad_all(get_global_margin())
    style_screen.set_radius(0)
    return style_screen
def get_style_panel():
    style_panel = lv.style()
    style_panel.set_bg_opa(lv.OPA.TRANSP)
    style_panel.set_text_font(get_font_text())
    style_panel.set_text_color(COLOR_TEXT)
    style_panel.set_pad_all(get_global_margin())
    style_panel.set_radius(0)
    style_panel.set_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT)
    style_panel.set_border_side(lv.BORDER_SIDE.NONE)
    style_panel.set_border_width(1)
    style_panel.set_border_color(lv.color_lighten(COLOR_BACKGROUND, 32))
    style_panel.set_border_opa(lv.OPA.COVER)
    return style_panel
def get_style_panel_pressed():
    style_panel_pressed = lv.style()
    style_panel_pressed.set_bg_color(lv.color_white())
    style_panel_pressed.set_bg_opa(lv.OPA._20)
    return style_panel_pressed
def get_style_label_title():
    style_label_title = lv.style()
    style_label_title.set_text_font(get_font_title())
    return style_label_title
def get_style_label_subtitle():
    style_label_subtitle = lv.style()
    style_label_subtitle.set_text_font(get_font_subtitle())
    style_label_subtitle.set_text_color(COLOR_SUBTITLE)
    style_label_subtitle.set_max_width(lv.pct(100))
    return style_label_subtitle
def get_style_label_text():
    style_label_text = lv.style()
    style_label_text.set_max_width(lv.pct(100))
    return style_label_text
def get_style_button():
    style_button = lv.style()
    style_button.set_bg_opa(lv.OPA.COVER)
    style_button.set_bg_color(lv.color_lighten(COLOR_BACKGROUND, 24))
    style_button.set_border_color(lv.color_lighten(COLOR_BACKGROUND, 72))
    style_button.set_border_width(1)
    style_button.set_border_side(lv.BORDER_SIDE.FULL)
    style_button.set_shadow_width(0)
    style_button.set_radius(lv.dpx(8))
    style_button.set_pad_hor(lv.dpx(10))
    style_button.set_min_width(lv.dpx(65))
    style_button.set_width(lv.SIZE_CONTENT)
    style_button.set_height(lv.dpx(65))
    style_button.set_text_align(lv.TEXT_ALIGN.CENTER)
    return style_button
def get_style_button_icon():
    style_button_icon = lv.style()
    style_button_icon.set_bg_opa(lv.OPA.TRANSP)
    style_button_icon.set_border_width(0)
    style_button_icon.set_shadow_width(0)
    style_button_icon.set_size(lv.dpx(65), lv.dpx(65))
    style_button_icon.set_text_align(lv.TEXT_ALIGN.CENTER)
    style_button_icon.set_text_font(get_font_icon())
    return style_button_icon
def get_style_button_pressed():
    style_button_pressed = lv.style()
    style_button_pressed.set_bg_opa(lv.OPA.COVER)
    style_button_pressed.set_bg_color(lv.color_lighten(COLOR_BACKGROUND, 96))
    return style_button_pressed
def get_style_button_disabled():
    style_button_disabled = lv.style()
    style_button_disabled.set_recolor(COLOR_BACKGROUND)
    style_button_disabled.set_text_color(lv.color_darken(COLOR_TEXT, 64))
    return style_button_disabled
def get_style_title_bar():
    style_title_bar = lv.style()
    style_title_bar.set_height(get_title_bar_height() + 2)
    style_title_bar.set_width(lv.pct(100))
    style_title_bar.set_bg_opa(lv.OPA.TRANSP)
    style_title_bar.set_pad_all(0)
    return style_title_bar
def get_style_checkbox():
    style_checkbox = lv.style()
    style_checkbox.set_size(lv.dpx(55), lv.dpx(55))
    style_checkbox.set_bg_color(lv.color_lighten(COLOR_BACKGROUND, 24))
    style_checkbox.set_border_color(lv.color_lighten(COLOR_BACKGROUND, 72))
    style_checkbox.set_border_width(1)
    style_checkbox.set_min_width(0)
    style_checkbox.set_text_font(get_font_icon())
    style_checkbox.set_radius(lv.dpx(8))
    return style_checkbox
def get_style_tag():
    style_tag = lv.style()
    style_tag.set_text_font(get_font_subtitle())
    style_tag.set_text_color(COLOR_TEXT)
    style_tag.set_bg_opa(lv.OPA.COVER)
    style_tag.set_pad_ver(lv.dpx(5))
    style_tag.set_pad_left(lv.dpx(5))
    style_tag.set_pad_right(lv.dpx(15))
    style_tag.set_radius(lv.dpx(25))
    style_tag.set_width(lv.SIZE_CONTENT)
    style_tag.set_height(lv.SIZE_CONTENT)
    style_tag.set_border_width(0)
    style_tag.set_text_color(COLOR_BACKGROUND)
    style_tag.set_max_width(lv.pct(100))
    return style_tag
def get_style_tag_pressed():
    style_tag_pressed = lv.style()
    style_tag_pressed.set_recolor(lv.color_white())
    style_tag_pressed.set_recolor_opa(lv.OPA._40)
    #style_tag_pressed.set_transform_scale_x(280)
    #style_tag_pressed.set_transform_scale_y(280)
    return style_tag_pressed
def get_style_modal():
    style_modal = lv.style()
    style_modal.set_bg_color(COLOR_BACKGROUND)
    style_modal.set_bg_opa(lv.OPA.COVER)
    style_modal.set_radius(8)
    style_modal.set_pad_all(lv.dpx(20))
    return style_modal

# Styled objects
def screen(tag=None):
    result = lv.obj(None)
    result.tag = tag
    result.add_style(get_style_screen(), lv.STATE.DEFAULT)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)
    result.add_flag(lv.OBJ_FLAG.USER_1)

    _obj_add_debug_label(result)
    return result

def panel(parent, flex_flow=None, flex_align=lv.FLEX_ALIGN.START, tag=None):
    result = lv.obj(parent)
    result.tag = tag
    result.add_style(get_style_panel(), lv.STATE.DEFAULT)
    result.add_style(get_style_panel_pressed(), lv.STATE.PRESSED)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)
    result.set_state(lv.STATE.DISABLED, True)

    if flex_flow is not None:
        result.set_flex_flow(flex_flow)
        result.set_flex_align(lv.FLEX_ALIGN.START, flex_align, flex_align)

        if flex_flow == lv.FLEX_FLOW.COLUMN or flex_flow == lv.FLEX_FLOW.COLUMN_WRAP:
            result.set_style_pad_left(get_global_margin(), lv.STATE.DEFAULT)
            result.set_style_pad_right(get_global_margin(), lv.STATE.DEFAULT)
            result.set_style_pad_row(get_global_margin(), lv.STATE.DEFAULT)

        elif flex_flow == lv.FLEX_FLOW.ROW or flex_flow == lv.FLEX_FLOW.ROW_WRAP:
            result.set_style_pad_top(get_global_margin(), lv.STATE.DEFAULT)
            result.set_style_pad_bottom(get_global_margin(), lv.STATE.DEFAULT)
            result.set_style_pad_column(get_global_margin(), lv.STATE.DEFAULT)
    
    def clear_event_cb():
        _obj_clear_event_cb(result)
    result.clear_event_cb = clear_event_cb

    _obj_add_debug_label(result)
    return result

def modal(parent, tag=None):
    result = panel(parent)
    result.tag = tag

    result.add_style(get_style_modal(), lv.STATE.DEFAULT)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)

    result.add_flag(lv.OBJ_FLAG.HIDDEN)
    result.set_width(lv.dpx(300))
    result.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    result.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    result.center()

    _obj_add_debug_label(result)
    return result

def button(parent):
    result = lv.button(parent)
    result.add_style(get_style_button(), lv.STATE.DEFAULT)
    result.add_style(get_style_button_pressed(), lv.STATE.PRESSED)
    result.add_style(get_style_button_disabled(), lv.STATE.DISABLED)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)
    result.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    result.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    result.set_style_pad_row(get_global_margin(), lv.STATE.DEFAULT)

    # Dumb fix for that blue flash when clicking button
    result.set_style_recolor(COLOR_BACKGROUND, lv.STATE.DEFAULT)
    result.set_style_recolor(COLOR_BACKGROUND, lv.STATE.CHECKED)
    result.set_style_recolor(COLOR_BACKGROUND, lv.STATE.FOCUSED)
    result.set_style_recolor(COLOR_BACKGROUND, lv.STATE.FOCUS_KEY)
    result.set_style_recolor(COLOR_BACKGROUND, lv.STATE.EDITED)
    result.set_style_recolor(COLOR_BACKGROUND, lv.STATE.HOVERED)
    result.set_style_recolor(COLOR_BACKGROUND, lv.STATE.PRESSED)
    result.set_style_recolor(COLOR_BACKGROUND, lv.STATE.SCROLLED)
    result.set_style_recolor(COLOR_BACKGROUND, lv.STATE.DISABLED)
    
    result_icon = lv.label(result)
    result_icon.add_style(get_style_debug(), lv.STATE.DEFAULT)
    result_icon.set_style_text_font(get_font_icon(), lv.STATE.DEFAULT)
    result_icon.set_width(lv.SIZE_CONTENT)
    result_icon.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)
    result_icon.center()

    result_label = lv.label(result)
    result_label.add_style(get_style_debug(), lv.STATE.DEFAULT)
    result_label.set_width(lv.SIZE_CONTENT)
    result_label.center()

    def set_width(width):
        result_icon.set_width(lv.pct(100))
        result_label.set_width(lv.pct(100))
        result.set_width_internal(width)
    result.set_width_internal = result.set_width
    result.set_width = set_width
    
    def set_size(width, height):
        result_icon.set_width(lv.pct(100))
        result_label.set_width(lv.pct(100))
        result.set_size_internal(width, height)
    result.set_size_internal = result.set_size
    result.set_size = set_size

    def clear_event_cb():
        _obj_clear_event_cb(result)
    result.clear_event_cb = clear_event_cb

    def set_icon(icon):
        result_icon.set_text(icon)
        if icon:
            result_icon.remove_flag(lv.OBJ_FLAG.HIDDEN)
        else:
            result_icon.add_flag(lv.OBJ_FLAG.HIDDEN)
    result.set_icon = set_icon

    def set_text(text):
        result_label.set_text(text)
        if text:
            result_label.remove_flag(lv.OBJ_FLAG.HIDDEN)
        else:
            result_label.add_flag(lv.OBJ_FLAG.HIDDEN)
    result.set_text = set_text

    result.set_text('')
    result.set_icon('')

    return result

def button_icon(parent):
    result = button(parent)
    result.add_style(get_style_button_icon(), lv.STATE.DEFAULT)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)
    return result

def checkbox(parent):
    result = button(parent)
    result.add_style(get_style_checkbox(), lv.STATE.DEFAULT)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)

    result_label = lv.label(result)
    result_label.center()
    result_label.set_text('')

    def set_checked(enabled):
        result.set_style_text_opa(lv.OPA.COVER if enabled else lv.OPA.TRANSP, lv.STATE.DEFAULT)
        result.state_checked = enabled
    def get_checked():
        return result.state_checked
    result.state_checked = False
    result.set_checked = set_checked
    result.get_checked = get_checked

    def set_text(text):
        result_label.set_text(text)
    result.set_text = set_text

    return result

def image(parent):
    result = lv.image(parent)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)

    def scale_to(size):
        scaling = size * 256 // result.get_self_width()
        scaling = size * 256 // result.get_self_width()
        result.set_size(size, size)
        result.set_scale(scaling)
    result.scale_to = scale_to

    return result

def label(parent):
    result = lv.label(parent)
    result.add_style(get_style_label_text(), lv.STATE.DEFAULT)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)
    result.set_long_mode(lv.LABEL_LONG_MODE.CLIP)
    return result

def title(parent):
    result = lv.label(parent)
    result.add_style(get_style_label_title(), lv.STATE.DEFAULT)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)
    return result

def subtitle(parent):
    result = lv.label(parent)
    result.add_style(get_style_label_subtitle(), lv.STATE.DEFAULT)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)
    result.set_long_mode(lv.LABEL_LONG_MODE.CLIP)
    return result

def title_bar(parent):
    result = panel(parent)
    result.add_style(get_style_title_bar(), lv.STATE.DEFAULT)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)
    return result

def tag(parent):
    result = lv.obj(parent)
    result.set_flex_flow(lv.FLEX_FLOW.ROW)
    result.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    result.add_style(get_style_tag(), lv.STATE.DEFAULT)
    result.add_style(get_style_tag_pressed(), lv.STATE.PRESSED)
    result.add_style(get_style_debug(), lv.STATE.DEFAULT)

    result_icon = label(result)
    result_icon.set_style_text_font(get_font_icon_small(), lv.STATE.DEFAULT)
    #result_icon.set_align(lv.ALIGN.LEFT_MID)
    result_icon.set_style_bg_opa(lv.OPA.COVER, lv.STATE.DEFAULT)
    result_icon.set_style_pad_all(lv.dpx(8), lv.STATE.DEFAULT)
    result_icon.set_style_radius(lv.dpx(20), lv.STATE.DEFAULT)
    result_icon.set_style_bg_color(lv.color_white(), lv.STATE.DEFAULT)
    result_icon.set_text('')
    result_icon.add_flag(lv.OBJ_FLAG.HIDDEN)
    
    result_label = label(result)
    #result.set_width(lv.SIZE_CONTENT)
    #result_label.set_style_min_height(get_font_text().get_line_height(), lv.STATE.DEFAULT)
    #result_label.set_long_mode(lv.LABEL_LONG_MODE.DOTS)
    
    def set_icon(icon):
        result_icon.set_text(icon)
        result_icon.remove_flag(lv.OBJ_FLAG.HIDDEN)
    def set_text(text):
        result_label.set_text(text)
    def set_color(color):
        result.set_style_bg_color(lv.color_lighten(color, 144), lv.STATE.DEFAULT)
        result_icon.set_style_text_color(lv.color_darken(color, 128), lv.STATE.DEFAULT)
        #result_icon.set_style_bg_color(lv.color_lighten(color, 64), lv.STATE.DEFAULT)

    result.set_icon = set_icon
    result.set_text = set_text
    result.set_color = set_color

    return result


# Debug
# def theme_debug_apply(t, o):
#     if not DEBUG_RENDERING:
#         return
#     if isinstance(o, lv.obj):
#         if o.has_flag(lv.OBJ_FLAG.USER_1):
#             o.set_style_border_color(COLOR_DEBUG, lv.STATE.DEFAULT)
#             o.set_style_border_width(1, lv.STATE.DEFAULT)
#             o.set_style_border_side(lv.BORDER_SIDE.FULL, lv.STATE.DEFAULT)
#theme_debug = lv.theme_default_init(None, COLOR_PRIMARY, COLOR_SECONDARY, True, font_text)
#theme_debug.set_parent(lv.theme_default_get())
#theme_debug.set_apply_cb(theme_debug_apply)


# Helpers
def set_debug_rendering(enabled: bool):
    global DEBUG_RENDERING
    DEBUG_RENDERING = enabled

def _obj_clear_event_cb(obj: lv.obj):
    count = obj.get_event_count()

    # We must remove event in reverse because LVGL might not clear the event list if it's traversing the list
    # For example trying to remove the cb while being in the cb
    for i in range(count, 0, -1):
        result = obj.remove_event(i - 1)
        if not result:
            raise Exception('Could not clear object events')

def _obj_add_debug_label(obj: lv.obj):
    global DEBUG_RENDERING
    if not DEBUG_RENDERING:
        return
    
    if obj.tag:
        obj.set_user_data(obj.tag)

        label_debug = lv.label(obj)
        label_debug.set_align(lv.ALIGN.TOP_RIGHT)
        label_debug.add_flag(lv.OBJ_FLAG.IGNORE_LAYOUT)
        label_debug.set_text(obj.tag)

class lock:
    def __enter__(self):
        lv.lock()
    def __exit__(self, exc_type, exc_value, traceback):
        lv.unlock()
