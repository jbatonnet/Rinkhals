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

from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import paho.mqtt.client as paho
from gui import *


class JSONWithCommentsDecoder(json.JSONDecoder):
    def __init__(self, **kwgs):
        super().__init__(**kwgs)
    def decode(self, s: str):
        regex = r"""("(?:\\"|[^"])*?")|(\/\*(?:.|\s)*?\*\/|\/\/.*)"""
        s = re.sub(regex, r"\1", s)  # , flags = re.X | re.M)
        return super().decode(s)

def shell(command):
    result = subprocess.check_output(['sh', '-c', command])
    result = result.decode('utf-8').strip()
    logging.debug(f'Shell "{command}" => "{result}"')
    return result
def ellipsis(text, length):
    if len(text) > length:
        text = text[:int(length / 2)] + '...' + text[-int(length / 2):]
    return text
def cache(getter, key = None):
    if not key:
        key = f'line:{sys._getframe().f_back.f_lineno}'
    item = Cache.get(key)
    if item is None:
        item = getter()
        Cache.set(key, item)
    return item


DEBUG = os.getenv('DEBUG')
DEBUG = not not DEBUG
DEBUG = True

# Setup logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Detect Rinkhals root
RINKHALS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

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
    KOBRA_VERSION = '1.2.3.4'

    if KOBRA_MODEL_CODE == 'KS1':
        QT_QPA_PLATFORM = 'linuxfb:fb=/dev/fb0:size=800x480:rotation=180:offset=0x0:nographicsmodeswitch'
    else:
        QT_QPA_PLATFORM = 'linuxfb:fb=/dev/fb0:size=480x272:rotation=90:offset=0x0:nographicsmodeswitch'

    def list_apps(): return [ f.name for f in os.scandir(f'{RINKHALS_HOME}/apps') if f.is_dir() ]
    def get_app_root(app): return f'{RINKHALS_HOME}/apps/{app}'
    def is_app_enabled(app): return os.path.exists(f'{RINKHALS_HOME}/apps/{app}/.enabled')
    def enable_app(): pass
    def disable_app(): pass
    def start_app(): pass
    def stop_app(): pass
else:
    environment = shell(f'. {RINKHALS_ROOT}/tools.sh && python -c "import os, json; print(json.dumps(dict(os.environ)))"')
    environment = json.loads(environment)

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
            return shell(f'. {RINKHALS_ROOT}/tools.sh && {function_name} ' + ' '.join([ str(a) for a in args ]))
        return tool_function

    list_apps = load_tool_function('list_apps')
    get_app_root = load_tool_function('get_app_root')
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
FONT_PATH = RINKHALS_ROOT + '/opt/rinkhals/ui/AlibabaSans-Regular.ttf'
FONT_TITLE_SIZE = 16
FONT_SUBTITLE_SIZE = 11
FONT_TEXT_SIZE = 14

COLOR_PRIMARY = (0, 128, 255)
COLOR_SECONDARY = (96, 96, 96)
COLOR_TEXT = (255, 255, 255)
COLOR_BACKGROUND = (0, 0, 0)
COLOR_DANGER = (255, 64, 64)
COLOR_SUBTITLE = (160, 160, 160)
COLOR_DISABLED = (176, 176, 176)
COLOR_SHADOW = (96, 96, 96)

def myButton(*args, height=48, font_path=FONT_PATH, font_size=FONT_TEXT_SIZE, background_color=(16, 16, 16), border_color=(0, 0, 0), border_width=4, **kwargs):
    return Button(*args, height=height, font_path=font_path, font_size=font_size, background_color=background_color, border_color=border_color, border_width=border_width, **kwargs)
def myStackPanel(*args, border_width=1, border_color=(255, 0, 255), **kwargs):
    return StackPanel(*args, border_width=border_width, border_color=border_color, **kwargs)
def myPanel(*args, border_width=1, border_color=(255, 0, 255), **kwargs):
    return Panel(*args, border_width=border_width, border_color=border_color, **kwargs)
def myLabel(*args, font_path=FONT_PATH, font_size=FONT_TEXT_SIZE, text_color=COLOR_TEXT, **kwargs):
    return Label(*args, font_path=font_path, font_size=font_size, text_color=text_color, **kwargs)


