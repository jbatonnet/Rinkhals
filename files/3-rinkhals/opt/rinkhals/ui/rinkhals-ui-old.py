import os
import time
import sys
import json
import re
import subprocess
import threading
import platform
import traceback

from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import paho.mqtt.client as paho

class JSONWithCommentsDecoder(json.JSONDecoder):
    def __init__(self, **kwgs):
        super().__init__(**kwgs)
    def decode(self, s: str):
        regex = r"""("(?:\\"|[^"])*?")|(\/\*(?:.|\s)*?\*\/|\/\/.*)"""
        s = re.sub(regex, r"\1", s)  # , flags = re.X | re.M)
        return super().decode(s)


DEBUG = os.getenv('DEBUG')
DEBUG = not not DEBUG
DEBUG = True


USING_SIMULATOR = True
if os.path.exists('/dev/fb0'):
    USING_SIMULATOR = False

COLOR_PRIMARY = (0, 128, 255)
COLOR_SECONDARY = (96, 96, 96)
COLOR_TEXT = (255, 255, 255)
COLOR_BACKGROUND = (0, 0, 0)
COLOR_DANGER = (255, 64, 64)
COLOR_SUBTITLE = (160, 160, 160)
COLOR_DISABLED = (176, 176, 176)
COLOR_SHADOW = (96, 96, 96)


RINKHALS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

USING_SHELL = True
if platform.system() == 'Windows':
    if os.system('sh -c "echo"') != 0:
        USING_SHELL = False
    else:
        RINKHALS_ROOT = RINKHALS_ROOT.replace('\\', '/')
    if os.system('sh -c "ls /mnt/c"') == 0:
        RINKHALS_ROOT = '/mnt/' + RINKHALS_ROOT[0].lower() + RINKHALS_ROOT[2:]

if USING_SIMULATOR:
    RINKHALS_HOME = f'{RINKHALS_ROOT}/../4-apps/home/rinkhals'
    RINKHALS_VERSION = 'dev'
    KOBRA_MODEL = 'Anycubic Kobra'
    KOBRA_VERSION = '1.2.3.4'
    KOBRA_MODEL_CODE = 'KS1'
else:
    command = f'source {RINKHALS_ROOT}/tools.sh && python -c "import os, json; print(json.dumps(dict(os.environ)))"'
    environment = subprocess.check_output(['sh', '-c', command])
    environment = json.loads(environment.decode('utf-8').strip())

    RINKHALS_HOME = environment['RINKHALS_HOME']
    RINKHALS_VERSION = environment['RINKHALS_VERSION']
    KOBRA_MODEL_ID = environment['KOBRA_MODEL_ID']
    KOBRA_MODEL = environment['KOBRA_MODEL']
    KOBRA_MODEL_CODE = environment['KOBRA_MODEL_CODE']
    KOBRA_VERSION = environment['KOBRA_VERSION']
    KOBRA_DEVICE_ID = environment['KOBRA_DEVICE_ID']

# TODO: Read that from QT_QPA_PLATFORM
# For example: QT_QPA_PLATFORM=linuxfb:fb=/dev/fb0:size=800x480:rotation=180:offset=0x0:nographicsmodeswitch
if KOBRA_MODEL_CODE == 'KS1':
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 480
    SCREEN_ROTATION = 180
    TOUCH_CALIBRATION_MIN_X = 800
    TOUCH_CALIBRATION_MAX_X = 0
    TOUCH_CALIBRATION_MIN_Y = 480
    TOUCH_CALIBRATION_MAX_Y = 0
else:
    SCREEN_WIDTH = 272
    SCREEN_HEIGHT = 480
    SCREEN_ROTATION = 90
    TOUCH_CALIBRATION_MIN_X = 235
    TOUCH_CALIBRATION_MAX_X = 25
    TOUCH_CALIBRATION_MIN_Y = 460
    TOUCH_CALIBRATION_MAX_Y = 25

if KOBRA_MODEL_CODE == 'KS1':
    BUTTON_HEIGHT = 60
else:
    BUTTON_HEIGHT = 44

BUILTIN_APP_PATH = f'{RINKHALS_ROOT}/home/rinkhals/apps'
USER_APP_PATH = f'{RINKHALS_HOME}/apps'

REMOTE_MODE = 'cloud'
if os.path.isfile('/useremain/dev/remote_ctrl_mode'):
    with open('/useremain/dev/remote_ctrl_mode', 'r') as f:
        REMOTE_MODE = f.read().strip()


if USING_SIMULATOR:
    from tkinter import Tk, Label
    from PIL import ImageTk
else:
    import evdev


LOG_DEBUG = 0
LOG_INFO = 1
LOG_WARNING = 2
LOG_ERROR = 3

LOG_LEVEL = LOG_DEBUG if DEBUG else LOG_INFO

def log(level, message):
    if level >= LOG_LEVEL:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + message, flush = True)
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
    log(LOG_DEBUG, f'Shell "{command}" => "{result}"')
    return result


