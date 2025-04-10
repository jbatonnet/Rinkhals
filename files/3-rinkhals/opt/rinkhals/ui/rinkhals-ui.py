import os
import time
import sys
import json
import re
import random
import threading
import traceback
import logging
import psutil
import requests
import subprocess

import paho.mqtt.client as paho

import lvgl as lv


class JSONWithCommentsDecoder(json.JSONDecoder):
    def __init__(self, **kwgs):
        super().__init__(**kwgs)
    def decode(self, s: str):
        regex = r"""("(?:\\"|[^"])*?")|(\/\*(?:.|\s)*?\*\/|\/\/.*)"""
        s = re.sub(regex, r"\1", s)  # , flags = re.X | re.M)
        return super().decode(s)

cache_items = {}

def shell(command):
    if USING_SIMULATOR:
        result = subprocess.check_output(['sh', '-c', command])
        result = result.decode('utf-8').strip()
    else:
        temp_output = f'/tmp/rinkhals/output-{random.randint(1000, 9999)}'

        os.system(f'{command} > {temp_output}')
        if os.path.exists(temp_output):
            with open(temp_output) as f:
                result = f.read().strip()
            os.remove(temp_output)
        else:
            result = ''

    logging.info(f'Shell "{command}" => "{result}"')
    return result
def shell_async(command, callback):
    def thread():
        result = shell(command)
        if callback:
            callback(result)
    t = threading.Thread(target=thread)
    t.start()
def run_async(callback):
    t = threading.Thread(target=callback)
    t.start()
def cache(getter, key = None):
    key = key or ''
    key = f'line:{sys._getframe().f_back.f_lineno}|{key}'
    item = cache_items.get(key)
    if item is None:
        item = getter()
        cache_items[key] = item
    return item
def ellipsis(text, length):
    if len(text) > length:
        text = text[:int(length / 2)] + '...' + text[-int(length / 2):]
    return text


DEBUG = os.getenv('DEBUG')
DEBUG = not not DEBUG
#DEBUG = True

SIMULATED_PRINTER = 'KS1'


# Setup logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Detect Rinkhals root
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
RINKHALS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_PATH)))

USING_SIMULATOR = lv.helpers.is_windows()
USING_SHELL = True
if USING_SIMULATOR:
    if os.system('sh -c "echo"') != 0:
        USING_SHELL = False
    else:
        RINKHALS_ROOT = RINKHALS_ROOT.replace('\\', '/')
    if os.system('sh -c "ls /mnt/c"') == 0:
        RINKHALS_ROOT = '/mnt/' + RINKHALS_ROOT[0].lower() + RINKHALS_ROOT[2:]

# Detect environment and tools
if USING_SIMULATOR:
    RINKHALS_HOME = f'{RINKHALS_ROOT}/../4-apps/home/rinkhals'
    RINKHALS_VERSION = 'dev'
    KOBRA_MODEL = 'Anycubic Kobra'
    KOBRA_MODEL_CODE = SIMULATED_PRINTER
    KOBRA_VERSION = '1.2.3.4'

    if KOBRA_MODEL_CODE == 'KS1':
        QT_QPA_PLATFORM = 'linuxfb:fb=/dev/fb0:size=800x480:rotation=180:offset=0x0:nographicsmodeswitch'
    else:
        QT_QPA_PLATFORM = 'linuxfb:fb=/dev/fb0:size=480x272:rotation=90:offset=0x0:nographicsmodeswitch'

    def list_apps():
        system_apps = [ f.name for f in os.scandir(f'{RINKHALS_HOME}/apps') if f.is_dir() ]
        user_apps = [ f.name for f in os.scandir(f'{RINKHALS_ROOT}/../../../Rinkhals.apps/apps') if f.is_dir() ] if os.path.exists(f'{RINKHALS_ROOT}/../../../Rinkhals.apps/apps') else []
        additional_apps = [ 'test-1', 'test-2', 'test-3', 'test-4', 'test-5', 'test-6', 'test-7', 'test-8' ]
        return ' '.join(system_apps + user_apps + additional_apps)
    def get_app_root(app):
        if os.path.exists(f'{RINKHALS_HOME}/apps/{app}'): return f'{RINKHALS_HOME}/apps/{app}'
        if os.path.exists(f'{RINKHALS_ROOT}/../../../Rinkhals.apps/apps/{app}'): return f'{RINKHALS_ROOT}/../../../Rinkhals.apps/apps/{app}'
        return ''
    def is_app_enabled(app): return '1' if os.path.exists(f'{RINKHALS_HOME}/apps/{app}/.enabled') else '0'
    def get_app_status(app): return 'started' if is_app_enabled(app) == '1' else 'stopped'
    def get_app_pids(app): return str(os.getpid()) if get_app_status(app) == 'started' else ''
    def enable_app(app): pass
    def disable_app(app): pass
    def start_app(app, timeout): pass
    def stop_app(app): pass
    def get_app_property(app, property): return 'https://github.com/jbatonnet/Rinkhals' if property == 'link_output' else ''
    def set_app_property(app, property, value): pass
    def set_temporary_app_property(app, property, value): pass

    def are_apps_enabled(): return { a: is_app_enabled(a) for a in list_apps().split(' ') }
else:
    environment = shell(f'. /useremain/rinkhals/.current/tools.sh && python -c "import os, json; print(json.dumps(dict(os.environ)))"')
    environment = json.loads(environment)

    RINKHALS_ROOT = environment['RINKHALS_ROOT']
    RINKHALS_HOME = environment['RINKHALS_HOME']
    RINKHALS_VERSION = environment['RINKHALS_VERSION']
    KOBRA_MODEL_ID = environment['KOBRA_MODEL_ID']
    KOBRA_MODEL = environment['KOBRA_MODEL']
    KOBRA_MODEL_CODE = environment['KOBRA_MODEL_CODE']
    KOBRA_VERSION = environment['KOBRA_VERSION']
    KOBRA_DEVICE_ID = environment['KOBRA_DEVICE_ID']
    QT_QPA_PLATFORM = environment['QT_QPA_PLATFORM']

    def load_tool_function(function_name):
        def tool_function(*args):
            return shell(f'. /useremain/rinkhals/.current/tools.sh && {function_name} ' + ' '.join([ str(a) for a in args ]))
        return tool_function

    list_apps = load_tool_function('list_apps')
    get_app_root = load_tool_function('get_app_root')
    get_app_status = load_tool_function('get_app_status')
    get_app_pids = load_tool_function('get_app_pids')
    is_app_enabled = load_tool_function('is_app_enabled')
    enable_app = load_tool_function('enable_app')
    disable_app = load_tool_function('disable_app')
    start_app = load_tool_function('start_app')
    stop_app = load_tool_function('stop_app')
    get_app_property = load_tool_function('get_app_property')
    set_app_property = load_tool_function('set_app_property')
    set_temporary_app_property = load_tool_function('set_temporary_app_property')

    def are_apps_enabled():
        result = shell('. /useremain/rinkhals/.current/tools.sh && for a in $(list_apps); do echo "$a $(is_app_enabled $a)"; done')
        apps = result.splitlines()
        apps = [ a.split(' ') for a in apps ]
        return { a[0]: a[1] for a in apps }
        