class Program:
    screen = None

    # Assets
    icon_rinkhals_path = RINKHALS_ROOT + '/opt/rinkhals/ui/icon.bmp'

    # Cache
    disk_usage = None
    apps_size = {}

    def __init__(self):
        if USING_SIMULATOR:
            self.screen = SimulatorScreen('Kobra simulator', SCREEN_WIDTH, SCREEN_HEIGHT)
        else:
            self.screen = TouchFramebuffer('/dev/fb0', '/dev/input/event0')

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

        log(LOG_INFO, f'Monitoring K3SysUi (PID: {pid})')

        while True:
            time.sleep(5)

            try:
                os.kill(pid, 0)
            except OSError:
                log(LOG_INFO, 'K3SysUi is gone, exiting...')
                self.quit()
    def monitor_mqtt(self):
        def mqtt_on_connect(client, userdata, flags, reason_code, properties):
            client.subscribe(f'anycubic/anycubicCloud/v1/+/printer/{KOBRA_MODEL_ID}/{KOBRA_DEVICE_ID}/print')
            log(LOG_INFO, 'Monitoring MQTT...')
        def mqtt_on_connect_fail(client, userdata):
            log(LOG_INFO, 'MQTT connection failed')
        def mqtt_on_log(client, userdata, level, buf):
            logging.debug(buf)
        def mqtt_on_message(client, userdata, msg):
            log(LOG_INFO, 'Received print event, exiting...')
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

    def is_screen_on(self):
        brightness = shell('cat /sys/class/backlight/backlight/brightness')
        return brightness != '0'
    def turn_on_screen(self):
        shell('echo 255 > /sys/class/backlight/backlight/brightness')
    def turn_off_screen(self):
        shell('echo 0 > /sys/class/backlight/backlight/brightness')

    def layout(self):
        def setScreenPanel(panel):
            self.panel_screen.components = [ panel ]
            if panel == self.panel_main: self.layout_main()
            if panel == self.panel_apps: self.layout_apps()
            self.screen.layout()

        self.panel_rinkhals = myStackPanel(left=0, top=0, bottom=0, background_color=(0, 0, 0), components=[
            Picture(self.icon_rinkhals_path, top=40, height=64),
            myLabel('Rinkhals', font_size=FONT_TITLE_SIZE, top=20),
            firmware_label := myLabel('Firmware:', font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE, top=8),
            version_label := myLabel('Version:', font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE, top=2),
            root_label := myLabel('Root:', font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE, top=2),
            home_label := myLabel('Home:', font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE, top=2),
            disk_label := myLabel('Disk usage:', font_size=FONT_SUBTITLE_SIZE, text_color=COLOR_SUBTITLE, top=2)
        ])
        self.panel_rinkhals.firmware_label = firmware_label
        self.panel_rinkhals.version_label = version_label
        self.panel_rinkhals.root_label = root_label
        self.panel_rinkhals.home_label = home_label
        self.panel_rinkhals.disk_label = disk_label

        self.panel_main = myStackPanel(left=0, right=0, bottom=0, components=[
            myButton('Manage apps', left=0, right=0, callback=lambda: setScreenPanel(self.panel_apps)),
            myButton('Stop Rinkhals', text_color=(255, 64, 64), left=0, right=0)
        ])

        self.panel_screen = myPanel(right=0, top=0, bottom=0, layout_mode=Component.LayoutMode.Absolute)

        self.panel_dialog = myPanel(left=0, right=0, top=0, bottom=0, layout_mode=Component.LayoutMode.Absolute, components=[
            #myPanel(left=48, right=48, top=48, bottom=48)
        ])


        if self.screen.width > self.screen.height:
            self.panel_rinkhals.right = self.screen.width / 2
            self.panel_rinkhals.bottom = 0
            self.panel_screen.left = self.screen.width / 2
            self.panel_main.top = 0

            self.screen.components.append(self.panel_rinkhals)
            self.screen.components.append(self.panel_screen)
        else:
            self.panel_rinkhals.right = 0
            self.panel_rinkhals.bottom = 210
            self.panel_screen.left = 0
            self.panel_main.top = self.screen.height - 210

            self.panel_main = Panel(left=0, right=0, top=0, bottom=0, components=[
                self.panel_rinkhals,
                self.panel_main
            ])

            self.screen.components.append(self.panel_screen)

        self.panel_apps = myStackPanel(left=0, right=0, top=0, bottom=0, components=[
            myPanel(left=0, right=0, height=48, components=[
                myLabel('Manage apps', font_size=FONT_TITLE_SIZE, auto_size=False, left=0, right=0, top=0, bottom=0),
                myButton('<', font_size=18, left=0, width=48, top=0, bottom=0, background_color=(0, 0, 0), callback=lambda: setScreenPanel(self.panel_main))
            ]),
            apps_panel := ScrollPanel(left=0, right=0, top=48, bottom=0)
        ])
        self.panel_apps.apps_panel = apps_panel

        self.screen.layout_mode = Component.LayoutMode.Absolute
        setScreenPanel(self.panel_main)
    def layout_main(self):
        self.panel_rinkhals.firmware_label.text = f'Firmware: {KOBRA_VERSION}'
        self.panel_rinkhals.version_label.text = f'Version: {RINKHALS_VERSION}'
        self.panel_rinkhals.root_label.text = f'Root: {ellipsis(RINKHALS_ROOT, 32)}'
        self.panel_rinkhals.home_label.text = f'Home: {ellipsis(RINKHALS_HOME, 32)}'

        disk_usage = cache(lambda: shell(f'df -Ph {RINKHALS_ROOT} | tail -n 1 | awk \'{{print $3 " / " $2 " (" $5 ")"}}\'') if USING_SHELL else '?G / ?G (?%)')
        self.panel_rinkhals.disk_label.text = f'Disk usage: {disk_usage}'
    def layout_apps(self):
        self.panel_apps.components = [ self.panel_apps.components[0] ]

        apps = list_apps()
        for app in apps:
            enabled = is_app_enabled(app)
            logging.info(f'Found {app}: {enabled}')

            component = myPanel(left=0, right=0, height=48, components=[
                myButton(app, left=0, right=0, top=0, bottom=0)
            ])
            self.panel_apps.components.append(component)

    def run(self):
        self.screen.run()
        self.quit()
    def quit(self):
        logging.info('Exiting Rinkhals UI...')
        self.redraw = False

        time.sleep(0.25)
        os.kill(os.getpid(), 9)


if __name__ == "__main__":
    if USING_SIMULATOR:
        program = Program()
        program.run()
    else:
        try:
            program = Program()
            program.loop()
        except Exception as e:
            log(LOG_ERROR, str(e))
            log(LOG_ERROR, traceback.format_exc())
            os.kill(os.getpid(), 9)