class Program:

    # State
    redraw = True
    touch_down = None
    screen = 'main'
    dialog = None
    selected_app = None
    touch_actions = []
    apps_page = 0
    last_screen_check = 0

    # Assets
    font_title = None
    font_subtitle = None
    font_text = None
    icon_rinkhals = None

    # Cache
    disk_usage = None
    apps_size = {}

    def __init__(self):
        if not USING_SIMULATOR:
            self.touch_device = evdev.InputDevice('/dev/input/event0')
            self.touch_last_x = 0
            self.touch_last_y = 0
            self.touch_down_builder = None
            self.touch_device.grab()
        else:
            def on_closing():
                self.window.destroy()
                self.quit()
            def on_mouse_down(event):
                self.on_touch_down(event.x, event.y)
            def on_mouse_up(event):
                self.on_touch_up(event.x, event.y)
            def on_mouse_move(event):
                self.on_touch_move(event.x, event.y)

            self.window = Tk()
            self.window.title('Kobra display')
            self.window.geometry(f'{SCREEN_WIDTH}x{SCREEN_HEIGHT}')
            self.window.resizable(False, False)
            self.window.configure(bg='black')
            self.window.update()

            self.window_panel = Label(self.window)
            self.window_panel.pack(fill = "both", expand = "yes")

            self.window.protocol("WM_DELETE_WINDOW", on_closing)
            self.window.bind('<Button-1>', on_mouse_down)
            self.window.bind('<ButtonRelease-1>', on_mouse_up)
            self.window.bind('<B1-Motion>', on_mouse_move)

        log(LOG_DEBUG, f'Simulator: {USING_SIMULATOR}')
        log(LOG_DEBUG, f'Root: {RINKHALS_ROOT}')
        log(LOG_DEBUG, f'Home: {RINKHALS_HOME}')

        # Subscribe to print event to exit in case of print
        if not USING_SIMULATOR and REMOTE_MODE == 'lan':
            self.monitor_mqtt()

        # Monitor K3SysUi process to exit if it dies
        if not USING_SIMULATOR:
            monitor_thread = threading.Thread(target = self.monitor_k3sysui)
            monitor_thread.start()

        icon_scale = 0.5
        self.icon_rinkhals = Image.open(RINKHALS_ROOT + '/opt/rinkhals/ui/icon.bmp').convert('RGBA')
        self.icon_rinkhals = self.icon_rinkhals.resize((int(self.icon_rinkhals.width * icon_scale), int(self.icon_rinkhals.height * icon_scale)))

        font_path = RINKHALS_ROOT + '/opt/rinkhals/ui/AlibabaSans-Regular.ttf'
        self.font_title = ImageFont.truetype(font_path, 24 if KOBRA_MODEL_CODE == 'KS1' else 16)
        self.font_subtitle = ImageFont.truetype(font_path, 15 if KOBRA_MODEL_CODE == 'KS1' else 11)
        self.font_text = ImageFont.truetype(font_path, 20 if KOBRA_MODEL_CODE == 'KS1' else 14)

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
            log(LOG_DEBUG, buf)
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

    def loop(self):

        while True:
            if not self.redraw:
                self.process_events(250)
                continue

            self.redraw = False

            self.touch_actions = []

            if KOBRA_MODEL_CODE == 'KS1':
                buffer = Image.new('RGBA', (SCREEN_WIDTH, SCREEN_HEIGHT), COLOR_BACKGROUND)
            else:
                buffer = self.capture()
                
            draw = ImageDraw.Draw(buffer)

            if KOBRA_MODEL_CODE == 'KS1':
                draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), fill = (0, 0, 0))
            else:
                draw.rectangle((0, 24, SCREEN_WIDTH, SCREEN_HEIGHT), fill = (0, 0, 0))

            if self.screen == 'main':
                self.draw_main_screen(buffer, draw)
            elif self.screen == 'apps':
                self.draw_apps_screen(buffer, draw)
            elif self.screen == 'app':
                self.draw_app_screen(buffer, draw)

            self.display(buffer)

        quit()

    def draw_main_screen(self, buffer, draw):
        draw.text((32, 48), '<', fill = COLOR_TEXT, font = self.font_title, anchor = 'mm')
        self.touch_actions.append(((0, 24, 48, 72), lambda: self.quit()))

        icon_x = ((SCREEN_WIDTH / 4) if KOBRA_MODEL_CODE == 'KS1' else (SCREEN_WIDTH / 2)) - self.icon_rinkhals.width / 2
        icon_y = 116 if KOBRA_MODEL_CODE == 'KS1' else 56
        buffer.alpha_composite(self.icon_rinkhals, (int(icon_x), int(icon_y)))

        root = RINKHALS_ROOT
        if len(root) > 32:
            root = root[:16] + '...' + root[-16:]

        home = RINKHALS_HOME
        if len(home) > 32:
            home = home[:16] + '...' + home[-16:]

        if not self.disk_usage:
            self.disk_usage = shell(f'df -Ph {RINKHALS_ROOT} | tail -n 1 | awk \'{{print $3 " / " $2 " (" $5 ")"}}\'') if USING_SHELL else '?G / ?G (?%)'

        current_x = (SCREEN_WIDTH / 4) if KOBRA_MODEL_CODE == 'KS1' else SCREEN_WIDTH / 2
        current_y = 214 if KOBRA_MODEL_CODE == 'KS1' else 144
        draw.text((current_x, current_y), 'Rinkhals', fill = COLOR_TEXT, font = self.font_title, anchor = 'mm')
        current_y += 40 if KOBRA_MODEL_CODE == 'KS1' else 24
        draw.text((current_x, current_y), 'Firmware: ' + KOBRA_VERSION, fill = COLOR_SUBTITLE, font = self.font_subtitle, anchor = 'mm')
        current_y += 20 if KOBRA_MODEL_CODE == 'KS1' else 16
        draw.text((current_x, current_y), 'Version: ' + RINKHALS_VERSION, fill = COLOR_SUBTITLE, font = self.font_subtitle, anchor = 'mm')
        current_y += 20 if KOBRA_MODEL_CODE == 'KS1' else 16
        draw.text((current_x, current_y), 'Root: ' + root, fill = COLOR_SUBTITLE, font = self.font_subtitle, anchor = 'mm')
        current_y += 20 if KOBRA_MODEL_CODE == 'KS1' else 16
        draw.text((current_x, current_y), 'Home: ' + home, fill = COLOR_SUBTITLE, font = self.font_subtitle, anchor = 'mm')
        current_y += 20 if KOBRA_MODEL_CODE == 'KS1' else 16
        draw.text((current_x, current_y), 'Disk usage: ' + self.disk_usage, fill = COLOR_SUBTITLE, font = self.font_subtitle, anchor = 'mm')

        current_y = 64 if KOBRA_MODEL_CODE == 'KS1' else 280
        margin_left = SCREEN_WIDTH / 2 if KOBRA_MODEL_CODE == 'KS1' else 0

        surface = (margin_left, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH, current_y + BUTTON_HEIGHT / 2)
        if not self.dialog and self.touch_down and self.touch_down[1] >= current_y - BUTTON_HEIGHT / 2 and self.touch_down[1] <= current_y + BUTTON_HEIGHT / 2:
            draw.rectangle(surface, fill = COLOR_SECONDARY)
        draw.text((margin_left + 16, current_y), 'Manage apps', fill = COLOR_TEXT, font = self.font_text, anchor = 'lm')
        draw.text((SCREEN_WIDTH - 16, current_y), '>', fill = COLOR_TEXT, font = self.font_text, anchor = 'rm')
        self.touch_actions.append((surface, lambda: self.show_screen('apps')))

        # current_y = current_y + BUTTON_HEIGHT
        # surface = (0, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH, current_y + BUTTON_HEIGHT / 2)
        # if not dialog and touch_down and touch_down[1] >= current_y - BUTTON_HEIGHT / 2 and touch_down[1] <= current_y + BUTTON_HEIGHT / 2:
        #     draw.rectangle(surface, fill = COLOR_SECONDARY)
        # draw.text((16, current_y), 'Clean storage (logs, old files, ...)', fill = self.COLOR_TEXT, font = font_text, anchor = 'lm')
        # touch_actions.append((surface, lambda: show_dialog('confirm-cleanup')))

        current_y = current_y + BUTTON_HEIGHT
        surface = (margin_left, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH, current_y + BUTTON_HEIGHT / 2)
        if not self.dialog and self.touch_down and self.touch_down[1] >= current_y - BUTTON_HEIGHT / 2 and self.touch_down[1] <= current_y + BUTTON_HEIGHT / 2:
            draw.rectangle(surface, fill = COLOR_SECONDARY)
        draw.text((margin_left + 16, current_y), 'Stop Rinkhals', fill = COLOR_TEXT, font = self.font_text, anchor = 'lm')
        self.touch_actions.append((surface, lambda: self.show_dialog('confirm-stop-rinkhals')))

        # current_y = current_y + BUTTON_HEIGHT
        # surface = (0, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH, current_y + BUTTON_HEIGHT / 2)
        # if not self.dialog and self.touch_down and self.touch_down[1] >= current_y - BUTTON_HEIGHT / 2 and self.touch_down[1] <= current_y + BUTTON_HEIGHT / 2:
        #     draw.rectangle(surface, fill = COLOR_SECONDARY)
        # draw.text((16, current_y), 'Restart Rinkhals', fill = COLOR_TEXT, font = self.font_text, anchor = 'lm')
        # touch_actions.append((surface, lambda: show_dialog('confirm-restart-rinkhals')))

        current_y = current_y + BUTTON_HEIGHT
        surface = (margin_left, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH, current_y + BUTTON_HEIGHT / 2)
        if not self.dialog and self.touch_down and self.touch_down[1] >= current_y - BUTTON_HEIGHT / 2 and self.touch_down[1] <= current_y + BUTTON_HEIGHT / 2:
            draw.rectangle(surface, fill = COLOR_SECONDARY)
        draw.text((margin_left + 16, current_y), 'Disable Rinkhals', fill = COLOR_DANGER, font = self.font_text, anchor = 'lm')
        self.touch_actions.append((surface, lambda: self.show_dialog('confirm-disable-rinkhals')))

        if self.dialog == 'confirm-cleanup':
            dialog_height = 144
            dialog_top = (SCREEN_HEIGHT - dialog_height) / 2
            button_top = dialog_top + dialog_height - 56

            draw.rounded_rectangle((32, dialog_top, SCREEN_WIDTH - 32, dialog_top + dialog_height), radius = 16, fill = COLOR_SECONDARY)
            draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 16), 'Are you sure you want to\nclean old logs and files?', align = 'center', fill = COLOR_TEXT, font = self.font_text, anchor = 'ma')
            draw.rounded_rectangle((72, button_top, SCREEN_WIDTH - 72, button_top + 36), radius = 8, fill = COLOR_PRIMARY)
            draw.text((SCREEN_WIDTH / 2, button_top + 18), 'Yes', fill = COLOR_TEXT, font = self.font_text, anchor = 'mm')

            self.touch_actions = []
            self.touch_actions.append(((72, button_top, SCREEN_WIDTH - 72, button_top + 36), lambda: self.show_dialog(None)))
            self.touch_actions.append(((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), lambda: self.show_dialog(None)))

        elif self.dialog == 'confirm-stop-rinkhals':
            dialog_height = 212
            dialog_top = (SCREEN_HEIGHT - dialog_height) / 2
            button_top = dialog_top + dialog_height - 56

            draw.rounded_rectangle((32, dialog_top, SCREEN_WIDTH - 32, dialog_top + dialog_height), radius = 16, fill = COLOR_SECONDARY)
            draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 16), 'Are you sure you want\nto stop Rinkhals?', align = 'center', fill = COLOR_TEXT, font = self.font_text, anchor = 'ma')
            draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 72), 'You will need to reboot\nyour printer in order to\nstart Rinkhals again', align = 'center', fill = COLOR_TEXT, font = self.font_text, anchor = 'ma')
            draw.rounded_rectangle((72, button_top, SCREEN_WIDTH - 72, button_top + 36), radius = 8, fill = COLOR_PRIMARY)
            draw.text((SCREEN_WIDTH / 2, button_top + 18), 'Yes', fill = COLOR_TEXT, font = self.font_text, anchor = 'mm')

            self.touch_actions = []
            self.touch_actions.append(((72, button_top, SCREEN_WIDTH - 72, button_top + 36), lambda: self.stop_rinkhals()))
            self.touch_actions.append(((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), lambda: self.show_dialog(None)))

        elif self.dialog == 'confirm-restart-rinkhals':
            dialog_height = 144
            dialog_top = (SCREEN_HEIGHT - dialog_height) / 2
            button_top = dialog_top + dialog_height - 56

            draw.rounded_rectangle((32, dialog_top, SCREEN_WIDTH - 32, dialog_top + dialog_height), radius = 16, fill = COLOR_SECONDARY)
            draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 16), 'Are you sure you want\nto restart Rinkhals?', align = 'center', fill = COLOR_TEXT, font = self.font_text, anchor = 'ma')
            draw.rounded_rectangle((72, button_top, SCREEN_WIDTH - 72, button_top + 36), radius = 8, fill = COLOR_PRIMARY)
            draw.text((SCREEN_WIDTH / 2, button_top + 18), 'Yes', fill = COLOR_TEXT, font = self.font_text, anchor = 'mm')

            self.touch_actions = []
            self.touch_actions.append(((72, button_top, SCREEN_WIDTH - 72, button_top + 36), lambda: self.restart_rinkhals()))
            self.touch_actions.append(((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), lambda: self.show_dialog(None)))

        elif self.dialog == 'confirm-disable-rinkhals':
            dialog_height = 196
            dialog_top = (SCREEN_HEIGHT - dialog_height) / 2
            button_top = dialog_top + dialog_height - 56

            draw.rounded_rectangle((32, dialog_top, SCREEN_WIDTH - 32, dialog_top + dialog_height), radius = 16, fill = COLOR_SECONDARY)
            draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 16), 'Are you sure you want\nto disable Rinkhals?', align = 'center', fill = COLOR_TEXT, font = self.font_text, anchor = 'ma')
            draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 72), 'You will need to reinstall\nRinkhals to start it again', align = 'center', fill = COLOR_TEXT, font = self.font_text, anchor = 'ma')
            draw.rounded_rectangle((72, button_top, SCREEN_WIDTH - 72, button_top + 36), radius = 8, fill = COLOR_DANGER)
            draw.text((SCREEN_WIDTH / 2, button_top + 18), 'Yes', fill = COLOR_TEXT, font = self.font_text, anchor = 'mm')

            self.touch_actions = []
            self.touch_actions.append(((72, button_top, SCREEN_WIDTH - 72, button_top + 36), lambda: self.disable_rinkhals()))
            self.touch_actions.append(((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), lambda: self.show_dialog(None)))

        pass
    def draw_apps_screen(self, buffer, draw):
        draw.text((32, 48), '<', fill = COLOR_TEXT, font = self.font_title, anchor = 'mm')
        self.touch_actions.append(((0, 24, 48, 72), lambda: self.show_screen('main')))

        log(LOG_DEBUG, f'Looking for apps in {BUILTIN_APP_PATH} and {USER_APP_PATH}...')

        builtin_apps = next(os.walk(BUILTIN_APP_PATH))[1] if os.path.exists(BUILTIN_APP_PATH) else []
        user_apps = next(os.walk(USER_APP_PATH))[1] if os.path.exists(USER_APP_PATH) else []

        apps = builtin_apps + user_apps
        apps = list(dict.fromkeys(apps))

        if USING_SIMULATOR:
            apps = apps + apps

        draw.text((SCREEN_WIDTH / 2, 50), 'Manage apps', fill = COLOR_TEXT, font = self.font_title, anchor = 'mm')

        current_y = 96

        apps_on_screen = round((SCREEN_HEIGHT - current_y) / BUTTON_HEIGHT) - 1
        page_start = self.apps_page * apps_on_screen
        page_end = min(page_start + apps_on_screen, len(apps))

        for app in apps[page_start:page_end]:

            user_app_root = f'{USER_APP_PATH}/{app}'
            builtin_app_root = f'{BUILTIN_APP_PATH}/{app}'

            app_root = user_app_root if os.path.exists(user_app_root) else builtin_app_root

            if not os.path.exists(f'{app_root}/app.sh') or not os.path.exists(f'{app_root}/app.json'):
                continue

            log(LOG_DEBUG, f'- Found {app} in {app_root}')

            app_manifest = None
            try:
                with open(f'{app_root}/app.json', 'r') as f:
                    app_manifest = json.loads(f.read(), cls = JSONWithCommentsDecoder)
            except Exception as e:
                if not USING_SIMULATOR:
                    continue

            app_schema_version = app_manifest.get('$version') if app_manifest else None
            if app_schema_version != '1':
                continue

            app_name = app_manifest.get('name') if app_manifest else app
            app_description = app_manifest.get('description') if app_manifest else ''
            app_version = app_manifest.get('version') if app_manifest else ''

            app_enabled = self.is_app_enabled(app, app_root)
                
            surface = (0, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH, current_y + BUTTON_HEIGHT / 2)
            if not self.dialog and self.touch_down and self.touch_down[1] >= current_y - BUTTON_HEIGHT / 2 and self.touch_down[1] <= current_y + BUTTON_HEIGHT / 2:
                draw.rectangle(surface, fill = COLOR_SECONDARY)
            draw.text((16, current_y), app_name + (f' ({app_version})' if app_version else ''), fill = COLOR_TEXT, font = self.font_text, anchor = 'lm')
            #draw.text((16, current_y + 9), description, fill = COLOR_TEXT, font = font_subtitle, anchor = 'lm')
            draw.rounded_rectangle((SCREEN_WIDTH - 60, current_y - 12, SCREEN_WIDTH - 12, current_y + 12), radius = 12, fill = COLOR_PRIMARY if app_enabled else COLOR_SECONDARY)
            position = SCREEN_WIDTH - 24 if app_enabled else SCREEN_WIDTH - 48
            draw.rounded_rectangle((position - 9, current_y - 9, position + 9, current_y + 9), 9, fill = COLOR_TEXT if app_enabled else COLOR_DISABLED)

            self.touch_actions.append(((0, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH - 60, current_y + BUTTON_HEIGHT / 2), lambda app = app: self.show_app(app)))
            self.touch_actions.append(((SCREEN_WIDTH - 60, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH, current_y + BUTTON_HEIGHT / 2), lambda app = app: self.toggle_app(app, start_stop=True)))

            current_y = current_y + BUTTON_HEIGHT

        if page_start > 0:
            button_rect = (SCREEN_WIDTH * 1 / 3 - 32, SCREEN_HEIGHT - 48, SCREEN_WIDTH * 1 / 3 + 32, SCREEN_HEIGHT - 16)
            draw.rounded_rectangle(button_rect, radius = 8, fill = COLOR_SECONDARY)
            draw.text((SCREEN_WIDTH * 1 / 3, SCREEN_HEIGHT - 32), '^', fill = COLOR_TEXT, font = self.font_text, anchor = 'mm')
            def page_up():
                self.apps_page = self.apps_page - 1
            self.touch_actions.append((button_rect, lambda: page_up()))
        if len(apps) > page_end:
            button_rect = (SCREEN_WIDTH * 2 / 3 - 32, SCREEN_HEIGHT - 48, SCREEN_WIDTH * 2 / 3 + 32, SCREEN_HEIGHT - 16)
            draw.rounded_rectangle(button_rect, radius = 8, fill = COLOR_SECONDARY)
            draw.text((SCREEN_WIDTH * 2 / 3, SCREEN_HEIGHT - 32), 'v', fill = COLOR_TEXT, font = self.font_text, anchor = 'mm')
            def page_down():
                self.apps_page = self.apps_page + 1
            self.touch_actions.append((button_rect, lambda: page_down()))

        pass
    def draw_app_screen(self, buffer, draw):
        draw.text((32, 48), '<', fill = COLOR_TEXT, font = self.font_title, anchor = 'mm')
        self.touch_actions.append(((0, 24, 48, 72), lambda: self.show_screen('apps')))

        app = self.selected_app
        app_root = self.get_app_root(app)
        if not os.path.exists(f'{app_root}/app.sh'):
            self.show_screen('apps')

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
        app_enabled = self.is_app_enabled(app, app_root)
        
        if app not in self.apps_size:
            app_size = shell(f"du -sh {app_root} | awk '{{print $1}}'") if USING_SHELL else '?M'
            self.apps_size[app] = app_size
        else:
            app_size = self.apps_size[app]
        
        app_status = 'Unknown'
        if not USING_SIMULATOR:
            os.system(f'chmod +x {app_root}/app.sh')
            app_status = shell(f'{app_root}/app.sh status')
            app_status = re.search('Status: ([a-z]+)', app_status).group(1)
            log(LOG_DEBUG, 'App status: ' + str(app_status))

        path = app_root
        if len(path) > 40:
            path = path[:20] + '...' + path[-20:]

        draw.text((SCREEN_WIDTH / 2, 50), app_name, fill = COLOR_TEXT, font = self.font_title, anchor = 'mm')

        current_y = 72
        draw.text((SCREEN_WIDTH / 2, current_y), 'Version: ' + app_version, fill = COLOR_SUBTITLE, font = self.font_subtitle, anchor = 'mm')

        current_y = current_y + 16
        draw.text((SCREEN_WIDTH / 2, current_y), path, fill = COLOR_SUBTITLE, font = self.font_subtitle, anchor = 'mm')

        current_y = current_y + 24
        app_description = '\n'.join(i for i in wrap(app_description, 40))
        bbox = draw.multiline_textbbox((SCREEN_WIDTH / 2, current_y), app_description)
        draw.multiline_text((SCREEN_WIDTH / 2, current_y), app_description, align = 'center', fill = COLOR_TEXT, font = self.font_subtitle, anchor = 'ma')

        current_y = bbox[3] + BUTTON_HEIGHT
        surface = (0, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH, current_y + BUTTON_HEIGHT / 2)
        draw.text((16, current_y), 'Size on disk', fill = COLOR_TEXT, font = self.font_text, anchor = 'lm')
        draw.text((SCREEN_WIDTH - 16, current_y), app_size, fill = COLOR_SUBTITLE, font = self.font_text, anchor = 'rm')

        current_y = current_y + BUTTON_HEIGHT
        surface = (0, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH, current_y + BUTTON_HEIGHT / 2)
        draw.text((16, current_y), 'Status', fill = COLOR_TEXT, font = self.font_text, anchor = 'lm')
        draw.text((SCREEN_WIDTH - 16, current_y), app_status, fill = COLOR_SUBTITLE, font = self.font_text, anchor = 'rm')

        current_y = current_y + BUTTON_HEIGHT
        surface = (0, current_y - BUTTON_HEIGHT / 2, SCREEN_WIDTH, current_y + BUTTON_HEIGHT / 2)
        if not self.dialog and self.touch_down and self.touch_down[1] >= current_y - BUTTON_HEIGHT / 2 and self.touch_down[1] <= current_y + BUTTON_HEIGHT / 2:
            draw.rectangle(surface, fill = COLOR_SECONDARY)
        draw.text((16, current_y), 'Enabled', fill = COLOR_TEXT, font = self.font_text, anchor = 'lm')
        draw.rounded_rectangle((SCREEN_WIDTH - 60, current_y - 12, SCREEN_WIDTH - 12, current_y + 12), radius = 12, fill = COLOR_PRIMARY if app_enabled else COLOR_SECONDARY)
        position = SCREEN_WIDTH - 24 if app_enabled else SCREEN_WIDTH - 48
        draw.rounded_rectangle((position - 9, current_y - 9, position + 9, current_y + 9), 9, fill = COLOR_TEXT if app_enabled else COLOR_DISABLED)
        self.touch_actions.append((surface, lambda: self.toggle_app(app, app_root)))
        
        if app_status == 'started':
            current_y = current_y + 44
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not self.dialog and self.touch_down and self.touch_down[1] >= current_y - 22 and self.touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = COLOR_SECONDARY)
            draw.text((16, current_y), 'Stop app', fill = COLOR_DANGER, font = self.font_text, anchor = 'lm')
            self.touch_actions.append((surface, lambda: self.stop_app(app, app_root)))

        if app_status == 'stopped':
            current_y = current_y + 44
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not self.dialog and self.touch_down and self.touch_down[1] >= current_y - 22 and self.touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = COLOR_SECONDARY)
            draw.text((16, current_y), 'Start app', fill = COLOR_TEXT, font = self.font_text, anchor = 'lm')
            self.touch_actions.append((surface, lambda: self.start_app(app, app_root)))

    def show_screen(self, screen):
        self.screen = screen
        self.dialog = None
        self.apps_page = 0
        self.redraw = True
    def show_dialog(self, dialog):
        self.dialog = dialog
        self.redraw = True
    def show_app(self, app):
        self.selected_app = app
        self.show_screen('app')

    def capture(self):
        framebuffer_path = '/dev/fb0'
        if USING_SIMULATOR:
            framebuffer_path = f'{RINKHALS_ROOT}/opt/rinkhals/ui/framebuffer_{KOBRA_MODEL_CODE}.bin'

        with open(framebuffer_path, 'rb') as f:
            framebuffer_bytes = f.read()

        if SCREEN_ROTATION % 180 == 90:
            framebuffer = Image.frombytes('RGBA', (SCREEN_HEIGHT, SCREEN_WIDTH), framebuffer_bytes, 'raw', 'BGRA')
        else:
            framebuffer = Image.frombytes('RGBA', (SCREEN_WIDTH, SCREEN_HEIGHT), framebuffer_bytes, 'raw', 'BGRA')

        framebuffer = framebuffer.rotate(SCREEN_ROTATION, expand = True)

        return framebuffer
    def display(self, image):
        log(LOG_DEBUG, 'Displayed image')

        if USING_SIMULATOR:
            imageTk = ImageTk.PhotoImage(image)
            globals()['__imageTk'] = imageTk

            self.window_panel.config(image = imageTk)
            self.window.update()
        else:
            image_bytes = image.rotate(-SCREEN_ROTATION, expand = True).tobytes('raw', 'BGRA')
            with open('/dev/fb0', 'wb') as fb:
                fb.write(image_bytes)
    def clear(self):
        if not USING_SIMULATOR:
            os.system('dd if=/dev/zero of=/dev/fb0 bs=480 count=1088')
    def quit(self):
        log(LOG_INFO, 'Exiting Rinkhals UI...')
        self.redraw = False

        time.sleep(0.25)
        os.kill(os.getpid(), 9)

    def on_touch_down(self, x, y):
        log(LOG_DEBUG, f'on_touch_down({x}, {y})')

        self.touch_down = [x, y]
        self.redraw = True
    def on_touch_move(self, x, y):
        #log(LOG_DEBUG, f'on_touch_move({x}, {y})')

        self.touch_down = [x, y]
        #self.redraw = True
    def on_touch_up(self, x, y):
        log(LOG_DEBUG, f'on_touch_up({x}, {y})')

        self.touch_down = None

        for action in self.touch_actions:
            if x >= action[0][0] and x <= action[0][2] and y >= action[0][1] and y <= action[0][3]:
                action[1]()
                break

        self.redraw = True
    def process_events(self, duration):
        stop = time.time_ns() + duration * 1000000

        while time.time_ns() < stop:

            if USING_SIMULATOR:
                self.window.update()

            else:
                while time.time_ns() < stop:
                    event = self.touch_device.read_one()
                    if not event:
                        break

                    # Touch position
                    if event.type == evdev.ecodes.EV_ABS:

                        # For K3 / K2P
                        if event.code == evdev.ecodes.ABS_X:
                            self.touch_last_y = (event.value - TOUCH_CALIBRATION_MIN_Y) / (TOUCH_CALIBRATION_MAX_Y - TOUCH_CALIBRATION_MIN_Y) * SCREEN_HEIGHT
                            self.touch_last_y = min(max(0, int(self.touch_last_y)), SCREEN_HEIGHT)
                            if self.touch_down_builder:
                                self.touch_down_builder[1] = self.touch_last_y
                        elif event.code == evdev.ecodes.ABS_Y:
                            self.touch_last_x = (event.value - TOUCH_CALIBRATION_MIN_X) / (TOUCH_CALIBRATION_MAX_X - TOUCH_CALIBRATION_MIN_X) * SCREEN_WIDTH
                            self.touch_last_x = min(max(0, int(self.touch_last_x)), SCREEN_WIDTH)
                            if self.touch_down_builder:
                                self.touch_down_builder[0] = self.touch_last_x

                        # For KS1
                        if event.code == evdev.ecodes.ABS_MT_POSITION_X:
                            self.touch_last_x = (event.value - TOUCH_CALIBRATION_MIN_X) / (TOUCH_CALIBRATION_MAX_X - TOUCH_CALIBRATION_MIN_X) * SCREEN_WIDTH
                            self.touch_last_x = min(max(0, int(self.touch_last_x)), SCREEN_WIDTH)
                            if self.touch_down_builder:
                                self.touch_down_builder[0] = self.touch_last_x
                        elif event.code == evdev.ecodes.ABS_MT_POSITION_Y:
                            self.touch_last_y = (event.value - TOUCH_CALIBRATION_MIN_Y) / (TOUCH_CALIBRATION_MAX_Y - TOUCH_CALIBRATION_MIN_Y) * SCREEN_HEIGHT
                            self.touch_last_y = min(max(0, int(self.touch_last_y)), SCREEN_HEIGHT)
                            if self.touch_down_builder:
                                self.touch_down_builder[1] = self.touch_last_y

                        if self.touch_down_builder and self.touch_down_builder[0] >= 0 and self.touch_down_builder[1] >= 0:
                            self.on_touch_down(self.touch_down_builder[0], self.touch_down_builder[1])
                            self.touch_down_builder = None
                        else:
                            self.on_touch_move(self.touch_last_x, self.touch_last_y)

                    # Touch action
                    elif event.code == evdev.ecodes.BTN_TOUCH: # EV_KEY
                        if time.time_ns() - self.last_screen_check > 5000000000:
                            self.last_screen_check = time.time_ns()

                            if not self.is_screen_on():
                                self.turn_on_screen()
                                return

                        if event.value == 1:
                            self.touch_down_builder = [-1, -1]
                        elif event.value == 0:
                            self.on_touch_up(self.touch_last_x, self.touch_last_y)

            time.sleep(0.1)
            if self.redraw:
                break

    def is_app_enabled(self, app, app_root = None):
        if not app_root:
            app_root = get_app_root(app)
        return (os.path.exists(f'{app_root}/.enabled') or os.path.exists(f'{RINKHALS_HOME}/apps/{app}.enabled')) and not os.path.exists(f'{app_root}/.disabled') and not os.path.exists(f'{RINKHALS_HOME}/apps/{app}.disabled')
    def get_app_root(self, app):
        user_app_root = f'{USER_APP_PATH}/{app}'
        builtin_app_root = f'{BUILTIN_APP_PATH}/{app}'

        app_root = user_app_root if os.path.exists(user_app_root) else builtin_app_root
        return app_root
    def toggle_app(self, app, app_root = None, start_stop = False):
        if USING_SIMULATOR:
            return
        if not app_root:
            app_root = self.get_app_root(app)

        enabled = self.is_app_enabled(app, app_root)

        if not os.path.exists(f'{RINKHALS_HOME}/apps'):
            os.makedirs(f'{RINKHALS_HOME}/apps')

        # If this is a built-in app, let's use HOME/apps/app.enabled
        if app_root.startswith(BUILTIN_APP_PATH):
            if enabled:
                if os.path.exists(f'{RINKHALS_HOME}/apps/{app}.enabled'):
                    os.remove(f'{RINKHALS_HOME}/apps/{app}.enabled')
                with open(f'{RINKHALS_HOME}/apps/{app}.disabled', 'wb'):
                    pass
            else:
                if os.path.exists(f'{RINKHALS_HOME}/apps/{app}.disabled'):
                    os.remove(f'{RINKHALS_HOME}/apps/{app}.disabled')
                if not os.path.exists(f'{app_root}/.enabled'):
                    with open(f'{RINKHALS_HOME}/apps/{app}.enabled', 'wb'):
                        pass

        # If this is a user app, let's use HOME/apps/app/.enabled
        else:
            if enabled:
                if os.path.exists(f'{RINKHALS_HOME}/apps/{app}.enabled'):
                    os.remove(f'{RINKHALS_HOME}/apps/{app}.enabled')
                if os.path.exists(f'{RINKHALS_HOME}/apps/{app}.disabled'):
                    os.remove(f'{RINKHALS_HOME}/apps/{app}.disabled')
                if os.path.exists(f'{RINKHALS_HOME}/apps/{app}/.enabled'):
                    os.remove(f'{RINKHALS_HOME}/apps/{app}/.enabled')
                with open(f'{RINKHALS_HOME}/apps/{app}/.disabled', 'wb'):
                    pass
            else:
                if os.path.exists(f'{RINKHALS_HOME}/apps/{app}.enabled'):
                    os.remove(f'{RINKHALS_HOME}/apps/{app}.enabled')
                if os.path.exists(f'{RINKHALS_HOME}/apps/{app}.disabled'):
                    os.remove(f'{RINKHALS_HOME}/apps/{app}.disabled')
                if os.path.exists(f'{RINKHALS_HOME}/apps/{app}/.disabled'):
                    os.remove(f'{RINKHALS_HOME}/apps/{app}/.disabled')
                with open(f'{RINKHALS_HOME}/apps/{app}/.enabled', 'wb'):
                    pass

        if enabled:
            self.stop_app(app, app_root)
        else:
            self.start_app(app, app_root)

        pass
    def start_app(self, app, app_root = None):
        if not app_root:
            app_root = self.get_app_root(app)

        log(LOG_INFO, f'Starting app {app} from {app_root}...')

        os.system(f'chmod +x {app_root}/app.sh')
        code = os.system(f'timeout -t 5 sh -c "{app_root}/app.sh start"')
        if code != 0:
            pass

        log(LOG_INFO, f'Started app {app} from {app_root}')
        redraw = True
    def stop_app(self, app, app_root = None):
        if not app_root:
            app_root = self.get_app_root(app)

        log(LOG_INFO, f'Stopping app {app} from {app_root}...')

        os.system(f'chmod +x {app_root}/app.sh')
        os.system(f'{app_root}/app.sh stop')

        log(LOG_INFO, f'Stopped app {app} from {app_root}')
        redraw = True

    def stop_rinkhals(self):
        log(LOG_INFO, 'Stopping Rinkhals...')

        screen = None

        self.clear()
        if not USING_SIMULATOR:
            os.system(RINKHALS_ROOT + '/stop.sh')
        else:
            self.quit()
    def restart_rinkhals(self):
        log(LOG_INFO, 'Restarting Rinkhals...')

        self.clear()
        if not USING_SIMULATOR:
            os.system(RINKHALS_ROOT + '/start.sh')

        self.quit()
    def disable_rinkhals(self):
        log(LOG_INFO, 'Disabling Rinkhals...')

        self.clear()
        if not USING_SIMULATOR:
            with open('/useremain/rinkhals/.disable-rinkhals', 'wb'):
                pass
            os.system('reboot')

        self.quit()


if __name__ == "__main__":
    if USING_SIMULATOR:
        program = Program()
        program.loop()
    else:
        try:
            program = Program()
            program.loop()
        except Exception as e:
            log(LOG_ERROR, str(e))
            log(LOG_ERROR, traceback.format_exc())
            os.kill(os.getpid(), 9)