# Detect screen parameters
screen_options = QT_QPA_PLATFORM.split(':')
screen_options = [ o.split('=') for o in screen_options ]
screen_options = { o[0]: o[1] if len(o) > 1 else None for o in screen_options }

resolution_match = re.search('^([0-9]+)x([0-9]+)$', screen_options['size'])

SCREEN_WIDTH = int(resolution_match[1])
SCREEN_HEIGHT = int(resolution_match[2])
SCREEN_ROTATION = int(screen_options['rotation'])

if SCREEN_ROTATION % 180 == 90:
    (SCREEN_WIDTH, SCREEN_HEIGHT) = (SCREEN_HEIGHT, SCREEN_WIDTH)

if KOBRA_MODEL_CODE == 'KS1':
    TOUCH_CALIBRATION_MIN_X = 800
    TOUCH_CALIBRATION_MAX_X = 0
    TOUCH_CALIBRATION_MIN_Y = 480
    TOUCH_CALIBRATION_MAX_Y = 0
else:
    TOUCH_CALIBRATION_MIN_X = 235
    TOUCH_CALIBRATION_MAX_X = 25
    TOUCH_CALIBRATION_MIN_Y = 460
    TOUCH_CALIBRATION_MAX_Y = 25

# Detect LAN mode
REMOTE_MODE = 'cloud'
if os.path.isfile('/useremain/dev/remote_ctrl_mode'):
    with open('/useremain/dev/remote_ctrl_mode', 'r') as f:
        REMOTE_MODE = f.read().strip()


