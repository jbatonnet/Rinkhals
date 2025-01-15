import os
import time
import sys
import json
import re
import subprocess
import threading

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

SCREEN_WIDTH = 272
SCREEN_HEIGHT = 480

SIMULATOR = False
if not os.path.exists('/dev/fb0'):
    SIMULATOR = True

if not SIMULATOR:
    import evdev

RINKHALS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
RINKHALS_HOME = f'{RINKHALS_ROOT}/home/rinkhals' if SIMULATOR else '/useremain/home/rinkhals'

BUILTIN_APP_PATH = f'{RINKHALS_ROOT}/home/rinkhals/apps'
USER_APP_PATH = f'{RINKHALS_HOME}/apps'


def log(message):
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' [rinkhals-ui] ' + message, flush = True)

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

def capture_fb():
    framebuffer_path = RINKHALS_ROOT + '/opt/rinkhals/ui/framebuffer.bin' if SIMULATOR else '/dev/fb0'

    with open(framebuffer_path, 'rb') as f:
        framebuffer_bytes = f.read()

    framebuffer = Image.frombytes('RGBA', (SCREEN_HEIGHT, SCREEN_WIDTH), framebuffer_bytes, 'raw', 'BGRA')
    framebuffer = framebuffer.rotate(90, expand = True)

    return framebuffer

def present_fb(image):
    if SIMULATOR:
        image.save(RINKHALS_ROOT + '/opt/rinkhals/ui/output.bmp')
    else:
        image_bytes = image.rotate(-90, expand = True).tobytes('raw', 'BGRA')
        with open('/dev/fb0', 'wb') as fb:
            fb.write(image_bytes)

def zero_fb():
    os.system('dd if=/dev/zero of=/dev/fb0 bs=480 count=1088')

def monitor_k3sysui():
    
    command = "ps | grep K3SysUi | grep -v grep | awk '{print $1}'"
    pid = subprocess.check_output(['sh', '-c', command])
    pid = pid.decode('utf-8').strip()
    pid = int(pid)

    log(f'Monitoring K3SysUi (PID: {pid})')

    while True:
        time.sleep(5)

        try:
            os.kill(pid, 0)
        except OSError:
            log(f'K3SysUi is gone, exiting...')
            os.kill(os.getpid(), 9)

def subscribe_mqtt():

    def mqtt_on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(f'anycubic/anycubicCloud/v1/slicer/printer/20024/{PRINTER_ID}/print')
        
        log(f'Monitoring MQTT...')

        if DEBUG:
            log('Connected to MQTT successfully')

    def mqtt_on_connect_fail(client, userdata):
        log('MQTT connection failed')

    def mqtt_on_log(client, userdata, level, buf):
        if DEBUG:
            log(buf)

    def mqtt_on_message(client, userdata, msg):
        if DEBUG:
            log('Received print event, exiting...')

        os.kill(os.getpid(), 9)

    with open('/userdata/app/gk/config/device_account.json', 'r') as f:
        json_data = f.read()
        data = json.loads(json_data)

        mqtt_username = data['username']
        mqtt_password = data['password']

    with open('/useremain/dev/device_id', 'r') as f:
        PRINTER_ID = f.read().strip()

    client = paho.Client(protocol = paho.MQTTv5)
    client.on_connect = mqtt_on_connect
    client.on_connect_fail = mqtt_on_connect_fail
    client.on_message = mqtt_on_message
    client.on_log = mqtt_on_log

    client.username_pw_set(mqtt_username, mqtt_password)
    client.connect('127.0.0.1', 2883)
    client.loop_start()


