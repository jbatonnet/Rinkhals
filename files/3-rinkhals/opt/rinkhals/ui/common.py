import time
import os
import sys
import json
import re
import random
import logging

from enum import Enum
from datetime import datetime, timezone

import lvgl as lv
import lvgl_rinkhals as lvr


class JSONWithCommentsDecoder(json.JSONDecoder):
    def __init__(self, **kwgs):
        super().__init__(**kwgs)
    def decode(self, s: str):
        regex = r"""("(?:\\"|[^"])*?")|(\/\*(?:.|\s)*?\*\/|\/\/.*)"""
        s = re.sub(regex, r"\1", s)  # , flags = re.X | re.M)
        return super().decode(s)


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


ORIGINAL_LD_LIBRARY_PATH = os.environ.get('LD_LIBRARY_PATH', '')
LD_LIBRARY_PATH = ORIGINAL_LD_LIBRARY_PATH.split(':')
LD_LIBRARY_PATH = [ p for p in LD_LIBRARY_PATH if not p.startswith('/tmp') ]
LD_LIBRARY_PATH = ':'.join(LD_LIBRARY_PATH)


def system(command):
    command = command.replace('\\', '\\\\')

    os.environ['LD_LIBRARY_PATH'] = LD_LIBRARY_PATH
    result = os.system(command)
    os.environ['LD_LIBRARY_PATH'] = ORIGINAL_LD_LIBRARY_PATH

    logging.info(f'System "{command}"')
    return result
def shell(command):
    command = command.replace('\\', '\\\\')
    os.environ['LD_LIBRARY_PATH'] = LD_LIBRARY_PATH

    if USING_SIMULATOR:
        import subprocess
        result = subprocess.check_output(['sh', '-c', command])
        result = result.decode().strip()
    else:
        os.makedirs('/tmp/rinkhals', exist_ok=True)
        temp_output = f'/tmp/rinkhals/output-{random.randint(1000, 9999)}'

        os.system(f'{command} > {temp_output}')
        if os.path.exists(temp_output):
            with open(temp_output) as f:
                result = f.read().strip()
            os.remove(temp_output)
        else:
            result = ''

    logging.info(f'Shell "{command}" => "{result}"')
    os.environ['LD_LIBRARY_PATH'] = ORIGINAL_LD_LIBRARY_PATH
    return result
def shell_async(command, callback):
    def thread():
        result = shell(command)
        if callback:
            callback(result)
    import threading
    t = threading.Thread(target=thread)
    t.start()
def run_async(callback):
    import threading
    t = threading.Thread(target=callback)
    t.start()

def hash(path):
    if not os.path.exists(path):
        return None
    
    import hashlib
    md5 = hashlib.md5()

    with open(path, 'rb') as f:
        while True:
            data = f.read(8192)
            if not data:
                break
            md5.update(data)

    return md5.hexdigest()


################
# Printer environment detection

RINKHALS_BASE = '/useremain/rinkhals'

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
ASSETS_PATH = os.path.join(SCRIPT_PATH, 'assets')

USING_SIMULATOR = lv.helpers.is_windows()

SIMULATED_MODEL = 'Anycubic Kobra'
SIMULATED_MODEL_CODE = 'K3'
SIMULATED_RINKHALS_VERSION = '20250424_01'
SIMULATED_FIRMWARE_VERSION = '1.2.3.4'

