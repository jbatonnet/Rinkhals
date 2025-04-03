import os
import time
import sys
import json
import re
import subprocess
import threading
import platform
import traceback
import logging
import psutil

import paho.mqtt.client as paho
from gui import *


class JSONWithCommentsDecoder(json.JSONDecoder):
    def __init__(self, **kwgs):
        super().__init__(**kwgs)
    def decode(self, s: str):
        regex = r"""("(?:\\"|[^"])*?")|(\/\*(?:.|\s)*?\*\/|\/\/.*)"""
        s = re.sub(regex, r"\1", s)  # , flags = re.X | re.M)
        return super().decode(s)

def wrap(txt, width):
    tmp = ""
    for i in txt.split():
        if len(tmp) + len(i) < width:
            tmp += " " + i
        else:
            yield tmp.strip()
            tmp = i
    if tmp:
        yield tmp.strip()
def shell(command):
    result = subprocess.check_output(['sh', '-c', command])
    result = result.decode('utf-8').strip()
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
def ellipsis(text, length):
    if len(text) > length:
        text = text[:int(length / 2)] + '...' + text[-int(length / 2):]
    return text
def cache(getter, key = None):
    key = key or ''
    key = f'line:{sys._getframe().f_back.f_lineno}|{key}'
    item = Cache.get(key)
    if item is None:
        item = getter()
        Cache.set(key, item)
    return item


DEBUG = os.getenv('DEBUG')
DEBUG = not not DEBUG
#DEBUG = True

# Setup logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Detect Rinkhals root
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
RINKHALS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_PATH)))

USING_SHELL = True
if platform.system() == 'Windows':
    if os.system('sh -c "echo"') != 0:
        USING_SHELL = False
    else:
        RINKHALS_ROOT = RINKHALS_ROOT.replace('\\', '/')
    if os.system('sh -c "ls /mnt/c"') == 0:
        RINKHALS_ROOT = '/mnt/' + RINKHALS_ROOT[0].lower() + RINKHALS_ROOT[2:]

# Detect environment and tools
USING_SIMULATOR = True
if os.path.exists('/dev/fb0'):
    USING_SIMULATOR = False

if USING_SIMULATOR:
    RINKHALS_HOME = f'{RINKHALS_ROOT}/../4-apps/home/rinkhals'
    RINKHALS_VERSION = 'dev'
    KOBRA_MODEL = 'Anycubic Kobra'
    KOBRA_MODEL_CODE = 'KS1'
    #KOBRA_MODEL_CODE = 'K3'
    KOBRA_VERSION = '1.2.3.4'

    if KOBRA_MODEL_CODE == 'KS1':
        QT_QPA_PLATFORM = 'linuxfb:fb=/dev/fb0:size=800x480:rotation=180:offset=0x0:nographicsmodeswitch'
    else:
        QT_QPA_PLATFORM = 'linuxfb:fb=/dev/fb0:size=480x272:rotation=90:offset=0x0:nographicsmodeswitch'

    def list_apps(): return ' '.join([ f.name for f in os.scandir(f'{RINKHALS_HOME}/apps') if f.is_dir() ]) + ' test-1 test-2 test-3 test-4 test-5 test-6 test-7 test-8'
    def get_app_root(app): return f'{RINKHALS_HOME}/apps/{app}'
    def is_app_enabled(app): return '1' if os.path.exists(f'{RINKHALS_HOME}/apps/{app}/.enabled') else '0'
    def get_app_status(app): return 'started' if is_app_enabled(app) == '1' else 'stopped'
    def get_app_pids(app): return str(os.getpid()) if get_app_status(app) == 'started' else ''
    def enable_app(app): pass
    def disable_app(app): pass
    def start_app(app): pass
    def stop_app(app): pass
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