def main():
    global screen, dialog, redraw, modified_features, selected_app
    global touch_device, touch_x, touch_y, touch_down, touch_down_builder, touch_actions

    # Log information
    if DEBUG:
        log(f'Simulator: {SIMULATOR}')
        log(f'Root: {RINKHALS_ROOT}')
        log(f'Home: {RINKHALS_HOME}')

    # Subscribe to print event to exit in case of print
    if not SIMULATOR:
        subscribe_mqtt()

    # Monitor K3SysUi process to exit if it dies
    if not SIMULATOR:
        monitor_thread = threading.Thread(target = monitor_k3sysui)
        monitor_thread.start()

    # Capture previous FB
    background = capture_fb()
    draw = ImageDraw.Draw(background)
    draw.rectangle((48, 24, SCREEN_WIDTH, SCREEN_HEIGHT), fill = (0, 0, 0))
    draw.rectangle((0, 72, SCREEN_WIDTH, SCREEN_HEIGHT), fill = (0, 0, 0))

    # Load resources
    icon = Image.open(RINKHALS_ROOT + '/opt/rinkhals/ui/icon.bmp').convert('RGBA')
    icon = icon.rotate(90)

    font_path = RINKHALS_ROOT + '/opt/rinkhals/ui/AlibabaSans-Regular.ttf'
    font_title = ImageFont.truetype(font_path, 16)
    font_subtitle = ImageFont.truetype(font_path, 11)
    font_text = ImageFont.truetype(font_path, 14)

    color_primary = (0, 128, 255)
    color_secondary = (96, 96, 96)
    color_danger = (255, 64, 64)
    color_text = (255, 255, 255)
    color_subtitle = (160, 160, 160)
    color_disabled = (176, 176, 176)
    color_shadow = (96, 96, 96)

    # Main loop
    redraw = True
    screen = 'main'
    dialog = None
    modified_features = False
    selected_app = None

    if SIMULATOR:
        screen = 'main'
        selected_app = 'example'

    # Events setup
    touch_device = None
    touch_x = 0
    touch_y = 0
    touch_down = None
    touch_down_builder = None
    touch_actions = []

    if not SIMULATOR:
        touch_device = evdev.InputDevice('/dev/input/event0')

    def on_touch_down(x, y):
        global screen, dialog, redraw
        global touch_device, touch_x, touch_y, touch_down, touch_down_builder, touch_actions    

        if DEBUG:
            log(f'on_touch_down({x}, {y})')
        touch_down = (x, y)

        if not dialog and screen == 'main' and x <= 48 and y >= 24 and y <= 72:
            quit()
            return

        redraw = True

    def on_touch_up(x, y):
        global screen, dialog, redraw
        global touch_device, touch_x, touch_y, touch_down, touch_down_builder, touch_actions    

        if DEBUG:
            log(f'on_touch_up({x}, {y})')
        touch_down = None

        for action in touch_actions:
            if x >= action[0][0] and x <= action[0][2] and y >= action[0][1] and y <= action[0][3]:
                action[1]()
                break

        redraw = True

    def process_events(duration):
        global screen, dialog, redraw
        global touch_device, touch_x, touch_y, touch_down, touch_down_builder, touch_actions    

        if SIMULATOR:
            time.sleep(duration)
        else:
            stop = time.time_ns() + duration * 1000000

            MIN_X = 235
            MAX_X = 25
            MIN_Y = 460
            MAX_Y = 25
            
            while time.time_ns() < stop and not redraw:
                event = touch_device.read_one()
                if not event:
                    time.sleep(0.1)
                    continue

                if event.type == evdev.ecodes.EV_ABS:
                    if event.code == evdev.ecodes.ABS_X:
                        #log(f'Raw X: {event.value}')
                        touch_y = (event.value - MIN_Y) / (MAX_Y - MIN_Y) * SCREEN_HEIGHT
                        touch_y = min(max(0, int(touch_y)), SCREEN_HEIGHT)
                        if touch_down_builder:
                            touch_down_builder[1] = touch_y
                    elif event.code == evdev.ecodes.ABS_Y:
                        #log(f'Raw Y: {event.value}')
                        touch_x = (event.value - MIN_X) / (MAX_X - MIN_X) * SCREEN_WIDTH
                        touch_x = min(max(0, int(touch_x)), SCREEN_WIDTH)
                        if touch_down_builder:
                            touch_down_builder[0] = touch_x

                    if touch_down_builder and touch_down_builder[0] >= 0 and touch_down_builder[1] >= 0:
                        on_touch_down(touch_down_builder[0], touch_down_builder[1])
                        touch_down_builder = None

                elif event.code == evdev.ecodes.BTN_TOUCH: # EV_KEY
                    if event.value == 1:
                        touch_down_builder = [-1, -1]
                    elif event.value == 0:
                        on_touch_up(touch_x, touch_y)

                if time.time_ns() > stop:
                    break

    def show_screen(new_screen):
        global screen, dialog, redraw
        global touch_device, touch_x, touch_y, touch_down, touch_down_builder, touch_actions    

        old_screen = screen
        screen = new_screen
        dialog = None

        if new_screen == 'main':
            touch_device.ungrab()
        elif old_screen == 'main':
            try:
                touch_device.grab()
            except:
                pass

        redraw = True

    def show_dialog(new_dialog):
        global screen, dialog, redraw
        global touch_device, touch_x, touch_y, touch_down, touch_down_builder, touch_actions    

        dialog = new_dialog

        if screen == 'main':
            if new_dialog:
                touch_device.grab()
            else:
                touch_device.ungrab()

        redraw = True

    def show_app(app):
        global screen, dialog, redraw, selected_app
        global touch_device, touch_x, touch_y, touch_down, touch_down_builder, touch_actions    

        log('Selecting app ' + app)

        selected_app = app
        show_screen('app')

    def toggle_feature(enabled, disable_file):
        global modified_features

        if enabled:
            if os.path.exists(disable_file):
                try:
                    os.remove(disable_file)
                except:
                    pass
        else:
            with open(disable_file, 'wb'):
                pass

        modified_features = True

    def get_app_root(app):
        user_app_root = f'{USER_APP_PATH}/{app}'
        builtin_app_root = f'{BUILTIN_APP_PATH}/{app}'

        app_root = user_app_root if os.path.exists(user_app_root) else builtin_app_root
        return app_root

    def is_app_enabled(app, app_root = None):
        if not app_root:
            app_root = get_app_root(app)
        return (os.path.exists(f'{app_root}/.enabled') or os.path.exists(f'{RINKHALS_HOME}/apps/{app}.enabled')) and not os.path.exists(f'{app_root}/.disabled') and not os.path.exists(f'{RINKHALS_HOME}/apps/{app}.disabled')

    def toggle_app(app, app_root = None):
        global screen, dialog, redraw

        if not app_root:
            app_root = get_app_root(app)

        enabled = is_app_enabled(app, app_root)

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

        # Now start/stop the app
        if enabled:
            stop_app(app, app_root)
        else:
            start_app(app, app_root)

        redraw = True

    def start_app(app, app_root = None):
        if not app_root:
            app_root = get_app_root(app)

        os.system(f'chmod +x {app_root}/app.sh')
        os.system(f'{app_root}/app.sh start')

        redraw = True

    def stop_app(app, app_root = None):
        if not app_root:
            app_root = get_app_root(app)

        os.system(f'chmod +x {app_root}/app.sh')
        os.system(f'{app_root}/app.sh stop')
        redraw = True

    def stop_rinkhals():
        global screen, dialog, redraw
 
        screen = None

        zero_fb()
        os.system(RINKHALS_ROOT + '/stop.sh')

    def restart_rinkhals():
        global screen, dialog, redraw
 
        zero_fb()
        os.system(RINKHALS_ROOT + '/start.sh')

        quit()

    def quit():
        global screen, dialog, redraw

        log('Exiting Rinkhals UI...')

        screen = None
        redraw = False

        os.kill(os.getpid(), 9)

    while True:
        if not redraw:
            process_events(250)
            continue

        buffer = background
        touch_actions = []

        if screen == 'main':
            firmware = '2.3.5.3'
            if os.path.isfile('/useremain/dev/version'):
                with open('/useremain/dev/version') as f:
                    firmware = f.read().strip()
            
            version = os.path.basename(RINKHALS_ROOT)
            if version == '4-rinkhals':
                version = 'dev'

            root = RINKHALS_ROOT
            if len(root) > 32:
                root = root[:16] + '...' + root[-16:]

            home = RINKHALS_HOME
            if len(home) > 32:
                home = home[:16] + '...' + home[-16:]

            if SIMULATOR:
                disk_usage = '?G / ?G (?%)'
            else:
                command = 'df -Ph /useremain | tail -n 1 | awk \'{print $3 " / " $2 " (" $5 ")"}\''
                disk_usage = subprocess.check_output(['sh', '-c', command])
                disk_usage = disk_usage.decode('utf-8').strip()

            buffer = background.copy()
            buffer.alpha_composite(icon, (104, 56))

            draw = ImageDraw.Draw(buffer)

            draw.text((SCREEN_WIDTH / 2, 144), 'Rinkhals', fill = color_text, font = font_title, anchor = 'mm')
            draw.text((SCREEN_WIDTH / 2, 168), 'Firmware: ' + firmware, fill = color_subtitle, font = font_subtitle, anchor = 'mm')
            draw.text((SCREEN_WIDTH / 2, 184), 'Version: ' + version, fill = color_subtitle, font = font_subtitle, anchor = 'mm')
            draw.text((SCREEN_WIDTH / 2, 200), 'Root: ' + root, fill = color_subtitle, font = font_subtitle, anchor = 'mm')
            draw.text((SCREEN_WIDTH / 2, 216), 'Home: ' + home, fill = color_subtitle, font = font_subtitle, anchor = 'mm')
            draw.text((SCREEN_WIDTH / 2, 232), 'Disk usage: ' + disk_usage, fill = color_subtitle, font = font_subtitle, anchor = 'mm')

            current_y = 280
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = color_secondary)
            draw.text((16, current_y), 'Manage features', fill = color_text, font = font_text, anchor = 'lm')
            draw.text((SCREEN_WIDTH - 16, current_y), '>', fill = color_text, font = font_text, anchor = 'rm')
            touch_actions.append((surface, lambda: show_screen('features')))

            # current_y = current_y + 44
            # surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            # if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
            #     draw.rectangle(surface, fill = color_secondary)
            # draw.text((16, current_y), 'Clean storage (logs, old files, ...)', fill = color_text, font = font_text, anchor = 'lm')
            # touch_actions.append((surface, lambda: show_dialog('confirm-cleanup')))

            current_y = current_y + 44
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = color_secondary)
            draw.text((16, current_y), 'Manage apps', fill = color_text, font = font_text, anchor = 'lm')
            draw.text((SCREEN_WIDTH - 16, current_y), '>', fill = color_text, font = font_text, anchor = 'rm')
            touch_actions.append((surface, lambda: show_screen('apps')))

            current_y = current_y + 44
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = color_secondary)
            draw.text((16, current_y), 'Stop Rinkhals', fill = color_text, font = font_text, anchor = 'lm')
            touch_actions.append((surface, lambda: show_dialog('confirm-stop-rinkhals')))

            # current_y = current_y + 44
            # surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            # if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
            #     draw.rectangle(surface, fill = color_secondary)
            # draw.text((16, current_y), 'Restart Rinkhals', fill = color_text, font = font_text, anchor = 'lm')
            # touch_actions.append((surface, lambda: show_dialog('confirm-restart-rinkhals')))

            current_y = current_y + 44
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = color_secondary)
            draw.text((16, current_y), 'Disable Rinkhals', fill = color_danger, font = font_text, anchor = 'lm')
            touch_actions.append((surface, lambda: show_dialog('confirm-disable-rinkhals')))

            if dialog == 'confirm-cleanup':
                dialog_height = 144
                dialog_top = (SCREEN_HEIGHT - dialog_height) / 2
                button_top = dialog_top + dialog_height - 56

                draw.rounded_rectangle((32, dialog_top, SCREEN_WIDTH - 32, dialog_top + dialog_height), radius = 16, fill = color_secondary)
                draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 16), 'Are you sure you want to\nclean old logs and files?', align = 'center', fill = color_text, font = font_text, anchor = 'ma')
                draw.rounded_rectangle((72, button_top, SCREEN_WIDTH - 72, button_top + 36), radius = 8, fill = color_primary)
                draw.text((SCREEN_WIDTH / 2, button_top + 18), 'Yes', fill = color_text, font = font_text, anchor = 'mm')

                touch_actions = []
                touch_actions.append(((72, button_top, SCREEN_WIDTH - 72, button_top + 36), lambda: show_dialog(None)))
                touch_actions.append(((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), lambda: show_dialog(None)))

            elif dialog == 'confirm-stop-rinkhals':
                dialog_height = 212
                dialog_top = (SCREEN_HEIGHT - dialog_height) / 2
                button_top = dialog_top + dialog_height - 56

                draw.rounded_rectangle((32, dialog_top, SCREEN_WIDTH - 32, dialog_top + dialog_height), radius = 16, fill = color_secondary)
                draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 16), 'Are you sure you want\nto stop Rinkhals?', align = 'center', fill = color_text, font = font_text, anchor = 'ma')
                draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 72), 'You will need to reboot\nyour printer in order to\nstart Rinkhals again', align = 'center', fill = color_text, font = font_text, anchor = 'ma')
                draw.rounded_rectangle((72, button_top, SCREEN_WIDTH - 72, button_top + 36), radius = 8, fill = color_primary)
                draw.text((SCREEN_WIDTH / 2, button_top + 18), 'Yes', fill = color_text, font = font_text, anchor = 'mm')

                touch_actions = []
                touch_actions.append(((72, button_top, SCREEN_WIDTH - 72, button_top + 36), lambda: stop_rinkhals()))
                touch_actions.append(((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), lambda: show_dialog(None)))

            elif dialog == 'confirm-restart-rinkhals':
                dialog_height = 144
                dialog_top = (SCREEN_HEIGHT - dialog_height) / 2
                button_top = dialog_top + dialog_height - 56

                draw.rounded_rectangle((32, dialog_top, SCREEN_WIDTH - 32, dialog_top + dialog_height), radius = 16, fill = color_secondary)
                draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 16), 'Are you sure you want\nto restart Rinkhals?', align = 'center', fill = color_text, font = font_text, anchor = 'ma')
                draw.rounded_rectangle((72, button_top, SCREEN_WIDTH - 72, button_top + 36), radius = 8, fill = color_primary)
                draw.text((SCREEN_WIDTH / 2, button_top + 18), 'Yes', fill = color_text, font = font_text, anchor = 'mm')

                touch_actions = []
                touch_actions.append(((72, button_top, SCREEN_WIDTH - 72, button_top + 36), lambda: restart_rinkhals()))
                touch_actions.append(((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), lambda: show_dialog(None)))


            elif dialog == 'confirm-disable-rinkhals':
                dialog_height = 196
                dialog_top = (SCREEN_HEIGHT - dialog_height) / 2
                button_top = dialog_top + dialog_height - 56

                draw.rounded_rectangle((32, dialog_top, SCREEN_WIDTH - 32, dialog_top + dialog_height), radius = 16, fill = color_secondary)
                draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 16), 'Are you sure you want\nto disable Rinkhals?', align = 'center', fill = color_text, font = font_text, anchor = 'ma')
                draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 72), 'You will need to reinstall\nRinkhals to start it again', align = 'center', fill = color_text, font = font_text, anchor = 'ma')
                draw.rounded_rectangle((72, button_top, SCREEN_WIDTH - 72, button_top + 36), radius = 8, fill = color_danger)
                draw.text((SCREEN_WIDTH / 2, button_top + 18), 'Yes', fill = color_text, font = font_text, anchor = 'mm')

                touch_actions = []
                touch_actions.append(((72, button_top, SCREEN_WIDTH - 72, button_top + 36), lambda: show_dialog(None)))
                touch_actions.append(((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), lambda: show_dialog(None)))

        elif screen == 'features':
            if modified_features:
                touch_actions.append(((0, 24, 48, 72), lambda: show_dialog('features-restart')))
            else:
                touch_actions.append(((0, 24, 48, 72), lambda: show_screen('main')))

            feature_moonraker = not os.path.isfile(RINKHALS_HOME + '/.disable-moonraker')
            feature_mjpgstreamer = not os.path.isfile(RINKHALS_HOME + '/.disable-mjpgstreamer')
            feature_nginx = not os.path.isfile(RINKHALS_HOME + '/.disable-nginx')

            buffer = background.copy()
            draw = ImageDraw.Draw(buffer)

            draw.text((SCREEN_WIDTH / 2, 50), 'Manage features', fill = color_text, font = font_title, anchor = 'mm')

            current_y = 96
            checked = feature_moonraker

            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = color_secondary)
            draw.text((16, current_y), 'Enable Moonraker', fill = color_text, font = font_text, anchor = 'lm')
            draw.rounded_rectangle((SCREEN_WIDTH - 60, current_y - 12, SCREEN_WIDTH - 12, current_y + 12), radius = 12, fill = color_primary if checked else color_secondary)
            position = SCREEN_WIDTH - 24 if checked else SCREEN_WIDTH - 48
            draw.rounded_rectangle((position - 9, current_y - 9, position + 9, current_y + 9), 9, fill = color_text if checked else color_disabled)
            touch_actions.append((surface, lambda: toggle_feature(not feature_moonraker, RINKHALS_HOME + '/.disable-moonraker')))

            current_y = current_y + 44
            enabled = feature_moonraker
            checked = feature_moonraker and feature_mjpgstreamer
            
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not dialog and enabled and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = color_secondary)
            draw.text((28, current_y), 'Camera in Moonraker', fill = color_text if enabled else color_disabled, font = font_text, anchor = 'lm')
            draw.rounded_rectangle((SCREEN_WIDTH - 60, current_y - 12, SCREEN_WIDTH - 12, current_y + 12), radius = 12, fill = color_primary if checked else color_secondary)
            position = SCREEN_WIDTH - 24 if checked else SCREEN_WIDTH - 48
            draw.rounded_rectangle((position - 9, current_y - 9, position + 9, current_y + 9), 9, fill = color_text if checked else color_disabled)
            touch_actions.append((surface, lambda: toggle_feature(not feature_mjpgstreamer, RINKHALS_HOME + '/.disable-mjpgstreamer')))
 
            current_y = current_y + 44
            enabled = feature_moonraker
            checked = feature_moonraker and feature_nginx
            
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not dialog and enabled and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = color_secondary)
            draw.text((28, current_y), 'Mainsail and Fluidd', fill = color_text if enabled else color_disabled, font = font_text, anchor = 'lm')
            draw.rounded_rectangle((SCREEN_WIDTH - 60, current_y - 12, SCREEN_WIDTH - 12, current_y + 12), radius = 12, fill = color_primary if checked else color_secondary)
            position = SCREEN_WIDTH - 24 if checked else SCREEN_WIDTH - 48
            draw.rounded_rectangle((position - 9, current_y - 9, position + 9, current_y + 9), 9, fill = color_text if checked else color_disabled)
            touch_actions.append((surface, lambda: toggle_feature(not feature_nginx, RINKHALS_HOME + '/.disable-nginx')))

            if dialog == 'features-restart':
                dialog_height = 144
                dialog_top = (SCREEN_HEIGHT - dialog_height) / 2
                button_top = dialog_top + dialog_height - 56

                draw.rounded_rectangle((32, dialog_top, SCREEN_WIDTH - 32, dialog_top + dialog_height), radius = 16, fill = color_secondary)
                draw.multiline_text((SCREEN_WIDTH / 2, dialog_top + 16), 'You toggled some feature\nRinkhals needs to restart', align = 'center', fill = color_text, font = font_text, anchor = 'ma')
                draw.rounded_rectangle((72, button_top, SCREEN_WIDTH - 72, button_top + 36), radius = 8, fill = color_primary)
                draw.text((SCREEN_WIDTH / 2, button_top + 18), 'Restart', fill = color_text, font = font_text, anchor = 'mm')

                touch_actions = []
                touch_actions.append(((72, button_top, SCREEN_WIDTH - 72, button_top + 36), lambda: restart_rinkhals()))
                touch_actions.append(((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), lambda: show_screen('main')))

        elif screen == 'apps':
            touch_actions.append(((0, 24, 48, 72), lambda: show_screen('main')))

            log(f'Looking for apps in {BUILTIN_APP_PATH} and {USER_APP_PATH}...')

            builtin_apps = next(os.walk(BUILTIN_APP_PATH))[1] if os.path.exists(BUILTIN_APP_PATH) else []
            user_apps = next(os.walk(USER_APP_PATH))[1] if os.path.exists(USER_APP_PATH) else []

            apps = builtin_apps + user_apps
            apps = list(dict.fromkeys(apps))

            buffer = background.copy()
            draw = ImageDraw.Draw(buffer)

            draw.text((SCREEN_WIDTH / 2, 50), 'Manage apps', fill = color_text, font = font_title, anchor = 'mm')

            current_y = 96

            for app in apps:

                user_app_root = f'{USER_APP_PATH}/{app}'
                builtin_app_root = f'{BUILTIN_APP_PATH}/{app}'

                app_root = user_app_root if os.path.exists(user_app_root) else builtin_app_root

                if not os.path.exists(f'{app_root}/app.sh') or not os.path.exists(f'{app_root}/app.json'):
                    continue

                log(f'- Found {app} in {app_root}')

                app_manifest = None
                try:
                    with open(f'{app_root}/app.json', 'r') as f:
                        app_manifest = json.loads(f.read(), cls = JSONWithCommentsDecoder)
                except Exception as e:
                    if not SIMULATOR:
                        continue

                app_schema_version = app_manifest['$version']
                if app_schema_version != '1':
                    continue

                app_name = app_manifest['name'] if app_manifest and 'name' in app_manifest else app
                app_description = app_manifest['description'] if app_manifest and 'description' in app_manifest else ''
                app_version = app_manifest['version'] if app_manifest and 'version' in app_manifest else ''

                app_enabled = is_app_enabled(app, app_root)
                    
                surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
                if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                    draw.rectangle(surface, fill = color_secondary)
                draw.text((16, current_y), app_name + (f' ({app_version})' if app_version else ''), fill = color_text, font = font_text, anchor = 'lm')
                #draw.text((16, current_y + 9), description, fill = color_text, font = font_subtitle, anchor = 'lm')
                draw.rounded_rectangle((SCREEN_WIDTH - 60, current_y - 12, SCREEN_WIDTH - 12, current_y + 12), radius = 12, fill = color_primary if app_enabled else color_secondary)
                position = SCREEN_WIDTH - 24 if app_enabled else SCREEN_WIDTH - 48
                draw.rounded_rectangle((position - 9, current_y - 9, position + 9, current_y + 9), 9, fill = color_text if app_enabled else color_disabled)

                touch_actions.append(((0, current_y - 22, SCREEN_WIDTH - 60, current_y + 22), lambda app = app: show_app(app)))
                touch_actions.append(((SCREEN_WIDTH - 60, current_y - 22, SCREEN_WIDTH, current_y + 22), lambda app = app: toggle_app(app)))

                current_y = current_y + 44

        elif screen == 'app':
            touch_actions.append(((0, 24, 48, 72), lambda: show_screen('apps')))

            app = selected_app
            app_root = get_app_root(selected_app)
            if not os.path.exists(f'{app_root}/app.sh'):
                show_screen('apps')

            app_manifest = None
            if os.path.exists(f'{app_root}/app.json'):
                try:
                    with open(f'{app_root}/app.json', 'r') as f:
                        app_manifest = json.loads(f.read(), cls = JSONWithCommentsDecoder)
                except Exception as e:
                    pass

            app_name = app_manifest['name'] if app_manifest and 'name' in app_manifest else app
            app_description = app_manifest['description'] if app_manifest and 'description' in app_manifest else ''
            app_version = app_manifest['version'] if app_manifest and 'version' in app_manifest else ''

            app_size = '?M'
            if not SIMULATOR:
                command = f"du -sh {app_root} | awk '{{print $1}}'"
                app_size = subprocess.check_output(['sh', '-c', command])
                app_size = app_size.decode('utf-8').strip()

            app_enabled = is_app_enabled(app, app_root)
            
            app_status = 'Unknown'
            if not SIMULATOR:
                os.system(f'chmod +x {app_root}/app.sh')
                command = f'{app_root}/app.sh status'
                app_status = subprocess.check_output(['sh', '-c', command])
                app_status = app_status.decode('utf-8').strip()
                app_status = re.search('Status: ([a-z]+)', app_status).group(1)

                log('App status: ' + str(app_status))

            path = app_root
            if len(path) > 40:
                path = path[:20] + '...' + path[-20:]

            buffer = background.copy()
            draw = ImageDraw.Draw(buffer)

            draw.text((SCREEN_WIDTH / 2, 50), app_name, fill = color_text, font = font_title, anchor = 'mm')

            current_y = 72
            draw.text((SCREEN_WIDTH / 2, current_y), 'Version: ' + app_version, fill = color_subtitle, font = font_subtitle, anchor = 'mm')

            current_y = current_y + 16
            draw.text((SCREEN_WIDTH / 2, current_y), path, fill = color_subtitle, font = font_subtitle, anchor = 'mm')

            current_y = current_y + 24
            app_description = '\n'.join(i for i in wrap(app_description, 40))
            bbox = draw.multiline_textbbox((SCREEN_WIDTH / 2, current_y), app_description)
            draw.multiline_text((SCREEN_WIDTH / 2, current_y), app_description, align = 'center', fill = color_text, font = font_subtitle, anchor = 'ma')

            current_y = bbox[3] + 44
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = color_secondary)
            draw.text((16, current_y), 'Size on disk', fill = color_text, font = font_text, anchor = 'lm')
            draw.text((SCREEN_WIDTH - 16, current_y), app_size, fill = color_subtitle, font = font_text, anchor = 'rm')

            current_y = current_y + 44
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = color_secondary)
            draw.text((16, current_y), 'Status', fill = color_text, font = font_text, anchor = 'lm')
            draw.text((SCREEN_WIDTH - 16, current_y), app_status, fill = color_subtitle, font = font_text, anchor = 'rm')

            current_y = current_y + 44
            surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
            if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                draw.rectangle(surface, fill = color_secondary)
            draw.text((16, current_y), 'Enabled', fill = color_text, font = font_text, anchor = 'lm')
            draw.rounded_rectangle((SCREEN_WIDTH - 60, current_y - 12, SCREEN_WIDTH - 12, current_y + 12), radius = 12, fill = color_primary if app_enabled else color_secondary)
            position = SCREEN_WIDTH - 24 if app_enabled else SCREEN_WIDTH - 48
            draw.rounded_rectangle((position - 9, current_y - 9, position + 9, current_y + 9), 9, fill = color_text if app_enabled else color_disabled)
            touch_actions.append((surface, lambda: toggle_app(app, app_root)))

            if app_status == 'started':
                current_y = current_y + 44
                surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
                if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                    draw.rectangle(surface, fill = color_secondary)
                draw.text((16, current_y), 'Stop app', fill = color_danger, font = font_text, anchor = 'lm')
                touch_actions.append((surface, lambda: stop_app(app, app_root)))

            if app_status == 'stopped':
                current_y = current_y + 44
                surface = (0, current_y - 22, SCREEN_WIDTH, current_y + 22)
                if not dialog and touch_down and touch_down[1] >= current_y - 22 and touch_down[1] <= current_y + 22:
                    draw.rectangle(surface, fill = color_secondary)
                draw.text((16, current_y), 'Start app', fill = color_text, font = font_text, anchor = 'lm')
                touch_actions.append((surface, lambda: start_app(app, app_root)))

        if not screen:
            break

        if DEBUG:
            log('Present')
        present_fb(buffer)
        redraw = False

        if SIMULATOR:
            break


if __name__ == "__main__":
    main()
    os.kill(os.getpid(), 9)
