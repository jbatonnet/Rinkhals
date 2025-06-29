import os
import time
import sys
import json
import logging

import lvgl as lv
import lvgl_rinkhals as lvr

from common import *


cache_items = {}

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


DEBUG_LOGGING = os.getenv('DEBUG_LOGGING')
DEBUG_LOGGING = not not DEBUG_LOGGING

DEBUG_RENDERING = os.getenv('DEBUG_RENDERING')
DEBUG_RENDERING = not not DEBUG_RENDERING

if DEBUG_LOGGING:
    logging.getLogger().setLevel(logging.DEBUG)

lvr.set_debug_rendering(DEBUG_RENDERING)

if USING_SIMULATOR:
    PrinterInfo.simulate(
        model_code='KS1',
        model='Anycubic Kobra',
        rinkhals_version='20250617_01',
        system_version='1.2.3.4',
    )


# Detect Rinkhals root
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
ASSETS_PATH = os.path.join(SCRIPT_PATH, 'assets')

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
    KOBRA_MODEL_CODE = 'K3'
    KOBRA_VERSION = '1.2.3.4'

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
    def remove_app_property(app, property): pass
    def clear_app_properties(app): pass

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
    remove_app_property = load_tool_function('remove_app_property')
    clear_app_properties = load_tool_function('clear_app_properties')

    def are_apps_enabled():
        result = shell('. /useremain/rinkhals/.current/tools.sh && for a in $(list_apps); do echo "$a $(is_app_enabled $a)"; done')
        apps = result.splitlines()
        apps = [ a.split(' ') for a in apps ]
        return { a[0]: a[1] for a in apps }
        
# Detect LAN mode
REMOTE_MODE = 'cloud'
if os.path.isfile('/useremain/dev/remote_ctrl_mode'):
    with open('/useremain/dev/remote_ctrl_mode', 'r') as f:
        REMOTE_MODE = f.read().strip()