class PrinterInfo:
    model_code: int
    model: int

    def get():
        printer_info = PrinterInfo()
        model_id = None
        
        if USING_SIMULATOR:
            global SIMULATED_MODEL
            global SIMULATED_MODEL_CODE

            printer_info.model = SIMULATED_MODEL
            printer_info.model_code = SIMULATED_MODEL_CODE

            return printer_info

        try:
            with open('/userdata/app/gk/config/api.cfg', 'r') as f:
                api_config = json.loads(f.read())

            model_id = api_config['cloud']['modelId']

            if model_id == '20021':
                printer_info.model = 'Anycubic Kobra 2 Pro'
                printer_info.model_code = 'K2P'
            elif model_id == '20024':
                printer_info.model = 'Anycubic Kobra 3'
                printer_info.model_code = 'K3'
            elif model_id == '20025':
                printer_info.model = 'Anycubic Kobra S1'
                printer_info.model_code = 'KS1'
            elif model_id == '20026':
                printer_info.model = 'Anycubic Kobra 3 Max'
                printer_info.model_code = 'K3M'
        except:
            return None
        
        return printer_info
    def simulate(model_code, model, rinkhals_version, system_version):
        global SIMULATED_MODEL
        global SIMULATED_MODEL_CODE
        global SIMULATED_RINKHALS_VERSION
        global SIMULATED_FIRMWARE_VERSION

        SIMULATED_MODEL = model
        SIMULATED_MODEL_CODE = model_code
        SIMULATED_RINKHALS_VERSION = rinkhals_version
        SIMULATED_FIRMWARE_VERSION = system_version

class ScreenInfo:
    width: int
    height: int
    rotation: int
    dpi: int
    touch_calibration: tuple[int, int, int, int]

    def get():
        printer_info = PrinterInfo.get()

        QT_QPA_PLATFORM = os.environ.get('QT_QPA_PLATFORM')

        if USING_SIMULATOR:
            if printer_info.model_code == 'KS1':
                QT_QPA_PLATFORM = 'linuxfb:fb=/dev/fb0:size=800x480:rotation=180:offset=0x0:nographicsmodeswitch'
            else:
                QT_QPA_PLATFORM = 'linuxfb:fb=/dev/fb0:size=480x272:rotation=90:offset=0x0:nographicsmodeswitch'

        if not QT_QPA_PLATFORM:
            return None

        screen_options = QT_QPA_PLATFORM.split(':')
        screen_options = [ o.split('=') for o in screen_options ]
        screen_options = { o[0]: o[1] if len(o) > 1 else None for o in screen_options }

        resolution_match = re.search('^([0-9]+)x([0-9]+)$', screen_options['size'])

        info = ScreenInfo()
        info.width = int(resolution_match[1])
        info.height = int(resolution_match[2])
        info.rotation = int(screen_options['rotation'])
        info.dpi = 130

        if info.rotation % 180 == 90:
            temp = info.width
            info.width = info.height
            info.height = temp

        if printer_info.model_code == 'KS1':
            info.touch_calibration = [0, 0, 800, 480]
            info.dpi = 180
        else:
            info.touch_calibration = [25, 235, 460, 25]

        return info


################
# Rinkhals update management

class RinkhalsVersion:
    version: str
    path: str
    test: bool
    date: int
    changes: str
    md5: str
    url: str
    supported_firmwares: list[str]