class Program:
    display = None

    def __init__(self):
        lv.init()

        if lv.helpers.is_windows():
            self.display = lv.windows_create_display('Rinkhals', SCREEN_WIDTH, SCREEN_HEIGHT, 100, False, True)
            touch = lv.windows_acquire_pointer_indev(self.display)
            touch.set_display(self.display)

        elif lv.helpers.is_linux():
            self.display = lv.linux_fbdev_create()
            lv.linux_fbdev_set_file(self.display, '/dev/fb0')

            if SCREEN_ROTATION == 0: self.display.set_rotation(lv.DISPLAY_ROTATION._0)
            elif SCREEN_ROTATION == 90: self.display.set_rotation(lv.DISPLAY_ROTATION._90)
            elif SCREEN_ROTATION == 180: self.display.set_rotation(lv.DISPLAY_ROTATION._180)
            elif SCREEN_ROTATION == 270 or SCREEN_ROTATION == -90: self.display.set_rotation(lv.DISPLAY_ROTATION._270)

            touch = lv.evdev_create(lv.INDEV_TYPE.POINTER, '/dev/input/event0')
            touch.set_display(self.display)

            lv.evdev_set_calibration(touch, TOUCH_CALIBRATION_MIN_X, TOUCH_CALIBRATION_MIN_Y, TOUCH_CALIBRATION_MAX_X, TOUCH_CALIBRATION_MAX_Y)

        if KOBRA_MODEL_CODE == 'KS1':
            self.display.set_dpi(180)
        else:
            self.display.set_dpi(130)

        logging.debug(f'Root: {RINKHALS_ROOT}')
        logging.debug(f'Home: {RINKHALS_HOME}')

        # Subscribe to print event to exit in case of print
        if not lv.helpers.is_linux() and REMOTE_MODE == 'lan':
            self.monitor_mqtt()

        # Monitor K3SysUi process to exit if it dies
        if lv.helpers.is_linux():
            monitor_thread = threading.Thread(target = self.monitor_k3sysui)
            monitor_thread.start()

        # Layout and draw
        global lvr
        import lvgl_rinkhals as lvr

        self.layout()

    def monitor_k3sysui(self):
        pid = shell("ps | grep K3SysUi | grep -v grep | awk '{print $1}'")
        pid = int(pid)

        logging.info(f'Monitoring K3SysUi (PID: {pid})')

        while True:
            time.sleep(5)

            try:
                os.kill(pid, 0)
            except OSError:
                logging.info('K3SysUi is gone, exiting...')
                self.quit()
    def monitor_mqtt(self):
        def mqtt_on_connect(client, userdata, flags, reason_code, properties):
            client.subscribe(f'anycubic/anycubicCloud/v1/+/printer/{KOBRA_MODEL_ID}/{KOBRA_DEVICE_ID}/print')
            logging.info('Monitoring MQTT...')
        def mqtt_on_connect_fail(client, userdata):
            logging.info('MQTT connection failed')
        def mqtt_on_log(client, userdata, level, buf):
            logging.debug(buf)
        def mqtt_on_message(client, userdata, msg):
            logging.info('Received print event, exiting...')
            self.quit()

        with open('/userdata/app/gk/config/device_account.json', 'r') as f:
            json_data = f.read()
            data = json.loads(json_data)

            mqtt_username = data['username']
            mqtt_password = data['password']

        client = paho.Client(protocol = paho.MQTTv5)
        client.on_connect = mqtt_on_connect
        client.on_connect_fail = mqtt_on_connect_fail
        client.on_message = mqtt_on_message
        client.on_log = mqtt_on_log

        client.username_pw_set(mqtt_username, mqtt_password)
        client.connect('127.0.0.1', 2883)
        client.loop_start()

    def layout(self):

        self.screen_container = lvr.screen()
        self.screen_container.set_style_pad_all(0, lv.STATE_DEFAULT)

        if SCREEN_WIDTH > SCREEN_HEIGHT:
            self.screen_composition = self.screen_container
            self.screen_container = lvr.panel(self.screen_composition)

        self.screen_rinkhals = lvr.panel(self.screen_container)
        if self.screen_rinkhals:
            self.screen_rinkhals.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.screen_rinkhals.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self.screen_rinkhals.set_style_pad_row(-lv.dpx(3), lv.STATE_DEFAULT)

            rinkhals_icon = lvr.image(self.screen_rinkhals)
            rinkhals_icon.set_src(SCRIPT_PATH + '/icon.png')
            lvr.scale_image(rinkhals_icon, lv.dpx(90))

            label_rinkhals = lvr.title(self.screen_rinkhals)
            label_rinkhals.set_text('Rinkhals')
            label_rinkhals.set_style_pad_top(lv.dpx(20), lv.STATE_DEFAULT)
            label_rinkhals.set_style_pad_bottom(lv.dpx(10), lv.STATE_DEFAULT)
            
            self.screen_rinkhals.label_firmware = lvr.subtitle(self.screen_rinkhals)
            self.screen_rinkhals.label_firmware.set_text('Firmware:')

            self.screen_rinkhals.label_version = lvr.subtitle(self.screen_rinkhals)
            self.screen_rinkhals.label_version.set_text('Version:')
            
            self.screen_rinkhals.label_root = lvr.subtitle(self.screen_rinkhals)
            self.screen_rinkhals.label_root.set_text('Root: ?')
            
            self.screen_rinkhals.label_home = lvr.subtitle(self.screen_rinkhals)
            self.screen_rinkhals.label_home.set_text('Home: ?')
            
            self.screen_rinkhals.label_disk = lvr.subtitle(self.screen_rinkhals)
            self.screen_rinkhals.label_disk.set_text('Disk usage: ?')

            button_exit = lvr.button_icon(self.screen_rinkhals)
            button_exit.add_flag(lv.OBJ_FLAG.IGNORE_LAYOUT)
            button_exit.align(lv.ALIGN.TOP_LEFT, -lvr.GLOBAL_PADDING, -lvr.GLOBAL_PADDING)
            button_exit.add_event_cb(lambda e: self.quit(), lv.EVENT_CODE.CLICKED, None)
            button_exit_label = lvr.label(button_exit)
            button_exit_label.center()
            button_exit_label.set_text('')

        self.screen_main = lvr.panel(self.screen_container)
        if self.screen_main:
            self.screen_main.set_size(lv.pct(100), lv.pct(100))
            self.screen_main.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.screen_main.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self.screen_main.set_style_pad_row(lvr.GLOBAL_PADDING, lv.STATE_DEFAULT)

            button_apps = lvr.button(self.screen_main)
            button_apps.set_width(lv.pct(100))
            button_apps.add_event_cb(lambda e: self.show_screen(self.screen_apps), lv.EVENT_CODE.CLICKED, None)
            button_apps_label = lv.label(button_apps)
            button_apps_label.set_text('Manage apps')
            button_apps_label.center()
            
            button_ota = lvr.button(self.screen_main)
            button_ota.set_width(lv.pct(100))
            button_ota.add_event_cb(lambda e: self.layout_ota(), lv.EVENT_CODE.CLICKED, None)
            button_ota_label = lv.label(button_ota)
            button_ota_label.set_text('Check for updates')
            button_ota_label.center()

            button_settings = lvr.button(self.screen_main)
            button_settings.set_width(lv.pct(100))
            button_settings.add_event_cb(lambda e: self.show_screen(self.screen_advanced), lv.EVENT_CODE.CLICKED, None)
            button_settings_label = lv.label(button_settings)
            button_settings_label.set_style_text_color(lvr.COLOR_DANGER, lv.STATE_DEFAULT)
            button_settings_label.set_text('Advanced settings')
            button_settings_label.center()

        self.screen_apps = lvr.panel(self.screen_container)
        if self.screen_apps:
            self.screen_apps.set_size(lv.pct(100), lv.pct(100))
            self.screen_apps.set_style_pad_all(0, lv.STATE_DEFAULT)
            self.screen_apps.set_style_pad_top(lvr.TITLE_BAR_HEIGHT, lv.STATE_DEFAULT)

            title_bar = lvr.title_bar(self.screen_apps)
            title_bar.set_y(-lvr.TITLE_BAR_HEIGHT)
            
            title = lvr.title(title_bar)
            title.set_text('Manage apps')
            title.center()

            icon_back = lvr.button_icon(title_bar)
            icon_back.set_align(lv.ALIGN.LEFT_MID)
            icon_back.add_event_cb(lambda e: self.show_screen(self.screen_main), lv.EVENT_CODE.CLICKED, None)
            icon_back_label = lvr.label(icon_back)
            icon_back_label.center()
            icon_back_label.set_text('')

            icon_refresh = lvr.button_icon(title_bar)
            icon_refresh.add_event_cb(lambda e: self.show_screen(self.screen_apps), lv.EVENT_CODE.CLICKED, None)
            icon_refresh.set_align(lv.ALIGN.RIGHT_MID)
            icon_refresh_label = lvr.label(icon_refresh)
            icon_refresh_label.center()
            icon_refresh_label.set_text('')

            self.screen_apps.panel_apps = None

        self.screen_app = lvr.panel(self.screen_container)
        if self.screen_app:
            self.screen_app.set_size(lv.pct(100), lv.pct(100))
            self.screen_app.set_style_pad_all(0, lv.STATE_DEFAULT)
            self.screen_app.set_style_pad_top(lvr.TITLE_BAR_HEIGHT, lv.STATE_DEFAULT)

            title_bar = lvr.title_bar(self.screen_app)
            title_bar.set_y(-lvr.TITLE_BAR_HEIGHT)
            
            self.screen_app.label_title = lvr.title(title_bar)
            self.screen_app.label_title.center()

            icon_back = lvr.button_icon(title_bar)
            icon_back.set_align(lv.ALIGN.LEFT_MID)
            icon_back.add_event_cb(lambda e: self.show_screen(self.screen_apps), lv.EVENT_CODE.CLICKED, None)
            icon_back_label = lvr.label(icon_back)
            icon_back_label.center()
            icon_back_label.set_text('')

            self.screen_app.button_refresh = lvr.button_icon(title_bar)
            self.screen_app.button_refresh.set_align(lv.ALIGN.RIGHT_MID)
            button_refresh_label = lvr.label(self.screen_app.button_refresh)
            button_refresh_label.center()
            button_refresh_label.set_text('')

            panel_app = lvr.flex_container(self.screen_app, align=lv.FLEX_ALIGN.CENTER)
            panel_app.set_size(lv.pct(100), lv.pct(100))

            self.screen_app.label_version = lvr.subtitle(panel_app)
            self.screen_app.label_version.set_text('Version:')
            self.screen_app.label_version.set_style_margin_ver(-lvr.GLOBAL_PADDING - lv.dpx(2), lv.STATE_DEFAULT)
            
            self.screen_app.label_path = lvr.subtitle(panel_app)
            self.screen_app.label_path.set_style_max_width(lv.pct(100), lv.STATE_DEFAULT)
            
            self.screen_app.label_description = lvr.subtitle(panel_app)
            self.screen_app.label_description.set_style_text_color(lvr.COLOR_TEXT, lv.STATE_DEFAULT)
            self.screen_app.label_description.set_width(lv.pct(100))
            self.screen_app.label_description.set_long_mode(lv.LABEL_LONG_MODE.WRAP)
            self.screen_app.label_description.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE_DEFAULT)

            panel_stats = lvr.panel(panel_app)
            panel_stats.set_width(lv.pct(100))
            panel_stats.set_flex_flow(lv.FLEX_FLOW.ROW)
            panel_stats.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            panel_stats.set_style_pad_column(0, lv.STATE_DEFAULT)
            panel_stats.set_style_pad_hor(0, lv.STATE_DEFAULT)
            panel_stats.set_style_pad_ver(lv.dpx(15), lv.STATE_DEFAULT)

            panel_disk = lvr.flex_container(panel_stats, align=lv.FLEX_ALIGN.CENTER)
            panel_disk.set_style_pad_row(-lv.dpx(2), lv.STATE_DEFAULT)
            panel_disk.set_width(lv.pct(30))
            panel_disk.set_style_pad_all(0, lv.STATE_DEFAULT)

            label_disk_subtitle = lvr.subtitle(panel_disk)
            label_disk_subtitle.set_text('Disk')
            
            self.screen_app.label_disk = lvr.label(panel_disk)
            self.screen_app.label_disk.set_text('?')
            
            panel_memory = lvr.flex_container(panel_stats, align=lv.FLEX_ALIGN.CENTER)
            panel_memory.set_style_pad_row(-lv.dpx(2), lv.STATE_DEFAULT)
            panel_memory.set_width(lv.pct(30))
            panel_memory.set_style_pad_all(0, lv.STATE_DEFAULT)

            label_memory_subtitle = lvr.subtitle(panel_memory)
            label_memory_subtitle.set_text('Memory')
            
            self.screen_app.label_memory = lvr.label(panel_memory)
            self.screen_app.label_memory.set_text('?')
            
            panel_cpu = lvr.flex_container(panel_stats, align=lv.FLEX_ALIGN.CENTER)
            panel_cpu.set_style_pad_row(-lv.dpx(2), lv.STATE_DEFAULT)
            panel_cpu.set_width(lv.pct(30))
            panel_cpu.set_style_pad_all(0, lv.STATE_DEFAULT)

            label_cpu_subtitle = lvr.subtitle(panel_cpu)
            label_cpu_subtitle.set_text('CPU')
            
            self.screen_app.label_cpu = lvr.label(panel_cpu)
            self.screen_app.label_cpu.set_text('?')
            
            panel_actions = lvr.panel(panel_app)
            panel_actions.set_height(lv.SIZE_CONTENT)
            panel_actions.set_width(lv.pct(100))
            panel_actions.set_flex_flow(lv.FLEX_FLOW.ROW_REVERSE)
            panel_actions.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            panel_actions.set_style_pad_column(lvr.GLOBAL_PADDING, lv.STATE_DEFAULT)
            panel_actions.set_style_pad_all(0, lv.STATE_DEFAULT)
            
            self.screen_app.button_qrcode = lvr.button_icon(panel_actions)
            self.screen_app.button_qrcode.add_style(lvr.style_button, lv.STATE_DEFAULT)
            self.screen_app.button_qrcode_label = lv.label(self.screen_app.button_qrcode)
            self.screen_app.button_qrcode_label.set_text('')
            self.screen_app.button_qrcode_label.center()
            
            self.screen_app.button_settings = lvr.button_icon(panel_actions)
            self.screen_app.button_settings.add_style(lvr.style_button, lv.STATE_DEFAULT)
            self.screen_app.button_settings_label = lv.label(self.screen_app.button_settings)
            self.screen_app.button_settings_label.set_text('')
            self.screen_app.button_settings_label.center()

            self.screen_app.button_toggle_enabled = lvr.button(panel_actions)
            self.screen_app.button_toggle_enabled.set_flex_grow(1)
            self.screen_app.button_toggle_enabled_label = lv.label(self.screen_app.button_toggle_enabled)
            self.screen_app.button_toggle_enabled_label.set_text('Enable/Disable app')
            self.screen_app.button_toggle_enabled_label.center()
            
            self.screen_app.button_toggle_started = lvr.button(panel_app)
            self.screen_app.button_toggle_started.set_width(lv.pct(100))
            self.screen_app.button_toggle_started_label = lv.label(self.screen_app.button_toggle_started)
            self.screen_app.button_toggle_started_label.set_text('Start/Stop app')
            self.screen_app.button_toggle_started_label.center()

        self.screen_advanced = lvr.panel(self.screen_container)
        if self.screen_advanced:
            self.screen_advanced.set_size(lv.pct(100), lv.pct(100))
            self.screen_advanced.set_style_pad_top(lvr.TITLE_BAR_HEIGHT + lvr.GLOBAL_PADDING, lv.STATE_DEFAULT)
            self.screen_advanced.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.screen_advanced.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            
            title_bar = lvr.title_bar(self.screen_advanced)
            title_bar.add_flag(lv.OBJ_FLAG.IGNORE_LAYOUT)
            title_bar.set_y(-lvr.TITLE_BAR_HEIGHT - lvr.GLOBAL_PADDING)
            
            title = lvr.title(title_bar)
            title.set_text('Advanced settings')
            title.center()

            icon_back = lvr.button_icon(title_bar)
            icon_back.set_align(lv.ALIGN.LEFT_MID)
            icon_back.add_event_cb(lambda e: self.show_screen(self.screen_main), lv.EVENT_CODE.CLICKED, None)
            icon_back_label = lvr.label(icon_back)
            icon_back_label.center()
            icon_back_label.set_text('')
            
            button_reboot = lvr.button(self.screen_advanced)
            button_reboot.set_width(lv.pct(100))
            button_reboot.add_event_cb(lambda e: self.show_text_dialog('Are you sure you want\nto reboot your printer?', action='Yes', callback=lambda: self.reboot_printer()), lv.EVENT_CODE.CLICKED, None)
            button_reboot_label = lv.label(button_reboot)
            button_reboot_label.set_text('Reboot printer')
            button_reboot_label.center()
            
            button_restart = lvr.button(self.screen_advanced)
            button_restart.set_width(lv.pct(100))
            button_restart.add_event_cb(lambda e: self.show_text_dialog('Are you sure you want\nto restart Rinkhals?', action='Yes', callback=lambda: self.restart_rinkhals()), lv.EVENT_CODE.CLICKED, None)
            button_restart_label = lv.label(button_restart)
            button_restart_label.set_text('Restart Rinkhals')
            button_restart_label.center()
            
            button_stock = lvr.button(self.screen_advanced)
            button_stock.set_width(lv.pct(100))
            button_stock.add_event_cb(lambda e: self.show_text_dialog('Are you sure you want\nto switch to stock firmware?\n\nYou can reboot your printer\nto start Rinkhals again', action='Yes', callback=lambda: self.stop_rinkhals()), lv.EVENT_CODE.CLICKED, None)
            button_stock_label = lv.label(button_stock)
            button_stock_label.set_text('Switch to stock')
            button_stock_label.center()

            button_disable = lvr.button(self.screen_advanced)
            button_disable.set_width(lv.pct(100))
            button_disable.set_style_text_color(lvr.COLOR_DANGER, lv.STATE_DEFAULT)
            button_disable.add_event_cb(lambda e: self.show_text_dialog('Are you sure you want\nto disable Rinkhals?\n\nYou will need to reinstall\nRinkhals to start it again', action='Yes', action_color=lvr.COLOR_DANGER, callback=lambda: self.disable_rinkhals()), lv.EVENT_CODE.CLICKED, None)
            button_disable_label = lv.label(button_disable)
            button_disable_label.set_text('Disable Rinkhals')
            button_disable_label.center()

        self.layer_ota = lvr.panel(lv.layer_top())
        if self.layer_ota:
            self.layer_ota.set_size(lv.pct(100), lv.pct(100))
            self.layer_ota.set_style_bg_color(lv.color_black(), lv.STATE_DEFAULT)
            self.layer_ota.set_style_bg_opa(160, lv.STATE_DEFAULT)
            self.layer_ota.add_flag(lv.OBJ_FLAG.HIDDEN)

            layer_ota = lvr.panel(self.layer_ota)
            layer_ota.set_width(lv.dpx(320))
            layer_ota.set_style_radius(8, lv.STATE_DEFAULT)
            layer_ota.set_style_pad_all(lv.dpx(20), lv.STATE_DEFAULT)
            layer_ota.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            layer_ota.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            layer_ota.center()

            label_title = lvr.title(layer_ota)
            label_title.set_text('Check for updates')
            label_title.set_style_pad_bottom(lv.dpx(10), lv.STATE_DEFAULT)

            label_rinkhals = lvr.label(layer_ota)
            label_rinkhals.set_style_text_color(lvr.COLOR_TEXT, lv.STATE_DEFAULT)
            label_rinkhals.set_text('Rinkhals')
            label_rinkhals.set_style_margin_bottom(-lv.dpx(20), lv.STATE_DEFAULT)

            panel_rinkhals = lvr.panel(layer_ota)
            panel_rinkhals.set_width(lv.pct(100))
            panel_rinkhals.set_flex_flow(lv.FLEX_FLOW.ROW)
            panel_rinkhals.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            panel_rinkhals.set_style_pad_column(0, lv.STATE_DEFAULT)
            panel_rinkhals.set_style_bg_opa(lv.OPA_TRANSP, lv.STATE_DEFAULT)

            panel_rinkhals_current = lvr.flex_container(panel_rinkhals, align=lv.FLEX_ALIGN.CENTER)
            panel_rinkhals_current.set_style_pad_row(-lv.dpx(2), lv.STATE_DEFAULT)
            panel_rinkhals_current.set_width(lv.pct(45))
            panel_rinkhals_current.set_style_pad_all(0, lv.STATE_DEFAULT)

            label_rinkhals_current = lvr.subtitle(panel_rinkhals_current)
            label_rinkhals_current.set_text('Current')
            
            self.layer_ota.label_rinkhals_current = lvr.label(panel_rinkhals_current)
            self.layer_ota.label_rinkhals_current.set_text('?')

            panel_rinkhals_latest = lvr.flex_container(panel_rinkhals, align=lv.FLEX_ALIGN.CENTER)
            panel_rinkhals_latest.set_style_pad_row(-lv.dpx(2), lv.STATE_DEFAULT)
            panel_rinkhals_latest.set_width(lv.pct(45))
            panel_rinkhals_latest.set_style_pad_all(0, lv.STATE_DEFAULT)

            label_rinkhals_latest = lvr.subtitle(panel_rinkhals_latest)
            label_rinkhals_latest.set_text('Latest')
            
            self.layer_ota.label_rinkhals_latest = lvr.label(panel_rinkhals_latest)
            self.layer_ota.label_rinkhals_latest.set_text('?')

            self.layer_ota.panel_progress = lvr.flex_container(layer_ota, align=lv.FLEX_ALIGN.CENTER)
            self.layer_ota.panel_progress.set_width(lv.pct(100))
            self.layer_ota.panel_progress.set_style_pad_row(lv.dpx(2), lv.STATE_DEFAULT)

            panel_progress_background = lvr.panel(self.layer_ota.panel_progress)
            panel_progress_background.set_size(lv.pct(100), lv.dpx(10))
            panel_progress_background.set_style_pad_all(0, lv.STATE_DEFAULT)
            panel_progress_background.set_style_bg_color(lv.color_lighten(lvr.COLOR_BACKGROUND, 48), lv.STATE_DEFAULT)
            panel_progress_background.remove_flag(lv.OBJ_FLAG.SCROLLABLE)

            self.layer_ota.obj_progress_bar = lvr.panel(panel_progress_background)
            self.layer_ota.obj_progress_bar.set_align(lv.ALIGN.LEFT_MID)
            self.layer_ota.obj_progress_bar.set_style_bg_color(lvr.COLOR_PRIMARY, lv.STATE_DEFAULT)
            self.layer_ota.obj_progress_bar.set_size(lv.pct(24), lv.pct(100))

            self.layer_ota.label_progress_text = lvr.label(self.layer_ota.panel_progress)
            self.layer_ota.label_progress_text.set_text('Ready')

            panel_actions = lvr.panel(layer_ota)
            panel_actions.set_width(lv.pct(100))
            panel_actions.set_flex_flow(lv.FLEX_FLOW.ROW)
            panel_actions.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            panel_actions.set_style_pad_column(lv.dpx(15), lv.STATE_DEFAULT)
            panel_actions.set_style_pad_all(0, lv.STATE_DEFAULT)

            self.layer_ota.button_cancel = lvr.button(panel_actions)
            self.layer_ota.button_cancel.set_width(lv.pct(45))
            self.layer_ota.button_cancel_label = lvr.label(self.layer_ota.button_cancel)
            self.layer_ota.button_cancel_label.set_text('Cancel')
            self.layer_ota.button_cancel_label.center()
            
            self.layer_ota.button_action = lvr.button(panel_actions)
            self.layer_ota.button_action.set_width(lv.pct(45))
            self.layer_ota.button_action_label = lvr.label(self.layer_ota.button_action)
            self.layer_ota.button_action_label.set_text('Download')
            self.layer_ota.button_action_label.center()

        self.layer_dialog = lvr.panel(lv.layer_top())
        if self.layer_dialog:
            self.layer_dialog.set_size(lv.pct(100), lv.pct(100))
            self.layer_dialog.set_style_bg_color(lv.color_black(), lv.STATE_DEFAULT)
            self.layer_dialog.set_style_bg_opa(160, lv.STATE_DEFAULT)
            self.layer_dialog.add_flag(lv.OBJ_FLAG.HIDDEN)

            panel_dialog = lvr.panel(self.layer_dialog)
            panel_dialog.set_width(lv.dpx(320))
            panel_dialog.set_style_radius(8, lv.STATE_DEFAULT)
            panel_dialog.set_style_pad_all(lv.dpx(20), lv.STATE_DEFAULT)
            panel_dialog.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            panel_dialog.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            panel_dialog.center()
            
            self.layer_dialog.message = lvr.label(panel_dialog)
            self.layer_dialog.message.set_style_pad_bottom(lv.dpx(15), lv.STATE_DEFAULT)
            self.layer_dialog.message.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE_DEFAULT)
            self.layer_dialog.message.set_text('Hello World!')

            self.layer_dialog.qrcode = lv.qrcode(panel_dialog)
            self.layer_dialog.qrcode.set_size(lv.dpx(224))
            self.layer_dialog.qrcode.update('https://github.com/jbatonnet/Rinkhals')

            self.layer_dialog.button_action = lvr.button(panel_dialog)
            self.layer_dialog.button_action.set_style_min_width(lv.dpx(160), lv.STATE_DEFAULT)
            self.layer_dialog.button_action_label = lvr.label(self.layer_dialog.button_action)
            self.layer_dialog.button_action_label.set_text('Action')
            self.layer_dialog.button_action_label.center()

            def action_callback(e):
                self.layer_dialog.add_flag(lv.OBJ_FLAG.HIDDEN)

                if self.layer_dialog.callback_action:
                    self.layer_dialog.callback_action()

            self.layer_dialog.button_action.add_event_cb(action_callback, lv.EVENT_CODE.CLICKED, None)
            self.layer_dialog.add_event_cb(lambda e: self.layer_dialog.add_flag(lv.OBJ_FLAG.HIDDEN), lv.EVENT_CODE.CLICKED, None)

        if SCREEN_WIDTH > SCREEN_HEIGHT:
            self.screen_rinkhals.set_parent(self.screen_composition)
            self.screen_rinkhals.set_align(lv.ALIGN.LEFT_MID)
            self.screen_rinkhals.set_width(lv.pct(50))
            self.screen_rinkhals.set_height(lv.pct(100))

            self.screen_container.set_style_bg_color(lv.color_make(64, 0, 0), lv.STATE_DEFAULT)
            self.screen_container.set_style_pad_all(0, lv.STATE_DEFAULT)
            self.screen_container.set_align(lv.ALIGN.RIGHT_MID)
            self.screen_container.set_width(lv.pct(50))
            self.screen_container.set_height(lv.pct(100))

            lv.screen_load(self.screen_composition)
        else:
            self.screen_rinkhals.set_align(lv.ALIGN.TOP_MID)
            self.screen_rinkhals.set_width(lv.pct(100))
            self.screen_rinkhals.set_height(lv.pct(50))

            self.screen_main.set_align(lv.ALIGN.BOTTOM_MID)
            self.screen_main.set_width(lv.pct(100))
            self.screen_main.set_height(lv.pct(50))
            
            screen_composition = lvr.panel(self.screen_container)
            screen_composition.set_style_pad_all(0, lv.STATE_DEFAULT)
            screen_composition.set_size(lv.pct(100), lv.pct(100))

            self.screen_rinkhals.set_parent(screen_composition)
            self.screen_main.set_parent(screen_composition)

            self.screen_main = screen_composition
            lv.screen_load(self.screen_container)

        self.show_screen(self.screen_main)

    def show_screen(self, screen):
        screen.move_foreground()

        if screen == self.screen_main: self.layout_main()
        if screen == self.screen_apps: self.layout_apps()
    def show_app(self, app):
        self.show_screen(self.screen_app)
        self.layout_app(app)

    def layout_main(self):
        self.screen_rinkhals.label_firmware.set_text(f'Firmware: {KOBRA_VERSION}')
        self.screen_rinkhals.label_version.set_text(f'Version: {RINKHALS_VERSION}')
        self.screen_rinkhals.label_root.set_text(f'Root: {ellipsis(RINKHALS_ROOT, 32)}')
        self.screen_rinkhals.label_home.set_text(f'Home: {ellipsis(RINKHALS_HOME, 32)}')
        self.screen_rinkhals.label_disk.set_text(f'Disk usage: ?')

        def update_disk_usage(result):
            lv.lock()
            self.screen_rinkhals.label_disk.set_text(f'Disk usage: {result}')
            lv.unlock()

        if USING_SHELL:
            shell_async(f'df -Ph {RINKHALS_ROOT} | tail -n 1 | awk \'{{print $3 " / " $2 " (" $5 ")"}}\'', update_disk_usage)
    def layout_apps(self):
        def toggle_app(app, checked):
            if checked:
                logging.info(f'Enabling {app}...')
                enable_app(app)
                if get_app_status(app) != 'started':
                    logging.info(f'Starting {app}...')
                    start_app(app, 5)
            else:
                logging.info(f'Disabling {app}...')
                disable_app(app)
                if get_app_status(app) == 'started':
                    logging.info(f'Stopping {app}...')
                    stop_app(app)

            self.app_checkboxes[app].set_checked(is_app_enabled(app) == '1')
            
        if self.screen_apps.panel_apps:
            self.screen_apps.panel_apps.delete()
        self.screen_apps.panel_apps = lvr.flex_container(self.screen_apps)
        self.screen_apps.panel_apps.set_size(lv.pct(100), lv.pct(100))

        self.app_checkboxes = {}

        apps = list_apps().split(' ')
        apps_enabled = are_apps_enabled()

        for app in apps:
            enabled = apps_enabled[app] == '1'

            button_app = lvr.button(self.screen_apps.panel_apps)
            button_app.set_width(lv.pct(100))
            button_app.set_style_pad_left(lv.dpx(15), lv.STATE_DEFAULT)
            button_app.set_style_pad_right(lv.dpx(4), lv.STATE_DEFAULT)
            button_app.add_event_cb(lambda e, app=app: self.show_app(app), lv.EVENT_CODE.CLICKED, None)
            button_app_label = lvr.label(button_app)
            button_app_label.set_align(lv.ALIGN.LEFT_MID)
            button_app_label.set_text(app)

            checkbox_app = lvr.checkbox(button_app)
            checkbox_app.set_align(lv.ALIGN.RIGHT_MID)
            checkbox_app.add_event_cb(lambda e, app=app, enabled=enabled: toggle_app(app, not enabled), lv.EVENT_CODE.CLICKED, None)
            checkbox_app.set_checked(enabled)

            self.app_checkboxes[app] = checkbox_app
    def layout_app(self, app):
        if isinstance(app, lv.event):
            app = app.get_user_data()

        app_root = get_app_root(app)
        if not os.path.exists(f'{app_root}/app.sh'):
            self.panel_screen.components = [ self.panel_apps ]
            self.layout_apps()
            self.screen.layout()

        app_manifest = None
        if os.path.exists(f'{app_root}/app.json'):
            try:
                with open(f'{app_root}/app.json', 'r') as f:
                    app_manifest = json.loads(f.read(), cls = JSONWithCommentsDecoder)
            except Exception as e:
                pass

        app_name = app_manifest.get('name') if app_manifest else app
        app_description = app_manifest.get('description') if app_manifest else ''
        app_version = app_manifest.get('version') if app_manifest else ''
        app_status = get_app_status(app)
        app_properties = app_manifest.get('properties', []) if app_manifest else []

        app_enabled = is_app_enabled(app) == '1'
        app_started = app_status != 'stopped'

        self.screen_app.label_title.set_text(ellipsis(app_name, 24))
        self.screen_app.label_version.set_text(f'Version: {app_version}')
        self.screen_app.label_path.set_text(ellipsis(app_root, 36))
        self.screen_app.label_description.set_text(app_description)
        self.screen_app.label_disk.set_text('-')
        self.screen_app.label_memory.set_text('-')
        self.screen_app.label_cpu.set_text('-')
        
        self.screen_app.button_toggle_enabled_label.set_text('Disable app' if app_enabled else 'Enable app')
        self.screen_app.button_toggle_enabled.remove_event_cb(self.enable_app)
        self.screen_app.button_toggle_enabled.remove_event_cb(self.disable_app)
        self.screen_app.button_toggle_enabled.add_event_cb(self.disable_app if app_enabled else self.enable_app, lv.EVENT_CODE.CLICKED, app)
        
        self.screen_app.button_toggle_started_label.set_text('Stop app' if app_started else 'Start app')
        self.screen_app.button_toggle_started_label.set_style_text_color(lvr.COLOR_DANGER if app_started else lvr.COLOR_TEXT, lv.STATE_DEFAULT)
        self.screen_app.button_toggle_started.remove_event_cb(self.start_app)
        self.screen_app.button_toggle_started.remove_event_cb(self.stop_app)
        self.screen_app.button_toggle_started.add_event_cb(self.stop_app if app_started else self.start_app, lv.EVENT_CODE.CLICKED, app)
        
        self.screen_app.button_refresh.remove_event_cb(self.show_app)
        self.screen_app.button_refresh.add_event_cb(self.show_app, lv.EVENT_CODE.CLICKED, app)

        if True:
            self.screen_app.button_settings.add_flag(lv.OBJ_FLAG.HIDDEN)

        self.screen_app.button_qrcode.add_flag(lv.OBJ_FLAG.HIDDEN)

        qr_properties = [ p for p in app_properties if app_properties[p]['type'] == 'qr' ]
        if qr_properties:
             qr_property = qr_properties[0]
             display = app_properties[qr_property].get('display')
             content = get_app_property(app, qr_property)
             if content:
                self.screen_app.button_qrcode.remove_flag(lv.OBJ_FLAG.HIDDEN)
                #self.panel_app.app_qr_code.callback = lambda content=content: self.show_qr_dialog(content, display)

        def update_app_size(result):
            lv.lock()
            self.screen_app.label_disk.set_text(result)
            lv.unlock()
        if USING_SHELL:
            shell_async(f"du -sh {app_root} | awk '{{print $1}}'", update_app_size)
            
        def update_memory():
            app_pids = get_app_pids(app)
            if not app_pids:
                return
            
            app_pids = app_pids.split(' ')
            app_memory = 0
            app_cpu = 0

            for pid in app_pids:
                p = psutil.Process(int(pid))
                app_memory += p.memory_info().rss / 1024 / 1024

            lv.lock()
            self.screen_app.label_memory.set_text(f'{round(app_memory, 1)}M')
            lv.unlock()

            for pid in app_pids:
                p = psutil.Process(int(pid))
                app_cpu += p.cpu_percent(interval=1)

            lv.lock()
            self.screen_app.label_cpu.set_text(f'{round(app_cpu, 1)}%')
            lv.unlock()
        run_async(update_memory)
    def layout_ota(self):
        def cancel_ota(e):
            if not USING_SIMULATOR:
                if os.path.exists('/useremain/update.swu'):
                    os.remove('/useremain/update.swu')

            self.layer_ota.add_flag(lv.OBJ_FLAG.HIDDEN)

        self.layer_ota.label_rinkhals_latest.set_text('-')
        self.layer_ota.panel_progress.add_flag(lv.OBJ_FLAG.HIDDEN)
        self.layer_ota.button_action_label.set_text('Refresh')
        self.layer_ota.button_action.set_state(lv.STATE_DISABLED, False)
        self.layer_ota.button_cancel.set_state(lv.STATE_DISABLED, False)
        self.layer_ota.button_action.clear_event_cb()
        self.layer_ota.button_action.add_event_cb(lambda e: run_async(check_rinkhals_update), lv.EVENT_CODE.CLICKED, None)
        self.layer_ota.button_cancel.clear_event_cb()
        self.layer_ota.button_cancel.add_event_cb(cancel_ota, lv.EVENT_CODE.CLICKED, None)

        self.layer_ota.remove_flag(lv.OBJ_FLAG.HIDDEN)

        def install_rinkhals_update():
            lv.lock()
            self.layer_ota.button_action.set_state(lv.STATE_DISABLED, True)
            self.layer_ota.button_cancel.set_state(lv.STATE_DISABLED, True)
            self.layer_ota.label_progress_text.set_text('Extracting...')
            lv.unlock()

            if KOBRA_MODEL_CODE == 'K2P' or KOBRA_MODEL_CODE == 'K3':
                password = 'U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w='
            elif KOBRA_MODEL_CODE == 'KS1':
                password = 'U2FsdGVkX1+lG6cHmshPLI/LaQr9cZCjA8HZt6Y8qmbB7riY'

            logging.info(f'Extracting Rinkhals update...')

            for i in range(1):
                if not USING_SIMULATOR:
                    if os.system('rm -rf /useremain/update_swu') != 0:
                        break
                    if os.system(f'unzip -P {password} /useremain/update.swu -d /useremain') != 0:
                        break
                    if os.system('rm /useremain/update.swu') != 0:
                        break
                    if os.system('tar zxf /useremain/update_swu/setup.tar.gz -C /useremain/update_swu') != 0:
                        break
                    if os.system('chmod +x /useremain/update_swu/update.sh') != 0:
                        break
                else:
                    time.sleep(1)

                lv.lock()
                self.layer_ota.label_progress_text.set_text('Installing...')
                lv.unlock()

                # TODO: Replace reboot by something we control (like start.sh maybe?)

                if not USING_SIMULATOR:
                    logging.info('Starting Rinkhals update...')
                    os.system('/useremain/update_swu/update.sh &')
                else:
                    time.sleep(1)
                    self.quit()
                return
            
            lv.lock()
            self.layer_ota.obj_progress_bar.set_style_bg_color(lvr.COLOR_DANGER, lv.STATE_DEFAULT)
            self.layer_ota.label_progress_text.set_text('Extraction failed')
            self.layer_ota.button_action.set_state(lv.STATE_DISABLED, False)
            self.layer_ota.button_cancel.set_state(lv.STATE_DISABLED, False)
            lv.unlock()

        def download_rinkhals_update():
            lv.lock()
            self.layer_ota.button_action.set_state(lv.STATE_DISABLED, True)
            self.layer_ota.panel_progress.remove_flag(lv.OBJ_FLAG.HIDDEN)
            self.layer_ota.obj_progress_bar.set_style_bg_color(lvr.COLOR_PRIMARY, lv.STATE_DEFAULT)
            self.layer_ota.obj_progress_bar.set_width(lv.pct(0))
            self.layer_ota.label_progress_text.set_text('Starting...')
            lv.unlock()

            target_path = f'{RINKHALS_ROOT}/../../build/dist/update-download.swu' if USING_SIMULATOR else '/useremain/update.swu'

            try:
                logging.info(f'Downloading Rinkhals {self.layer_ota.latest_version} from {self.layer_ota.latest_release_url}...')

                with requests.get(self.layer_ota.latest_release_url, stream=True) as r:
                    r.raise_for_status()
                    with open(target_path, 'wb') as f:
                        total_length = int(r.headers.get('content-length', 0))
                        downloaded = 0
                        last_update_time = 0

                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                if self.layer_ota.has_flag(lv.OBJ_FLAG.HIDDEN):
                                    logging.info('Download canceled.')
                                    return
                                
                                f.write(chunk)
                                downloaded += len(chunk)

                                current_time = time.time()
                                if current_time - last_update_time >= 0.75:
                                    last_update_time = current_time

                                    progress = int(downloaded / total_length * 100)
                                    downloaded_mb = downloaded / (1024 * 1024)
                                    total_mb = total_length / (1024 * 1024)

                                    lv.lock()
                                    self.layer_ota.obj_progress_bar.set_width(lv.pct(progress))
                                    self.layer_ota.label_progress_text.set_text(f'{progress}% ({downloaded_mb:.1f}M / {total_mb:.1f}M)')
                                    lv.unlock()

                logging.info('Download completed.')

                lv.lock()
                self.layer_ota.obj_progress_bar.set_width(lv.pct(100))
                self.layer_ota.label_progress_text.set_text('Ready to install')
                self.layer_ota.button_action_label.set_text('Install')
                self.layer_ota.button_action.clear_event_cb()
                self.layer_ota.button_action.add_event_cb(lambda e: run_async(install_rinkhals_update), lv.EVENT_CODE.CLICKED, None)
                lv.unlock()
            except Exception as e:
                logging.info(f'Download failed. {e}')

                lv.lock()
                self.layer_ota.obj_progress_bar.set_style_bg_color(lvr.COLOR_DANGER, lv.STATE_DEFAULT)
                self.layer_ota.label_progress_text.set_text('Failed')
                lv.unlock()
                
            lv.lock()
            self.layer_ota.button_action.set_state(lv.STATE_DISABLED, False)
            lv.unlock()

        def check_rinkhals_update():
            self.layer_ota.latest_release = None
            self.layer_ota.latest_version = None
            self.layer_ota.latest_release_url = None
            
            try:
                logging.info('Checking latest Rinkhals update...')
                response = requests.get('https://api.github.com/repos/jbatonnet/Rinkhals/releases/latest')

                if response.status_code == 200:
                    self.layer_ota.latest_release = response.json()
                    self.layer_ota.latest_version = self.layer_ota.latest_release.get('tag_name')

                    assets = self.layer_ota.latest_release.get('assets', [])
                    for asset in assets:
                        if (KOBRA_MODEL_CODE == 'K2P' or KOBRA_MODEL_CODE == 'K3') and asset['name'] == 'update-k2p-k3.swu':
                            self.layer_ota.latest_release_url = asset['browser_download_url']
                        elif KOBRA_MODEL_CODE == 'KS1' and asset['name'] == 'update-ks1.swu':
                            self.layer_ota.latest_release_url = asset['browser_download_url']

                    logging.info(f'Found update {self.layer_ota.latest_version} from {self.layer_ota.latest_release_url}')
                else:
                    logging.error(f'Failed to fetch latest release: {response.status_code}')
            except Exception as e:
                logging.error(f'Error checking Rinkhals update: {e}')

            lv.lock()
            if self.layer_ota.latest_version and self.layer_ota.latest_release_url:
                self.layer_ota.label_rinkhals_latest.set_text(ellipsis(self.layer_ota.latest_version, 16))
                self.layer_ota.button_action_label.set_text('Download' if self.layer_ota.latest_version != RINKHALS_VERSION else 'Refresh')
                
                lvr.obj_clear_event_cb(self.layer_ota.button_action)
                self.layer_ota.button_action.add_event_cb(lambda e: run_async(download_rinkhals_update) if self.layer_ota.latest_version != RINKHALS_VERSION else lambda e: run_async(check_rinkhals_update), lv.EVENT_CODE.CLICKED, None)
            else:
                self.layer_ota.label_rinkhals_latest.set_text('-')
                self.layer_ota.button_action_label.set_text('Refresh')
                
                lvr.obj_clear_event_cb(self.layer_ota.button_action)
                self.layer_ota.button_action.add_event_cb(lambda: run_async(check_rinkhals_update), lv.EVENT_CODE.CLICKED, None)
            lv.unlock()

        run_async(check_rinkhals_update)

    def show_text_dialog(self, text, action='OK', action_color=None, callback=None):
        self.layer_dialog.callback_action = callback

        self.layer_dialog.message.set_text(text)
        self.layer_dialog.message.remove_flag(lv.OBJ_FLAG.HIDDEN)
        self.layer_dialog.qrcode.add_flag(lv.OBJ_FLAG.HIDDEN)
        self.layer_dialog.button_action_label.set_text(action)
        self.layer_dialog.button_action_label.set_style_text_color(action_color if action_color else lvr.COLOR_TEXT, lv.STATE_DEFAULT)

        self.layer_dialog.remove_flag(lv.OBJ_FLAG.HIDDEN)
    def show_qr_dialog(self, content, text=None):
        if text:
            self.layer_dialog.message.set_text(text)
            self.layer_dialog.message.remove_flag(lv.OBJ_FLAG.HIDDEN)
        else:
            self.layer_dialog.message.add_flag(lv.OBJ_FLAG.HIDDEN)
        self.layer_dialog.qrcode.remove_flag(lv.OBJ_FLAG.HIDDEN)
        self.layer_dialog.qrcode.update(content)
        self.layer_dialog.button_action_label.set_text('OK')
        self.layer_dialog.button_action_label.set_style_text_color(lvr.COLOR_TEXT, lv.STATE_DEFAULT)

        self.layer_dialog.remove_flag(lv.OBJ_FLAG.HIDDEN)

    def enable_app(self, app):
        if isinstance(app, lv.event):
            app = app.get_user_data()
        logging.info(f'Enabling {app}...')
        enable_app(app)
        self.layout_app(app)
    def disable_app(self, app):
        if isinstance(app, lv.event):
            app = app.get_user_data()
        logging.info(f'Disabling {app}...')
        disable_app(app)
        self.layout_app(app)
    def start_app(self, app):
        if isinstance(app, lv.event):
            app = app.get_user_data()
        logging.info(f'Starting {app}...')
        start_app(app, 5)
        self.layout_app(app)
    def stop_app(self, app):
        if isinstance(app, lv.event):
            app = app.get_user_data()
        logging.info(f'Stopping {app}...')
        stop_app(app)
        self.layout_app(app)

    def reboot_printer(self, e=None):
        logging.info('Rebooting printer...')

        if not USING_SIMULATOR:
            self.clear()
            os.system('sync && reboot')
        else:
            self.quit()
    def restart_rinkhals(self, e=None):
        logging.info('Restarting Rinkhals...')

        if not USING_SIMULATOR:
            self.clear()
            os.system(RINKHALS_ROOT + '/start.sh')

        self.quit()
    def stop_rinkhals(self, e=None):
        logging.info('Stopping Rinkhals...')

        if not USING_SIMULATOR:
            self.clear()
            os.system(RINKHALS_ROOT + '/stop.sh')

        self.quit()
    def disable_rinkhals(self, e=None):
        logging.info('Disabling Rinkhals...')

        if not USING_SIMULATOR:
            self.clear()
            with open('/useremain/rinkhals/.disable-rinkhals', 'wb'):
                pass
            os.system('reboot')

        self.quit()

    def clear(self):
        if not USING_SIMULATOR:
            os.system(f'dd if=/dev/zero of=/dev/fb0 bs={self.screen.width * 4} count={self.screen.height}')
    def run(self):
        while True:
            lv.tick_inc(16)
            lv.timer_handler()
            time.sleep(0.016)
    def quit(self):
        logging.info('Exiting Rinkhals UI...')
        time.sleep(0.25)
        os.kill(os.getpid(), 9)


if __name__ == "__main__":
    if USING_SIMULATOR:
        program = Program()
        program.run()
    else:
        try:
            program = Program()
            program.run()
        except:
            frames = sys._current_frames()
            threads = {}
            for thread in threading.enumerate():
                threads[thread.ident] = thread
            for thread_id, stack in frames.items():
                if thread_id == threading.main_thread().ident:
                    print(traceback.format_exc())
                elif thread_id in threads:
                    print(f'-- Thread {thread_id}: {threads[thread_id]} --')
                    print(' '.join(traceback.format_list(traceback.extract_stack(stack))))
            
    print('', flush=True)
    os.kill(os.getpid(), 9)