# Styling
FONT_PATH = SCRIPT_PATH + '/AlibabaSans-Regular.ttf'
FONT_TITLE_SIZE = 16
FONT_SUBTITLE_SIZE = 11
FONT_TEXT_SIZE = 14
ICON_FONT_PATH = SCRIPT_PATH + '/MaterialIcons-Regular.ttf'

COLOR_PRIMARY = (0, 128, 255)
COLOR_SECONDARY = (96, 96, 96)
COLOR_TEXT = (255, 255, 255)
COLOR_BACKGROUND = (0, 0, 0)
COLOR_DANGER = (255, 64, 64)
COLOR_SUBTITLE = (160, 160, 160)
COLOR_DISABLED = (176, 176, 176)
COLOR_SHADOW = (96, 96, 96)

def debug(kwargs):
    if DEBUG:
        kwargs['border_color'] = (255, 0, 255)
        kwargs['border_width'] = 1
    return kwargs

def myButton(*args, left=8, right=8, top=8, height=48, font_path=FONT_PATH, font_size=FONT_TEXT_SIZE, background_color=(48, 48, 48), pressed_color=(80, 80, 80), border_color=(96, 96, 96), border_width=1, border_radius=8, text_color=COLOR_TEXT, text_padding=12, **kwargs):
    return Button(*args, left=left, right=right, top=top, height=height, font_path=font_path, font_size=font_size, background_color=background_color, pressed_color=pressed_color, border_color=border_color, border_width=border_width, border_radius=border_radius, text_color=text_color, text_padding=text_padding, **kwargs)
def myStackPanel(*args, background_color=(32, 32, 32), **kwargs):
    return StackPanel(*args, background_color=background_color, **debug(kwargs))
def myScrollPanel(*args, background_color=(32, 32, 32), distance_threshold=32, **kwargs):
    return ScrollPanel(*args, background_color=background_color, distance_threshold=distance_threshold, **debug(kwargs))
def myPanel(*args, background_color=(32, 32, 32), **kwargs):
    return Panel(*args, background_color=background_color, **debug(kwargs))
def myLabel(*args, font_path=FONT_PATH, font_size=FONT_TEXT_SIZE, text_color=COLOR_TEXT, **kwargs):
    return Label(*args, font_path=font_path, font_size=font_size, text_color=text_color, **debug(kwargs))
def myCheckBox(*args, width=40, height=40, font_path=ICON_FONT_PATH, font_size=28, background_color=(48, 48, 48), border_color=(96, 96, 96), border_width=1, border_radius=8, text_color=COLOR_TEXT, check_symbol='', **kwargs):
    return CheckBox(*args, width=width, height=height, font_path=font_path, font_size=font_size, background_color=background_color, border_color=border_color, border_width=border_width, border_radius=border_radius, text_color=text_color, check_symbol=check_symbol, **kwargs)