class Rinkhals:
    def get_current_path():
        try:
            version_file = os.path.join(RINKHALS_BASE, '.version')
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    current_path = f.read().strip()

            return os.path.join(RINKHALS_BASE, current_path)
        except:
            return None
    def get_current_version():
        if USING_SIMULATOR:
            current = RinkhalsVersion()
            current.path = os.path.join(RINKHALS_BASE, SIMULATED_RINKHALS_VERSION)
            current.version = SIMULATED_RINKHALS_VERSION
            return current

        try:
            current = RinkhalsVersion()
            current.path = Rinkhals.get_current_path()
            if not current.path:
                return None
            
            version_file = os.path.join(current.path, '.version')
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    current.version = f.read().strip()

            return current
        except:
            return None
    def get_installed_versions():
        versions = []
        if os.path.exists(RINKHALS_BASE):
            for f in os.scandir(RINKHALS_BASE):
                if f.is_dir():
                    version = RinkhalsVersion()
                    version.version = f.name
                    version.path = f.path
                    versions.append(version)
        return versions
    def get_available_versions(include_test=False, limit=10):
        printer_info = PrinterInfo.get()
        if not printer_info or not printer_info.model_code:
            return None
        
        try:
            import requests
            response = requests.get(f'https://api.github.com/repos/jbatonnet/Rinkhals/releases?per_page=20', timeout=5)
            if response.status_code == 200:
                releases = response.json()
                releases.sort(key=lambda r: r.get('published_at', ''), reverse=True)
                versions = []
                for release in releases:
                    tag = release.get('tag_name')
                    if not tag:
                        continue

                    version = RinkhalsVersion()
                    version.version = tag
                    version.test = 'test' in tag.lower() or 'beta' in tag.lower()
                    version.changes = release.get('body', '')
                    
                    if not include_test and version.test:
                        continue

                    published_at = release.get('published_at')
                    if published_at:
                        try:
                            dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                            version.date = int(dt.replace(tzinfo=timezone.utc).timestamp())
                        except Exception:
                            version.date = None

                    assets = release.get('assets', [])
                    if assets:
                        # Try to find asset matching current model code
                        asset_url = None
                        for asset in assets:
                            asset_name = asset.get('name', '').lower()
                            if 'update' in asset_name and printer_info.model_code.lower() in asset_name:
                                asset_url = asset.get('browser_download_url', '')
                                break
                        if not asset_url:
                            continue
                        version.url = asset_url

                    versions.append(version)
                    if len(versions) >= limit:
                        break
                return versions
            else:
                logging.warning(f'Failed to fetch releases: {response.status_code}')
                return []
        except Exception as e:
            logging.error(f'Error listing Rinkhals versions: {e}')
            return []
    def get_latest_version(include_test=False):
        return (Rinkhals.get_available_versions(include_test=include_test, limit=1) or [None])[0]


################
# Firmware update management

class FirmwareVersion:
    version: str
    date: int
    changes: str
    md5: str
    url: str

class Firmware:
    repositories = {
        'K2P': 'https://cdn.meowcat285.com/rinkhals/Kobra%202%20Pro/manifest.json',
        'K3': 'https://cdn.meowcat285.com/rinkhals/Kobra%203/manifest.json',
        'KS1': 'https://cdn.meowcat285.com/rinkhals/Kobra%20S1/manifest.json',
        'K3M': 'https://cdn.meowcat285.com/rinkhals/Kobra%203%20Max/manifest.json',
    }

    def get_current_version():
        if USING_SIMULATOR:
            global SIMULATED_FIRMWARE_VERSION
            return SIMULATED_FIRMWARE_VERSION

        try:
            with open('/useremain/dev/version', 'r') as f:
                return f.read().strip()
        except Exception as e:
            logging.error(f'Failed to read system version: {e}')
            return None
    def get_latest_version():
        try:
            from check_updates import CheckUpdateProgram

            check_updates = CheckUpdateProgram()
            (result, error) = check_updates.get_latest_update()

            if error:
                return None
            if not result:
                current_version = Firmware.get_current_version()

                available_versions = Firmware.get_available_versions()
                matching_version = ([ v for v in available_versions if v.version == current_version] or [None])[0]
                if matching_version:
                    return matching_version
                
                version = FirmwareVersion()
                version.version = current_version
                version.date = None
                version.changes = None
                version.url = None

                return version
            
            data = json.loads(result)

            version = FirmwareVersion()
            version.version = data.get('firmware_version', None)
            version.date = data.get('create_date', None)
            version.changes = data.get('update_desc', None)
            version.md5 = data.get('firmware_md5', None)
            version.url = data.get('firmware_url', None)

            return version
        except Exception as e:
            logging.error(f'Failed to get system available version: {e}')
            return None
    def get_available_versions(limit=10):
        versions = []
        printer_info = PrinterInfo.get()
        if not printer_info or printer_info.model_code not in Firmware.repositories:
            return versions

        manifest_url = Firmware.repositories.get(printer_info.model_code)
        if not manifest_url:
            return versions

        try:
            import requests
            response = requests.get(manifest_url, timeout=5)
            if response.status_code != 200:
                logging.warning(f'Failed to fetch firmware manifest: {response.status_code}')
                return versions
            
            manifest = json.loads(response.text)
            manifest_entries = sorted(manifest.get('firmwares', []), key=lambda e: e.get('version', ''), reverse=True)

            for entry in manifest_entries[:limit]:
                supported_models = entry.get('supported_models', [])
                supported_models = [ m.lower() for m in supported_models ]
                if supported_models and printer_info.model_code.lower() not in supported_models:
                    continue

                version = FirmwareVersion()
                version.version = entry.get('version', '')
                version.date = entry.get('date', 0)
                version.changes = entry.get('changes', '')
                version.md5 = entry.get('md5', '')
                version.url = entry.get('url', '')

                versions.append(version)
            return versions
        except Exception as e:
            logging.error(f'Error fetching firmware versions: {e}')
            return []