class RinkhalsUiApp(BaseApp):
    app_update_loop_key = 0

    def __init__(self):
        super().__init__()
        
        logging.debug(f'Root: {RINKHALS_ROOT}')
        logging.debug(f'Home: {RINKHALS_HOME}')

    def monitor_k3sysui(self):
        pid = shell("ps | grep K3SysUi | grep -v grep | awk '{print $1}'")
        if not pid:
            return
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
        import paho.mqtt.client as paho
        
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
        super().layout()
        
        if self.screen_logo:
            self.screen_logo.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.screen_logo.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self.screen_logo.set_style_pad_row(-lv.dpx(3), lv.STATE.DEFAULT)

            rinkhals_icon = lvr.image(self.screen_logo)
            rinkhals_icon.set_src(ASSETS_PATH + '/icon.png')
            rinkhals_icon.scale_to(lv.dpx(90))

            label_rinkhals = lvr.title(self.screen_logo)
            label_rinkhals.set_text('Rinkhals')
            label_rinkhals.set_style_pad_top(lv.dpx(20), lv.STATE.DEFAULT)
            label_rinkhals.set_style_pad_bottom(lv.dpx(10), lv.STATE.DEFAULT)
            
            self.screen_logo.label_model = lvr.subtitle(self.screen_logo)
            self.screen_logo.label_model.set_text('Model:')

            self.screen_logo.label_firmware = lvr.subtitle(self.screen_logo)
            self.screen_logo.label_firmware.set_text('Firmware:')

            self.screen_logo.label_version = lvr.subtitle(self.screen_logo)
            self.screen_logo.label_version.set_text('Version:')
                        
            self.screen_logo.label_disk = lvr.subtitle(self.screen_logo)
            self.screen_logo.label_disk.set_text('Disk usage: ?')

            button_exit = lvr.button_icon(self.screen_logo)
            button_exit.add_flag(lv.OBJ_FLAG.IGNORE_LAYOUT)
            button_exit.align(lv.ALIGN.TOP_LEFT, -lvr.get_global_margin(), -lvr.get_global_margin())
            button_exit.set_text('')
            button_exit.add_event_cb(lambda e: self.quit(), lv.EVENT_CODE.CLICKED, None)

        if self.screen_main:
            self.screen_main.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.screen_main.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self.screen_main.set_style_pad_row(lvr.get_global_margin(), lv.STATE.DEFAULT)

            button_apps = lvr.button(self.screen_main)
            button_apps.set_width(lv.pct(100))
            button_apps.set_text('Manage apps')
            button_apps.add_event_cb(lambda e: self.show_screen(self.screen_apps), lv.EVENT_CODE.CLICKED, None)
            
            button_ota = lvr.button(self.screen_main)
            button_ota.set_width(lv.pct(100))
            button_ota.set_text('Install & Updates')
            button_ota.add_event_cb(lambda e: self.show_screen(self.screen_ota), lv.EVENT_CODE.CLICKED, None)

            button_settings = lvr.button(self.screen_main)
            button_settings.set_width(lv.pct(100))
            button_settings.set_text('Advanced settings')
            button_settings.set_style_text_color(lvr.COLOR_DANGER, lv.STATE.DEFAULT)
            button_settings.add_event_cb(lambda e: self.show_screen(self.screen_advanced), lv.EVENT_CODE.CLICKED, None)

        # fireworks_shown = get_app_property('rinkhals_ui', 'fireworks_shown')
        # if not fireworks_shown or fireworks_shown.lower() != 'true':
        #     set_app_property('rinkhals_ui', 'fireworks_shown', 'True')
        #     self.show_fireworks()

        self.show_screen(self.screen_main)
        run_async(self.layout_async)
    def layout_async(self):
        with lvr.lock():
            self.screen_apps = lvr.panel(self.root_screen)
            if self.screen_apps:
                self.screen_apps.add_flag(lv.OBJ_FLAG.HIDDEN)
                self.screen_apps.set_size(lv.pct(100), lv.pct(100))
                self.screen_apps.set_style_pad_all(0, lv.STATE.DEFAULT)
                self.screen_apps.set_style_pad_top(lvr.get_title_bar_height(), lv.STATE.DEFAULT)

                title_bar = lvr.title_bar(self.screen_apps)
                title_bar.set_y(-lvr.get_title_bar_height())
                
                title = lvr.title(title_bar)
                title.set_text('Manage apps')
                title.center()

                icon_back = lvr.button_icon(title_bar)
                icon_back.set_align(lv.ALIGN.LEFT_MID)
                icon_back.add_event_cb(lambda e: self.show_screen(self.screen_main), lv.EVENT_CODE.CLICKED, None)
                icon_back.set_text('')

                icon_refresh = lvr.button_icon(title_bar)
                icon_refresh.add_event_cb(lambda e: self.show_screen(self.screen_apps), lv.EVENT_CODE.CLICKED, None)
                icon_refresh.set_align(lv.ALIGN.RIGHT_MID)
                icon_refresh.set_text('')

                self.screen_apps.panel_apps = None

        with lvr.lock():
            self.screen_app = lvr.panel(self.root_screen)
            if self.screen_app:
                self.screen_app.add_flag(lv.OBJ_FLAG.HIDDEN)
                self.screen_app.set_size(lv.pct(100), lv.pct(100))
                self.screen_app.set_style_pad_all(0, lv.STATE.DEFAULT)
                self.screen_app.set_style_pad_top(lvr.get_title_bar_height(), lv.STATE.DEFAULT)

                title_bar = lvr.title_bar(self.screen_app)
                title_bar.set_y(-lvr.get_title_bar_height())
                
                icon_back = lvr.button_icon(title_bar)
                icon_back.set_align(lv.ALIGN.LEFT_MID)
                icon_back.set_text('')
                icon_back.add_event_cb(lambda e: self.show_screen(self.screen_apps), lv.EVENT_CODE.CLICKED, None)

                self.screen_app.button_refresh = lvr.button_icon(title_bar)
                self.screen_app.button_refresh.set_text('')
                self.screen_app.button_refresh.set_align(lv.ALIGN.RIGHT_MID)
                
                self.screen_app.label_title = lvr.title(title_bar)
                self.screen_app.label_title.center()

                panel_app = lvr.panel(self.screen_app, flex_flow=lv.FLEX_FLOW.COLUMN, flex_align=lv.FLEX_ALIGN.CENTER)
                panel_app.set_size(lv.pct(100), lv.pct(100))

                self.screen_app.label_version = lvr.subtitle(panel_app)
                self.screen_app.label_version.set_text('Version:')
                self.screen_app.label_version.set_style_margin_ver(-lvr.get_global_margin() - lv.dpx(2), lv.STATE.DEFAULT)
                
                self.screen_app.label_path = lvr.subtitle(panel_app)
                self.screen_app.label_path.set_style_max_width(lv.pct(100), lv.STATE.DEFAULT)
                
                self.screen_app.label_description = lvr.subtitle(panel_app)
                self.screen_app.label_description.set_style_text_color(lvr.COLOR_TEXT, lv.STATE.DEFAULT)
                self.screen_app.label_description.set_width(lv.pct(100))
                self.screen_app.label_description.set_long_mode(lv.LABEL_LONG_MODE.WRAP)
                self.screen_app.label_description.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)

                panel_stats = lvr.panel(panel_app)
                panel_stats.set_width(lv.pct(100))
                panel_stats.set_flex_flow(lv.FLEX_FLOW.ROW)
                panel_stats.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
                panel_stats.set_style_pad_column(0, lv.STATE.DEFAULT)
                panel_stats.set_style_pad_hor(0, lv.STATE.DEFAULT)
                panel_stats.set_style_pad_ver(lv.dpx(15), lv.STATE.DEFAULT)

                panel_disk = lvr.panel(panel_stats, flex_flow=lv.FLEX_FLOW.COLUMN, flex_align=lv.FLEX_ALIGN.CENTER)
                panel_disk.set_style_pad_row(-lv.dpx(2), lv.STATE.DEFAULT)
                panel_disk.set_width(lv.pct(30))
                panel_disk.set_style_pad_all(0, lv.STATE.DEFAULT)

                label_disk_subtitle = lvr.subtitle(panel_disk)
                label_disk_subtitle.set_text('Disk')
                
                self.screen_app.label_disk = lvr.label(panel_disk)
                self.screen_app.label_disk.set_text('?')
                
                panel_memory = lvr.panel(panel_stats, flex_flow=lv.FLEX_FLOW.COLUMN, flex_align=lv.FLEX_ALIGN.CENTER)
                panel_memory.set_style_pad_row(-lv.dpx(2), lv.STATE.DEFAULT)
                panel_memory.set_width(lv.pct(30))
                panel_memory.set_style_pad_all(0, lv.STATE.DEFAULT)

                label_memory_subtitle = lvr.subtitle(panel_memory)
                label_memory_subtitle.set_text('Memory')
                
                self.screen_app.label_memory = lvr.label(panel_memory)
                self.screen_app.label_memory.set_text('?')
                
                panel_cpu = lvr.panel(panel_stats, flex_flow=lv.FLEX_FLOW.COLUMN, flex_align=lv.FLEX_ALIGN.CENTER)
                panel_cpu.set_style_pad_row(-lv.dpx(2), lv.STATE.DEFAULT)
                panel_cpu.set_width(lv.pct(30))
                panel_cpu.set_style_pad_all(0, lv.STATE.DEFAULT)

                label_cpu_subtitle = lvr.subtitle(panel_cpu)
                label_cpu_subtitle.set_text('CPU')
                
                self.screen_app.label_cpu = lvr.label(panel_cpu)
                self.screen_app.label_cpu.set_text('?')
                
                panel_actions = lvr.panel(panel_app)
                panel_actions.set_height(lv.SIZE_CONTENT)
                panel_actions.set_width(lv.pct(100))
                panel_actions.set_flex_flow(lv.FLEX_FLOW.ROW_REVERSE)
                panel_actions.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
                panel_actions.set_style_pad_column(lvr.get_global_margin(), lv.STATE.DEFAULT)
                panel_actions.set_style_pad_all(0, lv.STATE.DEFAULT)
                
                self.screen_app.button_qrcode = lvr.button(panel_actions)
                self.screen_app.button_qrcode.set_icon('')
                
                self.screen_app.button_settings = lvr.button(panel_actions)
                self.screen_app.button_settings.set_icon('')

                self.screen_app.button_toggle_enabled = lvr.button(panel_actions)
                self.screen_app.button_toggle_enabled.set_text('Enable/Disable app')
                self.screen_app.button_toggle_enabled.set_flex_grow(1)
                
                self.screen_app.button_toggle_started = lvr.button(panel_app)
                self.screen_app.button_toggle_started.set_text('Start/Stop app')
                self.screen_app.button_toggle_started.set_width(lv.pct(100))

        with lvr.lock():
            self.screen_app_settings = lvr.panel(self.root_screen)
            if self.screen_app_settings:
                self.screen_app_settings.add_flag(lv.OBJ_FLAG.HIDDEN)
                self.screen_app_settings.set_size(lv.pct(100), lv.pct(100))
                self.screen_app_settings.set_style_pad_all(0, lv.STATE.DEFAULT)
                self.screen_app_settings.set_style_pad_top(lvr.get_title_bar_height(), lv.STATE.DEFAULT)

                title_bar = lvr.title_bar(self.screen_app_settings)
                title_bar.set_y(-lvr.get_title_bar_height())
                
                self.screen_app_settings.label_title = lvr.title(title_bar)
                self.screen_app_settings.label_title.center()

                self.screen_app_settings.button_back = lvr.button_icon(title_bar)
                self.screen_app_settings.button_back.set_align(lv.ALIGN.LEFT_MID)
                self.screen_app_settings.button_back.set_text('')

                self.screen_app_settings.button_refresh = lvr.button_icon(title_bar)
                self.screen_app_settings.button_refresh.set_align(lv.ALIGN.RIGHT_MID)
                self.screen_app_settings.button_refresh.set_text('')

                self.screen_app_settings.panel_properties = None

        with lvr.lock():
            self.screen_advanced = lvr.panel(self.root_screen)
            if self.screen_advanced:
                self.screen_advanced.add_flag(lv.OBJ_FLAG.HIDDEN)
                self.screen_advanced.set_size(lv.pct(100), lv.pct(100))
                self.screen_advanced.set_style_pad_hor(0, lv.STATE.DEFAULT)
                self.screen_advanced.set_style_pad_top(lvr.get_title_bar_height(), lv.STATE.DEFAULT)
                
                title_bar = lvr.title_bar(self.screen_advanced)
                title_bar.add_flag(lv.OBJ_FLAG.IGNORE_LAYOUT)
                title_bar.set_y(-lvr.get_title_bar_height())

                icon_back = lvr.button_icon(title_bar)
                icon_back.set_align(lv.ALIGN.LEFT_MID)
                icon_back.set_text('')
                icon_back.add_event_cb(lambda e: self.show_screen(self.screen_main), lv.EVENT_CODE.CLICKED, None)
                
                title = lvr.title(title_bar)
                title.set_text('Advanced settings')
                title.center()

                panel_buttons = lvr.panel(self.screen_advanced, flex_flow=lv.FLEX_FLOW.COLUMN)
                panel_buttons.set_size(lv.pct(100), lv.pct(100))
                
                button_reboot = lvr.button(panel_buttons)
                button_reboot.set_width(lv.pct(100))
                button_reboot.set_text('Reboot printer')
                button_reboot.add_event_cb(lambda e: self.show_text_dialog('Are you sure you want\nto reboot your printer?', action='Yes', callback=lambda: self.reboot_printer()), lv.EVENT_CODE.CLICKED, None)
                
                button_restart = lvr.button(panel_buttons)
                button_restart.set_width(lv.pct(100))
                button_restart.set_text('Restart Rinkhals')
                button_restart.add_event_cb(lambda e: self.show_text_dialog('Are you sure you want\nto restart Rinkhals?', action='Yes', callback=lambda: self.restart_rinkhals()), lv.EVENT_CODE.CLICKED, None)
                
                button_stock = lvr.button(panel_buttons)
                button_stock.set_width(lv.pct(100))
                button_stock.set_text('Switch to stock')
                button_stock.add_event_cb(lambda e: self.show_text_dialog('Are you sure you want\nto switch to stock firmware?\n\nYou can reboot your printer\nto start Rinkhals again', action='Yes', callback=lambda: self.stop_rinkhals()), lv.EVENT_CODE.CLICKED, None)

                button_disable = lvr.button(panel_buttons)
                button_disable.set_width(lv.pct(100))
                button_disable.set_style_text_color(lvr.COLOR_DANGER, lv.STATE.DEFAULT)
                button_disable.set_text('Disable Rinkhals')
                button_disable.add_event_cb(lambda e: self.show_text_dialog('Are you sure you want\nto disable Rinkhals?\n\nYou will need to reinstall\nRinkhals to start it again', action='Yes', action_color=lvr.COLOR_DANGER, callback=lambda: self.disable_rinkhals()), lv.EVENT_CODE.CLICKED, None)

        with lvr.lock():
            self.layout_ota()
        with lvr.lock():
            self.layout_ota_rinkhals()
        with lvr.lock():
            self.layout_ota_firmware()

        with lvr.lock():
            self.modal_selection = lvr.modal(self.root_modal)
            if self.modal_selection:
                self.modal_selection.panel_selection = None

    def show_screen(self, screen):
        super().show_screen(screen)

        if screen == self.screen_main: self.show_main()
        elif screen == self.screen_apps: self.show_apps()
    def show_main(self):
        self.screen_logo.label_model.set_text(f'Model: {KOBRA_MODEL}')
        self.screen_logo.label_firmware.set_text(f'Firmware: {KOBRA_VERSION}')
        self.screen_logo.label_version.set_text(f'Version: {RINKHALS_VERSION}')
        self.screen_logo.label_disk.set_text(f'Disk usage: ?')

        def update_disk_usage(result):
            lv.lock()
            self.screen_logo.label_disk.set_text(f'Disk usage: {result}')
            lv.unlock()

        if USING_SHELL:
            shell_async(f'df -Ph {RINKHALS_ROOT} | tail -n 1 | awk \'{{print $3 " / " $2 " (" $5 ")"}}\'', update_disk_usage)
    def show_apps(self):
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
        self.screen_apps.panel_apps = lvr.panel(self.screen_apps, flex_flow=lv.FLEX_FLOW.COLUMN)
        self.screen_apps.panel_apps.set_size(lv.pct(100), lv.pct(100))

        self.app_checkboxes = {}

        def refresh_apps():
            apps = list_apps().split(' ')
            apps_enabled = are_apps_enabled()

            for app in apps:
                enabled = apps_enabled[app] == '1'

                lv.lock()
                panel_app = lvr.panel(self.screen_apps.panel_apps)
                panel_app.set_style_pad_all(0, lv.STATE.DEFAULT)
                panel_app.set_width(lv.pct(100))

                button_app = lvr.button(panel_app)
                button_app.set_width(lv.pct(100))
                button_app.set_text(app)
                button_app.set_style_pad_left(lv.dpx(15), lv.STATE.DEFAULT)
                button_app.set_style_pad_right(lv.dpx(4), lv.STATE.DEFAULT)
                button_app.set_style_text_align(lv.TEXT_ALIGN.LEFT, lv.STATE.DEFAULT)
                button_app.add_event_cb(lambda e, app=app: self.show_app(app), lv.EVENT_CODE.CLICKED, None)

                checkbox_app = lvr.checkbox(panel_app)
                checkbox_app.align(lv.ALIGN.RIGHT_MID, -lv.dpx(5), 0)
                checkbox_app.add_event_cb(lambda e, app=app, enabled=enabled: toggle_app(app, not enabled), lv.EVENT_CODE.CLICKED, None)
                checkbox_app.set_checked(enabled)
                lv.unlock()

                self.app_checkboxes[app] = checkbox_app

        run_async(refresh_apps)
    def show_app(self, app):
        self.show_screen(self.screen_app)
        
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
        app_properties = app_manifest.get('properties', []) if app_manifest else []

        self.screen_app.label_title.set_text(ellipsis(app_name, 24))
        self.screen_app.label_version.set_text(f'Version: {app_version}')
        self.screen_app.label_path.set_text(ellipsis(app_root, 36))
        self.screen_app.label_description.set_text(app_description)
        self.screen_app.label_disk.set_text('-')
        self.screen_app.label_memory.set_text('-')
        self.screen_app.label_cpu.set_text('-')

        self.screen_app.button_refresh.clear_event_cb()
        self.screen_app.button_refresh.add_event_cb(lambda e, app=app: self.show_app(app), lv.EVENT_CODE.CLICKED, None)

        self.screen_app.button_qrcode.add_flag(lv.OBJ_FLAG.HIDDEN)
        
        if len(app_properties) == 0:
            self.screen_app.button_settings.add_flag(lv.OBJ_FLAG.HIDDEN)
        else:
            self.screen_app.button_settings.remove_flag(lv.OBJ_FLAG.HIDDEN)
            self.screen_app.button_settings.clear_event_cb()
            self.screen_app.button_settings.add_event_cb(lambda e, app=app: self.show_app_settings(app), lv.EVENT_CODE.CLICKED, None)

        def update_app_size(result):
            lv.lock()
            self.screen_app.label_disk.set_text(result)
            lv.unlock()
        if USING_SHELL:
            shell_async(f"du -sh {app_root} | awk '{{print $1}}'", update_app_size)
            
        def update_info(app=app):
            app_enabled = is_app_enabled(app) == '1'
            app_status = get_app_status(app)
            app_started = app_status != 'stopped'
            
            # Update the enable app button
            with lvr.lock():
                self.screen_app.button_toggle_enabled.set_text('Disable app' if app_enabled else 'Enable app')
                self.screen_app.button_toggle_enabled.clear_event_cb()
                if app_enabled:
                    self.screen_app.button_toggle_enabled.add_event_cb(lambda e, app=app: self.disable_app(app), lv.EVENT_CODE.CLICKED, app)
                else:
                    self.screen_app.button_toggle_enabled.add_event_cb(lambda e, app=app: self.enable_app(app), lv.EVENT_CODE.CLICKED, app)
        
            # Update the start app button
            with lvr.lock():
                self.screen_app.button_toggle_started.set_text('Stop app' if app_started else 'Start app')
                self.screen_app.button_toggle_started.set_style_text_color(lvr.COLOR_DANGER if app_started else lvr.COLOR_TEXT, lv.STATE.DEFAULT)
                self.screen_app.button_toggle_started.clear_event_cb()
                if app_started:
                    self.screen_app.button_toggle_started.add_event_cb(lambda e, app=app: self.stop_app(app), lv.EVENT_CODE.CLICKED, app)
                else:
                    self.screen_app.button_toggle_started.add_event_cb(lambda e, app=app: self.start_app(app), lv.EVENT_CODE.CLICKED, app)
        
            # Refresh the QR code button if available
            with lvr.lock():
                self.screen_app.button_qrcode.add_flag(lv.OBJ_FLAG.HIDDEN)

            with lvr.lock():
                qr_properties = [ p for p in app_properties if app_properties[p]['type'] == 'qr' ]
                if qr_properties:
                    qr_property = qr_properties[0]
                    display = app_properties[qr_property].get('display')
                    content = get_app_property(app, qr_property)
                    if content:
                        self.screen_app.button_qrcode.remove_flag(lv.OBJ_FLAG.HIDDEN)
                        self.screen_app.button_qrcode.clear_event_cb()
                        self.screen_app.button_qrcode.add_event_cb(lambda e, content=content: self.show_qr_dialog(content, display), lv.EVENT_CODE.CLICKED, None)
                    else:
                        self.screen_app.button_qrcode.add_flag(lv.OBJ_FLAG.HIDDEN)
                else:
                    self.screen_app.button_qrcode.add_flag(lv.OBJ_FLAG.HIDDEN)
        def update_stats(app=app):
            import psutil

            app_pids = get_app_pids(app)
            if not app_pids:
                with lvr.lock():
                    self.screen_app.label_memory.set_text('-')
                    self.screen_app.label_cpu.set_text('-')
                return
            
            app_pids = app_pids.split(' ')
            app_memory = 0
            app_cpu = 0

            for pid in app_pids:
                try:
                    p = psutil.Process(int(pid))
                    app_memory += p.memory_info().rss / 1024 / 1024
                except:
                    continue

            if app_memory == 0:
                with lvr.lock():
                    self.screen_app.label_memory.set_text('-')
                    self.screen_app.label_cpu.set_text('-')
                return

            with lvr.lock():
                self.screen_app.label_memory.set_text(f'{round(app_memory, 1)}M')

            for pid in app_pids:
                try:
                    p = psutil.Process(int(pid))
                    app_cpu += p.cpu_percent(interval=1)
                except:
                    continue
            with lvr.lock():
                self.screen_app.label_cpu.set_text(f'{round(app_cpu, 1)}%')

        self.app_update_loop_key += 1
        def update_loop(key=self.app_update_loop_key * 1):
            while True:
                update_info()

                time.sleep(2)
                if self.screen_current != self.screen_app or key != self.app_update_loop_key:
                    break
                
                update_info()
                update_stats()

                time.sleep(2)
                if self.screen_current != self.screen_app or key != self.app_update_loop_key:
                    break
        run_async(update_loop)
    def show_app_settings(self, app):
        self.show_screen(self.screen_app_settings)
        
        app_root = get_app_root(app)

        app_manifest = None
        if os.path.exists(f'{app_root}/app.json'):
            try:
                with open(f'{app_root}/app.json', 'r') as f:
                    app_manifest = json.loads(f.read(), cls = JSONWithCommentsDecoder)
            except Exception as e:
                pass

        app_name = app_manifest.get('name') if app_manifest else app
        self.screen_app_settings.label_title.set_text(ellipsis(app_name, 24))
            
        self.screen_app_settings.button_back.clear_event_cb()
        self.screen_app_settings.button_back.add_event_cb(lambda e, app=app: self.show_app(app), lv.EVENT_CODE.CLICKED, None)

        self.screen_app_settings.button_refresh.clear_event_cb()
        self.screen_app_settings.button_refresh.add_event_cb(lambda e, app=app: self.show_app_settings(app), lv.EVENT_CODE.CLICKED, None)

        if self.screen_app_settings.panel_properties:
            self.screen_app_settings.panel_properties.delete()
        self.screen_app_settings.panel_properties = lvr.panel(self.screen_app_settings, flex_flow=lv.FLEX_FLOW.COLUMN)
        self.screen_app_settings.panel_properties.set_size(lv.pct(100), lv.pct(100))
        self.screen_app_settings.panel_properties.set_style_pad_row(0, lv.STATE.DEFAULT)
        self.screen_app_settings.panel_properties.set_style_pad_all(0, lv.STATE.DEFAULT)

        app_properties = app_manifest.get('properties', []) if app_manifest else []
        for p in app_properties:
            display_name = app_properties[p].get('display')
            type = app_properties[p].get('type')
            default = app_properties[p].get('default')
            value = get_app_property(app, p) or default

            panel_property = lvr.panel(self.screen_app_settings.panel_properties)
            panel_property.set_width(lv.pct(100))
            panel_property.set_style_min_height(lv.dpx(72), lv.STATE.DEFAULT)
            panel_property.set_style_border_side(lv.BORDER_SIDE.BOTTOM, lv.STATE.DEFAULT)
            panel_property.set_style_border_width(1, lv.STATE.DEFAULT)
            panel_property.set_style_border_color(lv.color_lighten(lvr.COLOR_BACKGROUND, 32), lv.STATE.DEFAULT)
            panel_property.set_flex_flow(lv.FLEX_FLOW.ROW_WRAP)
            panel_property.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            panel_property.set_style_pad_row(lv.dpx(2), lv.STATE.DEFAULT)

            label_property = lvr.label(panel_property)
            label_property.set_text(display_name)
            label_property.set_width(lv.pct(80))
            label_property.set_long_mode(lv.LABEL_LONG_MODE.WRAP)

            label_value = lvr.label(panel_property)
            label_value.set_style_text_color(lvr.COLOR_SUBTITLE, lv.STATE.DEFAULT)
            label_value.set_text(str(value) if value is not None else '-')
            label_value.set_width(lv.pct(80))
            label_value.set_long_mode(lv.LABEL_LONG_MODE.WRAP)

            if type in [ 'text', 'number', 'enum' ]:
                button_edit = lvr.button(panel_property)
                button_edit.set_align(lv.ALIGN.RIGHT_MID)
                button_edit.set_icon('')
                button_edit.add_flag(lv.OBJ_FLAG.IGNORE_LAYOUT)
                button_edit.set_size(lv.dpx(55), lv.dpx(55))
                button_edit.set_style_min_width(0, lv.STATE.DEFAULT)

                if type == 'text':
                    button_edit.set_state(lv.STATE.DISABLED, True)
                elif type == 'number':
                    button_edit.set_state(lv.STATE.DISABLED, True)
                elif type == 'enum':
                    options = app_properties[p].get('options')
                    if len(options) == 2 and sorted(options)[0].lower() == 'false' and sorted(options)[1].lower() == 'true':
                        value_bool = value and value.lower() == 'true'
                        
                        label_value.add_flag(lv.OBJ_FLAG.HIDDEN)
                        button_edit.delete()

                        checkbox = lvr.checkbox(panel_property)
                        checkbox.set_align(lv.ALIGN.RIGHT_MID)
                        checkbox.add_flag(lv.OBJ_FLAG.IGNORE_LAYOUT)
                        checkbox.set_checked(value_bool)
                        
                        def toggle_checkbox(e, app=app, property=p, checkbox=checkbox):
                            default = app_properties[property].get('default')
                            options = app_properties[property].get('options')
                            value = get_app_property(app, property)

                            value = (value or default or '').lower() == 'true'
                            value = not value
                            options_value = sorted(options)[0 if not value else 1]

                            set_app_property(app, property, options_value)
                            checkbox.set_checked(value)

                        checkbox.add_event_cb(toggle_checkbox, lv.EVENT_CODE.CLICKED, None)
                    else:
                        def select_option(option, app=app, property=p, default=default, label_value=label_value):
                            set_app_property(app, property, option)
                            label_value.set_text(str(option or default))

                        button_edit.add_event_cb(lambda e, options=options, select_option=select_option: self.show_selection_dialog(options, select_option), lv.EVENT_CODE.CLICKED, None)

            if type == 'report':
                if value:
                    label_property.set_width(lv.pct(100))
                    label_value.set_width(lv.pct(100))
            elif type == 'qr':
                if value:
                    label_value.set_height(lvr.font_subtitle.get_line_height())
                    label_value.set_long_mode(lv.LABEL_LONG_MODE.DOTS)

                    button_show = lvr.button(panel_property)
                    button_show.align(lv.ALIGN.RIGHT_MID, -lv.dpx(5), 0)
                    button_show.set_icon('')
                    button_show.add_flag(lv.OBJ_FLAG.IGNORE_LAYOUT)
                    button_show.set_size(lv.dpx(55), lv.dpx(55))
                    button_show.set_style_min_width(0, lv.STATE.DEFAULT)
                    button_show.add_event_cb(lambda e, display_name=display_name, value=value: self.show_qr_dialog(value, display_name), lv.EVENT_CODE.CLICKED, None)

        def reset_default(app=app):
            clear_app_properties(app)
            self.show_app_settings(app)

        button_reset = lvr.button(self.screen_app_settings.panel_properties)
        button_reset.set_style_margin_all(lvr.get_global_margin(), lv.STATE.DEFAULT)
        button_reset.set_width(lv.pct(100))
        button_reset.set_text('Reset to default')
        button_reset.add_event_cb(lambda e: reset_default(), lv.EVENT_CODE.CLICKED, None)
    def show_selection_dialog(self, options, select_callback=None):
        if self.modal_selection.panel_selection:
            self.modal_selection.panel_selection.delete()

        self.modal_selection.panel_selection = lvr.panel(self.modal_selection)
        self.modal_selection.panel_selection.set_style_pad_all(0, lv.STATE.DEFAULT)
        self.modal_selection.panel_selection.set_size(lv.pct(100), lv.SIZE_CONTENT)
        self.modal_selection.panel_selection.set_flex_flow(lv.FLEX_FLOW.ROW_WRAP)
        self.modal_selection.panel_selection.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

        label_title = lvr.title(self.modal_selection.panel_selection)
        label_title.set_text('Select an option')
        label_title.set_align(lv.ALIGN.TOP_MID)
        label_title.set_style_margin_bottom(lvr.get_global_margin(), lv.STATE.DEFAULT)

        panel_options = lvr.panel(self.modal_selection.panel_selection)
        panel_options.set_style_pad_all(0, lv.STATE.DEFAULT)
        panel_options.set_size(lv.pct(100), lv.SIZE_CONTENT)
        panel_options.set_style_max_height(lv.dpx(300), lv.STATE.DEFAULT)
        panel_options.set_flex_flow(lv.FLEX_FLOW.ROW_WRAP)
        panel_options.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

        for option in options:
            def select_option_cb(e, option=option):
                self.hide_modal()
                if select_callback:
                    select_callback(option)

            button_option = lvr.button(panel_options)
            button_option.set_text(option)
            button_option.add_event_cb(select_option_cb, lv.EVENT_CODE.CLICKED, None)

        self.root_modal.add_event_cb(lambda e: self.hide_modal(), lv.EVENT_CODE.CLICKED, None)
        self.show_modal(self.modal_selection)
    def show_fireworks(self):
        import random

        layer_top = lv.display_get_default().get_layer_top()
        layer_top.remove_flag(lv.OBJ_FLAG.SCROLLABLE)

        panel_fireworks = lvr.panel(layer_top)
        panel_fireworks.remove_flag(lv.OBJ_FLAG.SCROLLABLE)

        self.fireworks_hidden = False

        rocket_margin = lv.dpx(30)

        class Rocket:
            object = None
            color = None
            animation = None
            target = None
            stars = None
        class Star:
            animation = None
            object = None
            position = None
            velocity = None

        def make_star(rocket):
            star = Star()

            star.object = lv.obj(panel_fireworks)
            star.object.set_size(lv.dpx(8), lv.dpx(8))
            star.object.set_style_radius(lv.dpx(3), lv.STATE.DEFAULT)
            star.object.set_style_bg_color(rocket.color, lv.STATE.DEFAULT)
            star.object.set_style_border_opa(lv.OPA.TRANSP, lv.STATE.DEFAULT)
            star.object.set_pos(int(rocket.target[0]), int(rocket.target[1]))

            star.position = [rocket.target[0], rocket.target[1]]
            star.velocity = [(random.random() - 0.5) * 3, random.random() * 3]
            
            def star_animation_cb(o, value, star=star):
                star.velocity[1] -= 0.05
                star.position[0] = star.position[0] + star.velocity[0]
                star.position[1] = star.position[1] - star.velocity[1]
                star.object.set_pos(int(star.position[0]), int(star.position[1]))
                star.object.set_style_bg_opa(255 - value * 2, lv.STATE.DEFAULT)

            def star_completed_cb(e, star=star):
                star.animation.delete(None)
                star.object.delete()
            
            star.animation = lv.anim()
            star.animation.set_exec_cb(star_animation_cb)
            star.animation.set_completed_cb(star_completed_cb)
            star.animation.set_duration(1500)
            star.animation.set_values(0, 100)
            star.animation.start()
        def make_rocket():
            rocket = Rocket()

            rocket.color = lv.color_make(random.randint(64, 255), random.randint(64, 255), random.randint(64, 255))
            rocket.target = [random.randint(rocket_margin, self.screen_info.width - rocket_margin), random.randint(rocket_margin, self.screen_info.height / 2)]

            rocket.object = lv.obj(panel_fireworks)
            rocket.object.set_size(lv.dpx(6), lv.dpx(6))
            rocket.object.set_style_radius(lv.dpx(3), lv.STATE.DEFAULT)
            rocket.object.set_style_bg_color(rocket.color, lv.STATE.DEFAULT)
            rocket.object.set_style_border_opa(lv.OPA.TRANSP, lv.STATE.DEFAULT)

            def rocket_animation_cb(o, value, rocket=rocket):
                x = self.screen_info.width / 2 + (rocket.target[0] - self.screen_info.width / 2) * value / 100
                y = self.screen_info.height - (self.screen_info.height - rocket.target[1]) * value / 100
                rocket.object.set_pos(int(x), int(y))

            def rocket_completed_cb(e, rocket=rocket):
                if self.fireworks_hidden:
                    return
                rocket.stars = [ make_star(rocket) for i in range(8) ]
                rocket.target = [random.randint(rocket_margin, self.screen_info.width - rocket_margin), random.randint(rocket_margin, self.screen_info.height / 2)]
                rocket.color = lv.color_make(random.randint(64, 255), random.randint(64, 255), random.randint(64, 255))
                rocket.object.set_style_bg_color(rocket.color, lv.STATE.DEFAULT)
                rocket.animation.start()

            rocket.animation = lv.anim()
            rocket.animation.set_exec_cb(rocket_animation_cb)
            rocket.animation.set_completed_cb(rocket_completed_cb)
            rocket.animation.set_delay(random.randint(0, 2000))
            rocket.animation.set_duration(random.randint(1200, 2400))
            rocket.animation.set_values(0, 100)
            rocket.animation.set_path_cb(lv.anim_path_ease_out)
            rocket.animation.start()

        rockets = [ make_rocket() for i in range(6) ]

        colors = [
            lvr.COLOR_BACKGROUND,
            lv.color_mix(lvr.COLOR_BACKGROUND, lvr.COLOR_PRIMARY, 224)
        ]
        opas = [
            lv.OPA.TRANSP.value,
            lv.OPA.COVER.value
        ]
        fracs = [
            0,
            48
        ]

        grad_dsc = lv.grad_dsc()
        grad_dsc.init_stops(colors, opas, fracs, len(colors))
        grad_dsc.vertical_init()

        panel_message = lvr.panel(layer_top, lv.FLEX_FLOW.COLUMN)
        panel_message.set_flex_align(lv.FLEX_ALIGN.END, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        panel_message.set_size(lv.pct(100), lv.dpx(300))
        panel_message.set_align(lv.ALIGN.BOTTOM_MID)
        panel_message.remove_flag(lv.OBJ_FLAG.SCROLLABLE)
        panel_message.set_style_bg_grad(grad_dsc, lv.STATE.DEFAULT)
        panel_message.set_style_bg_opa(lv.OPA.COVER, lv.STATE.DEFAULT)

        label_text = lvr.label(panel_message)
        label_text.set_text('\n\nRinkhals has now reached 1000 community members and 256 GitHub stars.\nThank you for your interest in this project!\nHave fun priting :) Julien\n')
        label_text.set_width(lv.pct(100))
        label_text.set_style_text_font(lvr.get_font_subtitle(), lv.STATE.DEFAULT)
        label_text.set_long_mode(lv.LABEL_LONG_MODE.WRAP)
        label_text.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)

        def close_fireworks(e, panel_fireworks=panel_fireworks, panel_message=panel_message):
            self.fireworks_hidden = True
            panel_fireworks.add_flag(lv.OBJ_FLAG.HIDDEN)
            panel_message.delete()

        button_close = lvr.button(panel_message)
        button_close.set_text('Yay! Let me print now!')
        button_close.add_event_cb(close_fireworks, lv.EVENT_CODE.CLICKED, None)
        button_close.set_style_margin_bottom(lv.dpx(15), lv.STATE.DEFAULT)

    def enable_app(self, app):
        logging.info(f'Enabling {app}...')
        enable_app(app)
        self.show_app(app)
    def disable_app(self, app):
        logging.info(f'Disabling {app}...')
        disable_app(app)
        self.show_app(app)
    def start_app(self, app):
        logging.info(f'Starting {app}...')
        start_app(app, 5)
        self.show_app(app)
    def stop_app(self, app):
        logging.info(f'Stopping {app}...')
        stop_app(app)
        self.show_app(app)

    def reboot_printer(self, e=None):
        logging.info('Rebooting printer...')

        if not USING_SIMULATOR:
            self.clear()
            system('sync && reboot')

        self.quit()
    def restart_rinkhals(self, e=None):
        logging.info('Restarting Rinkhals...')

        if not USING_SIMULATOR:
            self.clear()
            system(RINKHALS_ROOT + '/start.sh')

        self.quit()
    def stop_rinkhals(self, e=None):
        logging.info('Stopping Rinkhals...')

        if not USING_SIMULATOR:
            self.clear()
            system(RINKHALS_ROOT + '/stop.sh')

        self.quit()
    def disable_rinkhals(self, e=None):
        logging.info('Disabling Rinkhals...')

        if not USING_SIMULATOR:
            self.clear()
            with open('/useremain/rinkhals/.disable-rinkhals', 'wb'):
                pass
            system('sync && reboot')

        self.quit()

    def clear(self):
        if not USING_SIMULATOR:
            system(f'dd if=/dev/zero of=/dev/fb0 bs={self.screen_info.width * 4} count={self.screen_info.height}')


if __name__ == '__main__':
    app = RinkhalsUiApp()
    app.run()