class Program:
    screen = None

    def __init__(self):
        if USING_SIMULATOR:
            self.screen = SimulatorScreen('Kobra simulator', SCREEN_WIDTH, SCREEN_HEIGHT)
        else:
            self.screen = TouchFramebuffer('/dev/fb0', '/dev/input/event0', rotation=SCREEN_ROTATION, touch_calibration=(TOUCH_CALIBRATION_MIN_X, TOUCH_CALIBRATION_MIN_Y, TOUCH_CALIBRATION_MAX_X, TOUCH_CALIBRATION_MAX_Y))

        if KOBRA_MODEL_CODE == 'KS1':
            self.screen.scale = 1.5

        logging.debug(f'Simulator: {USING_SIMULATOR}')
        logging.debug(f'Root: {RINKHALS_ROOT}')
        logging.debug(f'Home: {RINKHALS_HOME}')

        # Subscribe to print event to exit in case of print
        if not USING_SIMULATOR and REMOTE_MODE == 'lan':
            self.monitor_mqtt()

        # Monitor K3SysUi process to exit if it dies
        if not USING_SIMULATOR:
            monitor_thread = threading.Thread(target = self.monitor_k3sysui)
            monitor_thread.start()

        # Layout and draw
        self.layout()
        self.screen.draw()

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
        # Rinkhals logo and general information
        self.panel_rinkhals = myPanel(left=0, top=0, bottom=0, components=[
            myStackPanel(left=0, right=0, top=0, bottom=0, background_color=None, components=[
                Picture(SCRIPT_PATH + '/icon.png', top=40, height=64),
                myLabel('Rinkhals', font_size=FONT_TITLE_SIZE, top=20),
                firmware_label := myLabel('Firmware:', font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE, top=8),
                version_label := myLabel('Version:', font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE, top=2),
                root_label := myLabel('Root:', font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE, top=2),
                home_label := myLabel('Home:', font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE, top=2),
                disk_label := myLabel('Disk usage:', font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE, top=2)
            ]),
            myButton('', font_path=ICON_FONT_PATH, font_size=24, left=0, right=None, width=48, top=0, background_color=None, border_width=0, callback=lambda: self.quit())
        ])
        self.panel_rinkhals.firmware_label = firmware_label
        self.panel_rinkhals.version_label = version_label
        self.panel_rinkhals.root_label = root_label
        self.panel_rinkhals.home_label = home_label
        self.panel_rinkhals.disk_label = disk_label

        # Main manu
        self.panel_main = myStackPanel(left=0, right=0, bottom=0, components=[
            myButton('Manage apps', left=8, right=8, callback=lambda: self.set_screen_panel(self.panel_apps)),
            myButton('Stop Rinkhals', left=8, right=8, callback=lambda: self.show_dialog('Are you sure you want\nto stop Rinkhals?\n\nYou will need to reboot\nyour printer in order to\nstart Rinkhals again', action='Yes', callback=lambda: self.stop_rinkhals())),
            myButton('Disable Rinkhals', text_color=COLOR_DANGER, left=8, right=8, callback=lambda: self.show_dialog('Are you sure you want\nto disable Rinkhals?\n\nYou will need to reinstall\nRinkhals to start it again', action='Yes', action_color=COLOR_DANGER, callback=lambda: self.disable_rinkhals()))
        ])

        # App list and quick toggle
        self.panel_apps = myPanel(left=0, right=0, top=0, bottom=0, components=[
            apps_panel := ScrollPanel(left=0, right=0, top=48, bottom=0),
            myPanel(left=0, right=0, top=0, height=48, components=[
                myLabel('Manage apps', font_size=FONT_TITLE_SIZE, auto_size=False, left=0, right=0, top=0, bottom=0),
                myButton('', font_path=ICON_FONT_PATH, font_size=24, left=0, right=None, width=48, top=0, bottom=0, background_color=None, border_width=0, callback=lambda: self.set_screen_panel(self.panel_main)),
                myButton('', font_path=ICON_FONT_PATH, font_size=24, left=None, right=0, width=48, top=0, bottom=0, background_color=None, border_width=0, callback=lambda: self.set_screen_panel(self.panel_apps))
            ])
        ])
        self.panel_apps.apps_panel = apps_panel

        # Detailed app screen
        self.panel_app = myPanel(left=0, right=0, top=0, bottom=0, components=[
            myScrollPanel(left=0, right=0, top=48, bottom=0, components=[
                app_version := myLabel(top=0, font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE),
                app_path := myLabel(top=2, font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE),
                app_description := myLabel(top=6, font_size=FONT_SUBTITLE_SIZE, text_align='mm'),
                myPanel(left=0, right=0, top=16, height=48, components=[
                    myPanel(left=0, width=96, top=0, bottom=0, background_color=None, components=[
                        myLabel('Disk', left=0, right=0, top=0, height=20, auto_size=False, font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE),
                        app_size := myLabel('?', left=0, right=0, top=18, height=24, auto_size=False),
                    ]),
                    myPanel(left=0, right=0, top=0, bottom=0, background_color=None, components=[
                        myLabel('Memory', left=0, right=0, top=0, height=20, auto_size=False, font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE),
                        app_memory := myLabel('?', left=0, right=0, top=18, height=24, auto_size=False),
                    ]),
                    myPanel(right=0, width=96, top=0, bottom=0, background_color=None, components=[
                        myLabel('CPU', left=0, right=0, top=0, height=20, auto_size=False, font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE),
                        app_cpu :=myLabel('?', left=0, right=0, top=18, height=24, auto_size=False),
                    ])
                ]),
                myPanel(left=0, right=0, top=4, height=40, components=[
                    myLabel('Status', left=8, right=8, top=0, bottom=0, auto_size=False, text_align='lm'),
                    app_status := myLabel('', left=8, right=8, top=0, bottom=0, auto_size=False, text_align='rm')
                ]),
                myPanel(left=0, right=0, top=4, height=40, components=[
                    myLabel('Enabled', left=8, right=0, top=0, bottom=0, auto_size=False, text_align='lm'),
                    app_toggle_enabled := myCheckBox(right=8, top=0)
                ]),
                # myPanel(left=0, right=0, top=8, height=48, components=[
                #     app_configuration := myButton('Configuration', left=8, right=64, top=0, height=48),
                #     app_qr_code := myButton('', font_path=ICON_FONT_PATH, font_size=28, left=None, right=8, top=0, height=48, width=48)
                # ]),
                app_toggle_started := myButton('Start', left=8, right=8, top=8, bottom=8, height=48)
            ]),
            myPanel(left=0, right=0, top=0, height=48, components=[
                app_title := myLabel('', font_size=FONT_TITLE_SIZE, auto_size=False, left=0, right=0, top=0, bottom=0),
                myButton('', font_path=ICON_FONT_PATH, font_size=24, left=0, right=None, width=48, top=0, bottom=0, background_color=None, border_width=0, callback=lambda: self.set_screen_panel(self.panel_apps)),
                app_refresh := myButton('', font_path=ICON_FONT_PATH, font_size=24, left=None, right=0, width=48, top=0, bottom=0, background_color=None, border_width=0)
            ])
        ])
        self.panel_app.app_title = app_title
        self.panel_app.app_refresh = app_refresh
        self.panel_app.app_version = app_version
        self.panel_app.app_path = app_path
        self.panel_app.app_description = app_description
        self.panel_app.app_size = app_size
        self.panel_app.app_memory = app_memory
        self.panel_app.app_cpu = app_cpu
        self.panel_app.app_status = app_status
        self.panel_app.app_toggle_enabled = app_toggle_enabled
        self.panel_app.app_toggle_started = app_toggle_started

        # Dialog overlay
        def dismiss_dialog():
            self.panel_dialog.visible = False
            self.screen.layout()
            self.screen.draw()

        self.panel_dialog = StackPanel(left=0, right=0, top=0, bottom=0, background_color=(0, 0, 0, 192), layout_mode=Component.LayoutMode.Absolute, touch_callback=dismiss_dialog, components=[
            StackPanel(width=min(360, self.screen.width - 48), top=0, height=self.screen.height, background_color=None, layout_mode=Component.LayoutMode.Absolute, orientation=StackPanel.Orientation.Horizontal, touch_callback=dismiss_dialog, components=[
                myStackPanel(auto_size=True, left=0, right=0, components=[
                    dialog_text := myLabel('', top=12, bottom=16),
                    dialog_button := myButton('', top=0, bottom=12, height=48, width=96)
                ])
            ])
        ])
        self.panel_dialog.dialog_text = dialog_text
        self.panel_dialog.dialog_button = dialog_button
        self.panel_dialog.visible = False

        # Screen setup, responsive design
        self.panel_screen = myPanel(right=0, top=0, bottom=0, background_color=None, layout_mode=Component.LayoutMode.Absolute)

        if self.screen.width > self.screen.height:
            self.panel_rinkhals.right = self.screen.width / 2
            self.panel_rinkhals.bottom = 0
            self.panel_screen.left = self.screen.width / 2
            self.panel_main.top = 0

            self.screen.components.append(self.panel_rinkhals)
            self.screen.components.append(self.panel_screen)
        else:
            self.panel_rinkhals.right = 0
            self.panel_rinkhals.bottom = 0
            self.panel_screen.left = 0
            self.panel_screen.top = 24
            self.panel_dialog.top = 24
            self.panel_main.top = self.screen.height - 210

            self.panel_main = Panel(left=0, right=0, top=0, bottom=0, components=[
                self.panel_rinkhals,
                self.panel_main
            ])

            self.screen.components.append(self.panel_screen)

        # On K2P and K3 redraw the title bar to keep information
        if KOBRA_MODEL_CODE != 'KS1':
            def draw_callback(draw, offset_x, offset_y):
                buffer = self.screen.capture()
                buffer = buffer.crop((0, 0, buffer.width, 24))
                draw._image.paste(buffer, (0, 0))

            self.screen.components.append(CallbackComponent(draw_callback=draw_callback, left=0, top=0, right=0, height=24))
        
        self.screen.components.append(self.panel_dialog)
        self.screen.layout_mode = Component.LayoutMode.Absolute
        self.screen.layout()

        self.set_screen_panel(self.panel_main)

    def layout_main(self):
        self.panel_rinkhals.firmware_label.text = f'Firmware: {KOBRA_VERSION}'
        self.panel_rinkhals.version_label.text = f'Version: {RINKHALS_VERSION}'
        self.panel_rinkhals.root_label.text = f'Root: {ellipsis(RINKHALS_ROOT, 32)}'
        self.panel_rinkhals.home_label.text = f'Home: {ellipsis(RINKHALS_HOME, 32)}'
        self.panel_rinkhals.disk_label.text = f'Disk usage: ?'

        def update_disk_usage(result):
            self.panel_rinkhals.disk_label.text = f'Disk usage: {result}'
            self.panel_rinkhals.layout()
            self.screen.draw()

        if USING_SHELL:
            shell_async(f'df -Ph {RINKHALS_ROOT} | tail -n 1 | awk \'{{print $3 " / " $2 " (" $5 ")"}}\'', update_disk_usage)
    def layout_apps(self):
        def show_app(app):
            logging.info(f'Navigating to {app}...')
            self.layout_app(app)
            self.set_screen_panel(self.panel_app)
            self.screen.layout()
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
            self.app_checkboxes[app].checked = is_app_enabled(app) == '1'
            
        self.panel_apps.apps_panel.components.clear()
        self.app_checkboxes = {}

        apps = list_apps().split(' ')
        for app in apps:
            enabled = is_app_enabled(app) == '1'
            logging.info(f'Found {app}: {enabled}')

            component = myPanel(left=0, right=0, top=4, bottom=4, height=48, components=[
                myButton(app, top=0, text_align='lm', callback=lambda app=app: show_app(app)),
                app_checkbox := myCheckBox(right=12, top=4, checked=enabled, callback=lambda checked, app=app: toggle_app(app, checked))
            ])

            self.app_checkboxes[app] = app_checkbox
            self.panel_apps.apps_panel.components.append(component)
    def layout_app(self, app):
        def refresh_app(app):
            self.layout_app(app)
            self.screen.layout()
        def toggle_app(app, checked):
            if checked:
                logging.info(f'Enabling {app}...')
                enable_app(app)
            else:
                logging.info(f'Disabling {app}...')
                disable_app(app)
            self.panel_app.app_toggle_enabled.checked = is_app_enabled(app) == '1'
        def _start_app(app):
            start_app(app)
            self.layout_app(app)
            self.panel_app.layout()
            self.screen.draw()
        def _stop_app(app):
            stop_app(app)
            self.layout_app(app)
            self.panel_app.layout()
            self.screen.draw()
   
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
        app_enabled = is_app_enabled(app) == '1'
        app_status = get_app_status(app)

        self.panel_app.app_title.text = ellipsis(app_name, 24)
        self.panel_app.app_refresh.callback = lambda app=app: refresh_app(app)
        self.panel_app.app_version.text = f'Version: {app_version}'
        self.panel_app.app_path.text = ellipsis(app_root, 40)
        self.panel_app.app_description.text = '\n'.join(i for i in wrap(app_description, 48))
        self.panel_app.app_size.text = '?'
        self.panel_app.app_memory.text = '?'
        self.panel_app.app_cpu.text = '?'
        self.panel_app.app_status.text = app_status
        self.panel_app.app_toggle_enabled.checked = app_enabled
        self.panel_app.app_toggle_enabled.callback = lambda checked, app=app: toggle_app(app, checked)
        
        def update_app_size(result):
            self.panel_app.app_size.text = result
            self.panel_app.layout()
            self.screen.draw()
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

            self.panel_app.app_memory.text = f'{round(app_memory, 1)}M'
            self.panel_app.layout()
            self.screen.draw()

            for pid in app_pids:
                p = psutil.Process(int(pid))
                app_cpu += p.cpu_percent(interval=1)

            self.panel_app.app_cpu.text = f'{round(app_cpu, 1)}%'
            self.panel_app.layout()
            self.screen.draw()
        run_async(update_memory)

        if app_status == 'started':
            self.panel_app.app_toggle_started.visible = True
            self.panel_app.app_toggle_started.text = 'Stop app'
            self.panel_app.app_toggle_started.text_color = COLOR_DANGER
            self.panel_app.app_toggle_started.callback = lambda app=app: _stop_app(app)
        elif app_status == 'stopped':
            self.panel_app.app_toggle_started.visible = True
            self.panel_app.app_toggle_started.text = 'Start app'
            self.panel_app.app_toggle_started.text_color = COLOR_TEXT
            self.panel_app.app_toggle_started.callback = lambda app=app: _start_app(app)
        else:
            self.panel_app.app_toggle_started.visible = False

    def set_screen_panel(self, panel):
        self.panel_screen.components = [ panel ]

        if panel == self.panel_main: self.layout_main()
        if panel == self.panel_apps: self.layout_apps()

        self.panel_screen.layout()
    def show_dialog(self, text, action='OK', action_color=COLOR_TEXT, callback=None):
        def button_callback():
            self.panel_dialog.visible = False
            self.screen.layout()
            self.screen.draw()

            if callback:
                callback()
        
        self.panel_dialog.dialog_text.text = text
        self.panel_dialog.dialog_button.text = action
        self.panel_dialog.dialog_button.text_color = action_color
        self.panel_dialog.dialog_button.callback = button_callback

        self.panel_dialog.visible = True
        self.screen.layout()
        self.screen.draw()

    def stop_rinkhals(self):
        logging.info('Stopping Rinkhals...')

        screen = None

        if not USING_SIMULATOR:
            self.clear()
            os.system(RINKHALS_ROOT + '/stop.sh')
        else:
            self.quit()
    def disable_rinkhals(self):
        logging.info('Disabling Rinkhals...')

        if not USING_SIMULATOR:
            self.clear()
            with open('/useremain/rinkhals/.disable-rinkhals', 'wb'):
                pass
            os.system('reboot')

        self.quit()

    def clear(self):
        if not USING_SIMULATOR:
            os.system(f'dd if=/dev/zero of=/dev/fb0 bs={self.width * 4} count={self.height}')
    def run(self):
        self.screen.run()
        self.quit()
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
            logging.error(traceback.format_exc())
            
    os.kill(os.getpid(), 9)