################
# Printer diagnostics

class DiagnosticType(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3
class DiagnosticFixes(Enum):
    REINSTALL_FIRMWARE = 1
    REINSTALL_RINKHALS = 2
    REINSTALL_RINKHALS_LAUNCHER = 3
    RESET_CONFIGURATION = 4

class Diagnostic:
    type = 0
    short_text = ''
    long_text = ''
    icon = None
    fix_text = None
    fix_action = None

    def __init__(self, type, short_text, long_text, icon=None, fix_text=None, fix_action=None):
        self.type = type
        self.short_text = short_text
        self.long_text = long_text
        self.icon = icon
        self.fix_text = fix_text
        self.fix_action = fix_action
    def collect():
        # Detect if environment cannot be identified
        printer_info = PrinterInfo.get()
        if not printer_info:
            yield Diagnostic(
                type=DiagnosticType.ERROR,
                short_text='Unknown environment',
                long_text='Unable to detect environment, your printer might be corrupted',
                fix_action=DiagnosticFixes.REINSTALL_FIRMWARE
            )

        # Detect if printer.cfg has been modified
        printer_cfg_path = '/userdata/app/gk/printer.cfg'

        if not os.path.exists(printer_cfg_path):
            yield Diagnostic(
                type=DiagnosticType.ERROR,
                short_text='Missing configuration',
                long_text='Unable to find default printer.cfg',
                fix_action=DiagnosticFixes.REINSTALL_FIRMWARE
            )
        else:
            printer_cfg_hash = hash(printer_cfg_path)
            supposed_hash = None

            firmware_version = Firmware.get_current_version()

            if printer_info:
                if printer_info.model_code == 'K3':
                    if firmware_version == '2.2.9.6': supposed_hash = None
                    if firmware_version == '2.3.3.2': supposed_hash = None
                    if firmware_version == '2.3.3.9': supposed_hash = None
                    if firmware_version == '2.3.5.3': supposed_hash = 'ed893ad8de97e52945c0f036acb1317e'
                    if firmware_version == '2.3.7':   supposed_hash = '6ae0f83abbd517232e03e9183984b5c8'
                    if firmware_version == '2.3.7.1': supposed_hash = '6ae0f83abbd517232e03e9183984b5c8'
                    if firmware_version == '2.3.8':   supposed_hash = 'addcb2cc9e34a867f49a7396bfdf276c'
                    if firmware_version == '2.3.8.9': supposed_hash = '0e6c2c875b997d861afa83c7453f5b6a'
                    if firmware_version == '2.4.0':   supposed_hash = 'eeac181517406e37d34463a79a5e2ebf'
                elif printer_info.model_code == 'KS1':
                    if firmware_version == '2.4.8.3': supposed_hash = '6ca031c6b72b86bb6a78311b308b2163'
                    if firmware_version == '2.5.0.2': supposed_hash = 'e142ceaba7a7fe56c1f5d51d15be2b96'
                    if firmware_version == '2.5.0.6': supposed_hash = 'c2d6967dce8803a20c3087b4e2764633'
                    if firmware_version == '2.5.1.6': supposed_hash = 'f41fdca985d7fdb02d561f5d271eb526'
                elif printer_info.model_code == 'K2P':
                    if firmware_version == '3.1.2.3': supposed_hash = 'fb945efa204eec777a139adafc6a40aa'
                    if firmware_version == '3.1.4':   supposed_hash = None
                elif printer_info.model_code == 'K3M':
                    if firmware_version == '2.4.4':   supposed_hash = None
                    if firmware_version == '2.4.4.9': supposed_hash = None

            if supposed_hash is None:
                printer_cfg_mtime = os.path.getmtime(printer_cfg_path)
                api_cfg_mtime = os.path.getmtime('/userdata/app/gk/config/api.cfg')

                if abs(printer_cfg_mtime - api_cfg_mtime) > 5:
                    yield Diagnostic(
                        type=DiagnosticType.WARNING,
                        short_text='Modified configuration',
                        long_text='Your printer.cfg has likely been modified',
                        fix_action=DiagnosticFixes.REINSTALL_FIRMWARE
                    )

            elif printer_cfg_hash != supposed_hash:
                yield Diagnostic(
                    type=DiagnosticType.WARNING,
                    short_text='Modified configuration',
                    long_text='Your printer.cfg has been modified',
                    fix_action=DiagnosticFixes.REINSTALL_FIRMWARE
                )

        # Detect if some configuration customizations are present
        custom_cfg_path = '/useremain/home/rinkhals/printer_data/config/printer.custom.cfg'
        if os.path.exists(custom_cfg_path):
            try:
                with open(custom_cfg_path, 'r') as f:
                    custom_lines = f.readlines()
            
                custom_lines = [ l for l in custom_lines if custom_lines.strip() and not custom_lines.strip().startswith('#') ]
                if len(custom_lines) > 0:
                    yield Diagnostic(
                        type=DiagnosticType.WARNING,
                        short_text='Customized configuration',
                        long_text='You have printer configuration customizations',
                        fix_action=DiagnosticFixes.RESET_CONFIGURATION
                    )
            except:
                pass

        # Detect if Rinkhals cannot start
        if os.path.exists('/useremain/rinkhals/.disable-rinkhals'):
            yield Diagnostic(
                type=DiagnosticType.WARNING,
                short_text='Rinkhals disabled',
                long_text='Rinkhals is disabled by the .disable-rinkhals file',
                fix_action=lambda: os.remove('/useremain/rinkhals/.disable-rinkhals')
            )

        if os.path.exists('/useremain/rinkhals/.version'):
            # Detect if launcher is missing
            if os.path.exists(start_script_path := '/userdata/app/gk/start.sh'):
                with open(start_script_path, 'r') as f:
                    script_content = f.read()
                    if 'Rinkhals/begin' not in script_content:
                        yield Diagnostic(
                            type=DiagnosticType.WARNING,
                            short_text='Rinkhals startup issue',
                            long_text='Rinkhals launcher is missing',
                            fix_action=DiagnosticFixes.REINSTALL_RINKHALS_LAUNCHER
                        )
                    if '\r\n' in script_content:
                        yield Diagnostic(
                            type=DiagnosticType.ERROR,
                            short_text='Firmware startup issue',
                            long_text='Kobra startup script has been altered',
                            fix_action=DiagnosticFixes.REINSTALL_FIRMWARE
                        )

            # Detect if start-rinkhals is missing
            if not os.path.exists('/useremain/rinkhals/start-rinkhals.sh'):
                yield Diagnostic(
                    type=DiagnosticType.WARNING,
                    short_text='Rinkhals startup issue',
                    long_text='Rinkhals startup script is missing',
                    fix_action=DiagnosticFixes.REINSTALL_RINKHALS
                )

            # TODO: Detect if .version does not exist
            pass
                
        # TODO: Detect if no internet > Run wpa_supplicant
        # TODO: Detect if Rinkhals is not installed
        # TODO: Detect if there are more than one bed meshes
        # TODO: Detect if LAN mode is enabled
        # TODO: Detect if there's enough space / too many Rinkhals installs
        # TODO: Detect if gklib failed to boot
        # TODO: Detect if the printer crashed somehow

        if USING_SIMULATOR:
            yield Diagnostic(
                type=DiagnosticType.INFO,
                short_text='Sample info diagnostic',
                long_text='You have printer configuration customizations'
            )
            yield Diagnostic(
                type=DiagnosticType.WARNING,
                short_text='Sample super long super long super long super long super long super long super long super long warning diagnostic',
                long_text='You have printer configuration customizations',
                fix_action=DiagnosticFixes.RESET_CONFIGURATION
            )
            yield Diagnostic(
                type=DiagnosticType.ERROR,
                short_text='Sample error diagnostic',
                long_text='You have printer configuration customizations',
                fix_action=DiagnosticFixes.REINSTALL_RINKHALS
            )






appsRepositories = [
    'https://raw.githubusercontent.com/jbatonnet/Rinkhals.apps/refs/heads/master/manifest.json'
]









class BaseApp:
    screen_info: ScreenInfo = None
    printer_info: PrinterInfo = None

    root_screen = None
    root_modal = None

    screen_composition = None
    screen_current = None
    screen_logo = None
    screen_main = None

    last_screen_check = 0
    modal_current = None

    def __init__(self):
        lv.init()

        self.screen_info = ScreenInfo.get()
        self.printer_info = PrinterInfo.get()

        if lv.helpers.is_windows():
            display = lv.windows_create_display('Rinkhals', self.screen_info.width, self.screen_info.height, 100, False, True)
            touch = lv.windows_acquire_pointer_indev(display)
            touch.set_display(display)

        elif lv.helpers.is_linux():
            display = lv.linux_fbdev_create()
            lv.linux_fbdev_set_file(display, '/dev/fb0')

            if self.screen_info.rotation == 0: display.set_rotation(lv.DISPLAY_ROTATION._0)
            elif self.screen_info.rotation == 90: display.set_rotation(lv.DISPLAY_ROTATION._270)
            elif self.screen_info.rotation == 180: display.set_rotation(lv.DISPLAY_ROTATION._180)
            elif self.screen_info.rotation == 270 or self.screen_info.rotation == -90: display.set_rotation(lv.DISPLAY_ROTATION._90)

            #display.set_color_format(lv.COLOR_FORMAT.RAW)

            touch = lv.evdev_create(lv.INDEV_TYPE.POINTER, '/dev/input/event0')
            touch.set_display(display)
            
            lv.evdev_grab_device(touch)
            lv.evdev_set_calibration(touch, self.screen_info.touch_calibration[0], self.screen_info.touch_calibration[1], self.screen_info.touch_calibration[2], self.screen_info.touch_calibration[3])

            def screen_sleep_cb(e):
                if time.time() - self.last_screen_check > 5:
                    self.last_screen_check = time.time()
                    brightness = shell('cat /sys/class/backlight/backlight/brightness')
                    if brightness == '0':
                        shell('echo 255 > /sys/class/backlight/backlight/brightness')

            touch.add_event_cb(screen_sleep_cb, lv.EVENT_CODE.CLICKED, None)

        display.set_dpi(self.screen_info.dpi)
        
        self.layout()

    def layout(self):
        self.root_screen = lvr.screen(tag='root_screen')
        self.root_screen.set_style_pad_all(0, lv.STATE.DEFAULT)
        #self.root_screen.set_style_bg_opa(lv.OPA.TRANSP, lv.STATE.DEFAULT)

        # For large screens, compose the screen with logo on the left and the actual content on the right
        if self.screen_info.width > self.screen_info.height:
            self.screen_composition = self.root_screen
            self.screen_composition.add_style(lvr.get_style_screen(), lv.STATE.DEFAULT)

            self.root_screen = lvr.panel(self.screen_composition)

            lv.screen_load(self.screen_composition)
            modal_parent = self.screen_composition
        else:
            lv.screen_load(self.root_screen)
            modal_parent = self.root_screen

        # Create the two main screens
        self.screen_logo = lvr.panel(self.root_screen, tag='screen_logo')
        self.screen_main = lvr.panel(self.root_screen, tag='screen_main')

        # Horizontal composition for large screens
        if self.screen_info.width > self.screen_info.height:
            self.screen_logo.set_parent(self.screen_composition)
            self.screen_logo.set_align(lv.ALIGN.LEFT_MID)
            self.screen_logo.set_size(lv.pct(50), lv.pct(100))

            self.root_screen.set_style_pad_all(0, lv.STATE.DEFAULT)
            self.root_screen.set_align(lv.ALIGN.RIGHT_MID)
            self.root_screen.set_size(lv.pct(50), lv.pct(100))

            self.screen_main.set_size(lv.pct(100), lv.pct(100))

        # Vertical composition for tall screens
        else:
            self.screen_composition = lvr.panel(self.root_screen)
            self.screen_composition.set_style_pad_all(0, lv.STATE.DEFAULT)
            self.screen_composition.set_size(lv.pct(100), lv.pct(100))

            self.screen_logo.set_parent(self.screen_composition)
            self.screen_logo.set_align(lv.ALIGN.TOP_MID)
            self.screen_logo.set_size(lv.pct(100), lv.pct(50))
            self.screen_logo.remove_flag(lv.OBJ_FLAG.HIDDEN)

            self.screen_main.set_parent(self.screen_composition)
            self.screen_main.set_align(lv.ALIGN.BOTTOM_MID)
            self.screen_main.set_size(lv.pct(100), lv.pct(50))
            self.screen_main.remove_flag(lv.OBJ_FLAG.HIDDEN)

        # Create the modal target
        self.root_modal = lvr.panel(modal_parent)
        if self.root_modal:
            self.root_modal.set_size(lv.pct(100), lv.pct(100))
            self.root_modal.set_style_bg_color(lv.color_black(), lv.STATE.DEFAULT)
            self.root_modal.set_style_bg_opa(160, lv.STATE.DEFAULT)
            self.root_modal.set_style_bg_color(lv.color_black(), lv.STATE.PRESSED)
            self.root_modal.set_style_bg_opa(160, lv.STATE.PRESSED)
            self.root_modal.add_flag(lv.OBJ_FLAG.HIDDEN)
            self.root_modal.set_state(lv.STATE.DISABLED, False)

        # Dialog modal for text and QR codes
        self.modal_dialog = lvr.panel(self.root_modal)
        if self.modal_dialog:
            self.modal_dialog.add_flag(lv.OBJ_FLAG.HIDDEN)
            self.modal_dialog.set_style_bg_color(lvr.COLOR_BACKGROUND, lv.STATE.DEFAULT)
            self.modal_dialog.set_style_bg_opa(lv.OPA.COVER, lv.STATE.DEFAULT)
            self.modal_dialog.set_width(lv.dpx(300))
            self.modal_dialog.set_style_radius(8, lv.STATE.DEFAULT)
            self.modal_dialog.set_style_pad_all(lv.dpx(20), lv.STATE.DEFAULT)
            self.modal_dialog.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.modal_dialog.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self.modal_dialog.center()
            
            self.modal_dialog.message = lvr.label(self.modal_dialog)
            self.modal_dialog.message.set_style_pad_bottom(lv.dpx(15), lv.STATE.DEFAULT)
            self.modal_dialog.message.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)

            self.modal_dialog.panel_qrcode = lvr.panel(self.modal_dialog)
            self.modal_dialog.panel_qrcode.set_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT)
            self.modal_dialog.panel_qrcode.set_style_pad_all(lv.dpx(10), lv.STATE.DEFAULT)
            self.modal_dialog.panel_qrcode.set_style_bg_color(lv.color_white(), lv.STATE.DEFAULT)

            self.modal_dialog.qrcode = lv.qrcode(self.modal_dialog.panel_qrcode)
            self.modal_dialog.qrcode.set_size(lv.dpx(224))

            self.modal_dialog.button_action = lvr.button(self.modal_dialog)
            self.modal_dialog.button_action.set_width(lv.dpx(160))

    def show_screen(self, screen):
        if self.screen_current:
            self.screen_current.add_flag(lv.OBJ_FLAG.HIDDEN)

        if self.screen_info.width <= self.screen_info.height and screen == self.screen_main:
            screen = self.screen_composition

        root = screen
        while parent := root.get_parent():
            root = parent
            
        if screen != root:
            screen.remove_flag(lv.OBJ_FLAG.HIDDEN)
            screen.move_foreground()

        lv.screen_load(root)
        self.screen_current = screen
    def show_modal(self, modal):
        if self.modal_current:
            self.modal_current.add_flag(lv.OBJ_FLAG.HIDDEN)

        self.modal_current = modal
        self.modal_current.remove_flag(lv.OBJ_FLAG.HIDDEN)
        self.modal_current.move_foreground()
        
        self.root_modal.remove_flag(lv.OBJ_FLAG.HIDDEN)
        self.root_modal.move_foreground()
    def hide_modal(self):
        if self.modal_current:
            self.modal_current.add_flag(lv.OBJ_FLAG.HIDDEN)

        self.root_modal.clear_event_cb()
        self.root_modal.add_flag(lv.OBJ_FLAG.HIDDEN)

    def show_text_dialog(self, text, action='OK', action_color=None, callback=None):
        def action_callback(callback=callback):
            if callback:
                callback()
            self.hide_modal()

        self.modal_dialog.message.set_text(text)
        self.modal_dialog.message.remove_flag(lv.OBJ_FLAG.HIDDEN)
        self.modal_dialog.panel_qrcode.add_flag(lv.OBJ_FLAG.HIDDEN)
        self.modal_dialog.button_action.set_text(action)
        self.modal_dialog.button_action.set_style_text_color(action_color if action_color else lvr.COLOR_TEXT, lv.STATE.DEFAULT)
        self.modal_dialog.button_action.clear_event_cb()
        self.modal_dialog.button_action.add_event_cb(lambda e: action_callback(), lv.EVENT_CODE.CLICKED, None)

        self.root_modal.add_event_cb(lambda e: self.hide_modal(), lv.EVENT_CODE.CLICKED, None)
        self.show_modal(self.modal_dialog)
    def show_qr_dialog(self, content, text=None):
        if text:
            self.modal_dialog.message.set_text(text)
            self.modal_dialog.message.remove_flag(lv.OBJ_FLAG.HIDDEN)
        else:
            self.modal_dialog.message.add_flag(lv.OBJ_FLAG.HIDDEN)

        self.modal_dialog.panel_qrcode.remove_flag(lv.OBJ_FLAG.HIDDEN)
        self.modal_dialog.qrcode.update(content)
        self.modal_dialog.button_action.set_text('OK')
        self.modal_dialog.button_action.set_style_text_color(lvr.COLOR_TEXT, lv.STATE.DEFAULT)
        self.modal_dialog.button_action.clear_event_cb()
        self.modal_dialog.button_action.add_event_cb(lambda e: self.hide_modal(), lv.EVENT_CODE.CLICKED, None)

        self.root_modal.add_event_cb(lambda e: self.hide_modal(), lv.EVENT_CODE.CLICKED, None)
        self.show_modal(self.modal_dialog)

    def quit(self):
        logging.info('Exiting...')
        print('', flush=True)
        os.kill(os.getpid(), 9)

    def run(self):
        def loop():
            while True:
                lv.tick_inc(16)
                lv.timer_handler()
                time.sleep(0.016)

        if USING_SIMULATOR:
            loop()
        else:
            try:
                loop()
            except:
                import threading
                import traceback

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

        quit()
