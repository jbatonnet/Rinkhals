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


DEBUG = os.getenv('DEBUG')
DEBUG = not not DEBUG
#DEBUG = True

SIMULATED_PRINTER = 'K3'


# Setup logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Detect environment and tools
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
USING_SIMULATOR = lv.helpers.is_windows()

if USING_SIMULATOR:
    KOBRA_MODEL = 'Anycubic Kobra'
    KOBRA_MODEL_CODE = SIMULATED_PRINTER
    KOBRA_VERSION = '1.2.3.4'

    if KOBRA_MODEL_CODE == 'KS1':
        QT_QPA_PLATFORM = 'linuxfb:fb=/dev/fb0:size=800x480:rotation=180:offset=0x0:nographicsmodeswitch'
    else:
        QT_QPA_PLATFORM = 'linuxfb:fb=/dev/fb0:size=480x272:rotation=90:offset=0x0:nographicsmodeswitch'
else:
    environment = shell(f'. /useremain/rinkhals/.current/tools.sh && python -c "import os, json; print(json.dumps(dict(os.environ)))"')
    environment = json.loads(environment)

    KOBRA_MODEL_ID = environment['KOBRA_MODEL_ID']
    KOBRA_MODEL = environment['KOBRA_MODEL']
    KOBRA_MODEL_CODE = environment['KOBRA_MODEL_CODE']
    KOBRA_VERSION = environment['KOBRA_VERSION']
    QT_QPA_PLATFORM = environment['QT_QPA_PLATFORM']
        
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

        # Layout and draw
        global lvr
        import lvgl_rinkhals as lvr

        self.layout()

    def layout(self):

        self.screen_welcome = lvr.screen()
        self.screen_welcome.set_style_bg_color(lvr.COLOR_BACKGROUND, lv.STATE_DEFAULT)

        gradient_color = lv.color_mix(lvr.COLOR_BACKGROUND, lvr.COLOR_PRIMARY, 64)
        self.screen_welcome.set_style_bg_grad_color(gradient_color, lv.STATE_DEFAULT)
        self.screen_welcome.set_style_bg_grad_dir(lv.GRAD_DIR.)

        gradient = lv.grad_dsc()




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

    def layout_main(self):
        pass

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
