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

    import subprocess
    process = subprocess.run(['sh', '-c', command], capture_output=True, text=True)
    result = (process.stdout or '').strip()

    command = command.replace('. /useremain/rinkhals/.current/tools.sh && ', '')
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

def hash_md5(path):
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
def hash_sha256(path):
    if not os.path.exists(path):
        return None
    
    import hashlib
    sha256 = hashlib.sha256()

    with open(path, 'rb') as f:
        while True:
            data = f.read(8192)
            if not data:
                break
            sha256.update(data)

    return sha256.hexdigest()


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
    model_code: str
    model: str

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
            elif model_id == '20027':
                printer_info.model = 'Anycubic Kobra 3 V2'
                printer_info.model_code = 'K3V2'
            elif model_id == '20029':
                printer_info.model = 'Anycubic Kobra S1 Max'
                printer_info.model_code = 'KS1M'
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
            if printer_info.model_code == 'KS1' or printer_info.model_code == 'KS1M':
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

        if printer_info.model_code == 'KS1' or printer_info.model_code == 'KS1M':
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
    sha256: str
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
                        asset_digest = None

                        for asset in assets:
                            asset_name = asset.get('name', '').lower()
                            if 'update' in asset_name and printer_info.model_code.lower().replace('v2', '') in asset_name:
                                asset_url = asset.get('browser_download_url', '')
                                asset_digest = asset.get('digest', '')
                                break
                        if not asset_url:
                            continue

                        version.url = asset_url
                        if asset_digest and 'sha256' in asset_digest:
                            version.sha256 = asset_digest.replace('sha256:', '') if asset_digest else None

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
        'K2P': 'https://rinkhals.thedju.net/Kobra%202%20Pro/manifest.json',
        'K3': 'https://rinkhals.thedju.net/Kobra%203/manifest.json',
        'K3V2': 'https://rinkhals.thedju.net/Kobra%203%20V2/manifest.json',
        'KS1': 'https://rinkhals.thedju.net/Kobra%20S1/manifest.json',
        'K3M': 'https://rinkhals.thedju.net/Kobra%203%20Max/manifest.json',
        'KS1M': 'https://rinkhals.thedju.net/Kobra%20S1%20Max/manifest.json',
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

            current_version = Rinkhals.get_current_version()

            headers = {
                'User-Agent': f'Rinkhals/{current_version.version if current_version else "Unknown"} ({printer_info.model_code if printer_info else "Unknown"})'
            }
            response = requests.get(manifest_url, timeout=5, headers=headers)
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
            printer_cfg_hash = hash_md5(printer_cfg_path)
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
                    if firmware_version == '2.4.0.4': supposed_hash = '7da3310baa37c466d790c7a2d8c0d097'
                    if firmware_version == '2.4.1.9': supposed_hash = None
                elif printer_info.model_code == 'KS1':
                    if firmware_version == '2.4.8.3': supposed_hash = '6ca031c6b72b86bb6a78311b308b2163'
                    if firmware_version == '2.5.0.2': supposed_hash = 'e142ceaba7a7fe56c1f5d51d15be2b96'
                    if firmware_version == '2.5.0.6': supposed_hash = 'c2d6967dce8803a20c3087b4e2764633'
                    if firmware_version == '2.5.1.6': supposed_hash = 'f41fdca985d7fdb02d561f5d271eb526'
                    if firmware_version == '2.5.2.2': supposed_hash = None
                    if firmware_version == '2.5.2.3': supposed_hash = 'b29e8594f56001c09d4e232696b9827d'
                    if firmware_version == '2.5.3.1': supposed_hash = '7678403dc8064f650931904f48be88f0'
                    if firmware_version == '2.5.3.5': supposed_hash = 'd4021a6471d431dcebbe1b2f7bc17add'
                elif printer_info.model_code == 'K2P':
                    if firmware_version == '3.1.2.3': supposed_hash = 'fb945efa204eec777a139adafc6a40aa'
                    if firmware_version == '3.1.4':   supposed_hash = None
                elif printer_info.model_code == 'K3M':
                    if firmware_version == '2.4.4':   supposed_hash = None
                    if firmware_version == '2.4.4.9': supposed_hash = None
                    if firmware_version == '2.4.5.3': supposed_hash = None
                    if firmware_version == '2.4.6':   supposed_hash = 'ff5c2d8ae79b8d90d0ff7c697d85502d'
                    if firmware_version == '2.4.6.5': supposed_hash = 'b79497202880f92b6e4a578a32e8f3a3'
                    if firmware_version == '2.4.8.4': supposed_hash = None
                elif printer_info.model_code == 'K3V2':
                    if firmware_version == '1.0.5.8': supposed_hash = '94b173bb47de679f11439e363a4628c8'
                    if firmware_version == '1.0.7.3': supposed_hash = None

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


################
# Apps management

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
    screen_ota = None
    screen_ota_rinkhals = None
    screen_ota_firmware = None

    last_screen_check = 0
    modal_current = None
    
    # Cache
    cache_rinkhals_latest = None
    cache_rinkhals_available = None
    cache_firmware_latest = None
    cache_firmware_available = None

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
                        os.system('echo 255 > /sys/class/backlight/backlight/brightness')
                        time.sleep(1)
                        lv.screen_active().invalidate()

            touch.add_event_cb(screen_sleep_cb, lv.EVENT_CODE.ALL, None)

        display.set_dpi(self.screen_info.dpi)
        
        self.layout()

    # UI logic
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
    
        # Leave an empty 24px gap at the top of K2P / K3 screen
        if self.printer_info.model_code == 'K2P' or self.printer_info.model_code == 'K3' or self.printer_info.model_code == 'K3M' or self.printer_info.model_code == 'K3V2':
            layer_bottom = lv.display_get_default().get_layer_bottom()
            #layer_bottom.set_style_bg_opa(lv.OPA.TRANSP, lv.STATE.DEFAULT)
            layer_bottom.set_style_bg_opa(lv.OPA.COVER, lv.STATE.DEFAULT)
            layer_bottom.set_style_bg_color(lv.color_black(), lv.STATE.DEFAULT)

            original_root = self.root_screen
            original_root.set_style_bg_opa(lv.OPA.TRANSP, lv.STATE.DEFAULT)

            self.root_screen = lvr.panel(original_root)
            self.root_screen.add_style(lvr.get_style_screen(), lv.STATE.DEFAULT)
            self.root_screen.set_size(lv.pct(100), self.screen_info.height - 24)
            self.root_screen.set_align(lv.ALIGN.BOTTOM_MID)
            self.root_screen.set_style_pad_all(0, lv.STATE.DEFAULT)

            self.root_modal.set_parent(self.root_screen)
            self.screen_composition.set_parent(self.root_screen)

            #lv.screen_load(original_root)
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
    def quit(self):
        logging.info('Exiting...')
        print('', flush=True)
        os.kill(os.getpid(), 9)

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

        if screen == self.screen_ota: self.show_ota()
        elif screen == self.screen_ota_rinkhals: self.show_ota_rinkhals()
        elif screen == self.screen_ota_firmware: self.show_ota_firmware()
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

    # Shared screens
    def layout_ota(self):
        self.screen_ota = lvr.panel(self.root_screen, tag='screen_ota', flex_flow=lv.FLEX_FLOW.COLUMN)

        self.screen_ota.add_flag(lv.OBJ_FLAG.HIDDEN)
        self.screen_ota.set_size(lv.pct(100), lv.pct(100))
        self.screen_ota.set_style_pad_all(0, lv.STATE.DEFAULT)

        title_bar = lvr.title_bar(self.screen_ota)
        title_bar.set_y(-lvr.get_title_bar_height())
        
        title = lvr.title(title_bar)
        title.set_text('Install & Updates')
        title.center()

        icon_back = lvr.button_icon(title_bar)
        icon_back.set_align(lv.ALIGN.LEFT_MID)
        icon_back.set_text('')
        icon_back.add_event_cb(lambda e: self.show_screen(self.screen_main), lv.EVENT_CODE.CLICKED, None)

        def refresh_ota(e):
            self.show_screen(self.screen_ota)
            self.show_ota(True)

        icon_refresh = lvr.button_icon(title_bar)
        icon_refresh.add_event_cb(refresh_ota, lv.EVENT_CODE.CLICKED, None)
        icon_refresh.set_text('')
        icon_refresh.set_align(lv.ALIGN.RIGHT_MID)

        panel_ota = lvr.panel(self.screen_ota, lv.FLEX_FLOW.COLUMN)
        panel_ota.set_width(lv.pct(100))
        panel_ota.set_style_pad_all(0, lv.STATE.DEFAULT)
        panel_ota.set_flex_grow(1)

        panel_rinkhals = lvr.panel(panel_ota)
        if panel_rinkhals:
            panel_rinkhals.set_width(lv.pct(100))
            panel_rinkhals.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            panel_rinkhals.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            panel_rinkhals.set_style_pad_row(0, lv.STATE.DEFAULT)
            panel_rinkhals.set_style_pad_all(0, lv.STATE.DEFAULT)

            panel_title = lvr.panel(panel_rinkhals)
            if panel_title:
                panel_title.set_width(lv.pct(100))
                panel_title.set_style_bg_color(lv.color_white(), lv.STATE.DEFAULT)
                panel_title.set_style_bg_opa(lv.OPA._10, lv.STATE.DEFAULT)

                label_rinkhals = lvr.title(panel_title)
                label_rinkhals.set_text('Rinkhals')

            panel_current = lvr.panel(panel_rinkhals)
            if panel_current:
                panel_current.set_width(lv.pct(100))
                panel_current.set_style_pad_hor(0, lv.STATE.DEFAULT)

                label_current = lvr.label(panel_current)
                label_current.set_text('Current version')
                label_current.align(lv.ALIGN.LEFT_MID, lvr.get_global_margin(), 0)

                self.screen_ota.label_rinkhals_current_value = lvr.label(panel_current)
                self.screen_ota.label_rinkhals_current_value.set_text('?')
                self.screen_ota.label_rinkhals_current_value.align(lv.ALIGN.RIGHT_MID, -lvr.get_global_margin(), 0)
                self.screen_ota.label_rinkhals_current_value.set_style_text_color(lvr.COLOR_DISABLED, lv.STATE.DEFAULT)
            
            panel_latest = lvr.panel(panel_rinkhals)
            if panel_latest:
                panel_latest.set_width(lv.pct(100))
                panel_latest.set_style_pad_hor(0, lv.STATE.DEFAULT)

                label_latest = lvr.label(panel_latest)
                label_latest.set_text('Latest version')
                label_latest.align(lv.ALIGN.LEFT_MID, lvr.get_global_margin(), 0)

                self.screen_ota.label_rinkhals_latest_value = lvr.label(panel_latest)
                self.screen_ota.label_rinkhals_latest_value.set_text('?')
                self.screen_ota.label_rinkhals_latest_value.align(lv.ALIGN.RIGHT_MID, -lvr.get_global_margin(), 0)
                self.screen_ota.label_rinkhals_latest_value.set_style_text_color(lvr.COLOR_DISABLED, lv.STATE.DEFAULT)
            
            panel_actions = lvr.panel(panel_rinkhals, lv.FLEX_FLOW.ROW)
            if panel_actions:
                self.screen_ota.button_rinkhals_manage = lvr.button(panel_actions)
                self.screen_ota.button_rinkhals_manage.set_text('Manage')
                self.screen_ota.button_rinkhals_manage.add_event_cb(lambda e: self.show_screen(self.screen_ota_rinkhals), lv.EVENT_CODE.CLICKED, None)
                
                self.screen_ota.button_rinkhals_refresh = lvr.button(panel_actions)
                self.screen_ota.button_rinkhals_refresh.set_text('Refresh')

        panel_firmware = lvr.panel(panel_ota)
        if panel_firmware:
            panel_firmware.set_width(lv.pct(100))
            panel_firmware.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            panel_firmware.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            panel_firmware.set_style_pad_row(0, lv.STATE.DEFAULT)
            panel_firmware.set_style_pad_all(0, lv.STATE.DEFAULT)

            panel_title = lvr.panel(panel_firmware)
            if panel_title:
                panel_title.set_width(lv.pct(100))
                panel_title.set_style_bg_color(lv.color_white(), lv.STATE.DEFAULT)
                panel_title.set_style_bg_opa(lv.OPA._10, lv.STATE.DEFAULT)

                label_rinkhals = lvr.title(panel_title)
                label_rinkhals.set_text('Anycubic')

            panel_current = lvr.panel(panel_firmware)
            if panel_current:
                panel_current.set_width(lv.pct(100))
                panel_current.set_style_pad_hor(0, lv.STATE.DEFAULT)

                label_current = lvr.label(panel_current)
                label_current.set_text('Current version')
                label_current.align(lv.ALIGN.LEFT_MID, lvr.get_global_margin(), 0)

                self.screen_ota.label_firmware_current_value = lvr.label(panel_current)
                self.screen_ota.label_firmware_current_value.set_text('?')
                self.screen_ota.label_firmware_current_value.align(lv.ALIGN.RIGHT_MID, -lvr.get_global_margin(), 0)
                self.screen_ota.label_firmware_current_value.set_style_text_color(lvr.COLOR_DISABLED, lv.STATE.DEFAULT)
            
            panel_latest = lvr.panel(panel_firmware)
            if panel_latest:
                panel_latest.set_width(lv.pct(100))
                panel_latest.set_style_pad_hor(0, lv.STATE.DEFAULT)

                label_latest = lvr.label(panel_latest)
                label_latest.set_text('Latest version')
                label_latest.align(lv.ALIGN.LEFT_MID, lvr.get_global_margin(), 0)

                self.screen_ota.label_firmware_latest_value = lvr.label(panel_latest)
                self.screen_ota.label_firmware_latest_value.set_text('?')
                self.screen_ota.label_firmware_latest_value.align(lv.ALIGN.RIGHT_MID, -lvr.get_global_margin(), 0)
                self.screen_ota.label_firmware_latest_value.set_style_text_color(lvr.COLOR_DISABLED, lv.STATE.DEFAULT)
            
            panel_actions = lvr.panel(panel_firmware, lv.FLEX_FLOW.ROW)
            if panel_actions:
                self.screen_ota.button_firmware_manage = lvr.button(panel_actions)
                self.screen_ota.button_firmware_manage.set_text('Manage')
                self.screen_ota.button_firmware_manage.add_event_cb(lambda e: self.show_screen(self.screen_ota_firmware), lv.EVENT_CODE.CLICKED, None)
                
                self.screen_ota.button_firmware_refresh = lvr.button(panel_actions)
                self.screen_ota.button_firmware_refresh.set_text('Refresh')
    def layout_ota_rinkhals(self):
        self.screen_ota_rinkhals = lvr.panel(self.root_screen, tag='screen_ota_rinkhals')
        if self.screen_ota_rinkhals:
            self.screen_ota_rinkhals.add_flag(lv.OBJ_FLAG.HIDDEN)
            self.screen_ota_rinkhals.set_size(lv.pct(100), lv.pct(100))
            self.screen_ota_rinkhals.set_style_pad_all(0, lv.STATE.DEFAULT)
            self.screen_ota_rinkhals.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.screen_ota_rinkhals.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self.screen_ota_rinkhals.set_style_pad_row(0, lv.STATE.DEFAULT)

            title_bar = lvr.title_bar(self.screen_ota_rinkhals)
            title_bar.set_y(-lvr.get_title_bar_height())
            
            title = lvr.title(title_bar)
            title.set_text('Manage Rinkhals')
            title.center()

            icon_back = lvr.button_icon(title_bar)
            icon_back.set_align(lv.ALIGN.LEFT_MID)
            icon_back.set_text('')
            icon_back.add_event_cb(lambda e: self.show_screen(self.screen_ota), lv.EVENT_CODE.CLICKED, None)

            self.screen_ota_rinkhals.icon_refresh = lvr.button_icon(title_bar)
            self.screen_ota_rinkhals.icon_refresh.set_text('')
            self.screen_ota_rinkhals.icon_refresh.set_align(lv.ALIGN.RIGHT_MID)

            panel_include_test = lvr.panel(self.screen_ota_rinkhals)
            panel_include_test.set_width(lv.pct(100))
            panel_include_test.set_style_border_side(lv.BORDER_SIDE.BOTTOM, lv.STATE.DEFAULT)

            label_include_test = lvr.label(panel_include_test)
            label_include_test.set_text('Include test versions')
            label_include_test.set_align(lv.ALIGN.LEFT_MID)

            self.screen_ota_rinkhals.checkbox_include_test = lvr.checkbox(panel_include_test)
            self.screen_ota_rinkhals.checkbox_include_test.set_align(lv.ALIGN.RIGHT_MID)
            self.screen_ota_rinkhals.checkbox_include_test.set_checked(False)

            self.screen_ota_rinkhals.panel_versions = lvr.panel(self.screen_ota_rinkhals, flex_flow=lv.FLEX_FLOW.COLUMN)
            self.screen_ota_rinkhals.panel_versions.set_width(lv.pct(100))
            self.screen_ota_rinkhals.panel_versions.set_style_pad_all(0, lv.STATE.DEFAULT)
            self.screen_ota_rinkhals.panel_versions.set_style_pad_row(0, lv.STATE.DEFAULT)
            self.screen_ota_rinkhals.panel_versions.set_flex_grow(1)

            self.screen_ota_firmware = lvr.panel(self.root_screen, tag='screen_ota_firmware')

            self.screen_ota_firmware.add_flag(lv.OBJ_FLAG.HIDDEN)
            self.screen_ota_firmware.set_size(lv.pct(100), lv.pct(100))
            self.screen_ota_firmware.set_style_pad_all(0, lv.STATE.DEFAULT)
            self.screen_ota_firmware.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.screen_ota_firmware.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self.screen_ota_firmware.set_style_pad_row(0, lv.STATE.DEFAULT)

            title_bar = lvr.title_bar(self.screen_ota_firmware)
            title_bar.set_y(-lvr.get_title_bar_height())
            
            title = lvr.title(title_bar)
            title.set_text('Manage firmware')
            title.center()

            icon_back = lvr.button_icon(title_bar)
            icon_back.set_align(lv.ALIGN.LEFT_MID)
            icon_back.set_text('')
            icon_back.add_event_cb(lambda e: self.show_screen(self.screen_ota), lv.EVENT_CODE.CLICKED, None)

            self.screen_ota_firmware.icon_refresh = lvr.button_icon(title_bar)
            self.screen_ota_firmware.icon_refresh.set_text('')
            self.screen_ota_firmware.icon_refresh.set_align(lv.ALIGN.RIGHT_MID)

            self.screen_ota_firmware.panel_versions = lvr.panel(self.screen_ota_firmware, flex_flow=lv.FLEX_FLOW.COLUMN)
            self.screen_ota_firmware.panel_versions.set_width(lv.pct(100))
            self.screen_ota_firmware.panel_versions.set_style_pad_all(0, lv.STATE.DEFAULT)
            self.screen_ota_firmware.panel_versions.set_style_pad_row(0, lv.STATE.DEFAULT)
            self.screen_ota_firmware.panel_versions.set_flex_grow(1)

        self.modal_ota_rinkhals = lvr.modal(self.root_modal, tag='modal_ota_rinkhals')
        if self.modal_ota_rinkhals:
            self.modal_ota_rinkhals.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.modal_ota_rinkhals.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

            self.modal_ota_rinkhals.label_title = lvr.title(self.modal_ota_rinkhals)
            self.modal_ota_rinkhals.label_title.set_width(lv.pct(100))
            self.modal_ota_rinkhals.label_title.set_height(lvr.get_font_title().get_line_height())
            self.modal_ota_rinkhals.label_title.set_style_pad_bottom(lvr.get_global_margin(), lv.STATE.DEFAULT)
            self.modal_ota_rinkhals.label_title.set_long_mode(lv.LABEL_LONG_MODE.DOTS)
            self.modal_ota_rinkhals.label_title.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)

            panel_description = lvr.panel(self.modal_ota_rinkhals)
            panel_description.set_size(lv.pct(100), lv.SIZE_CONTENT)
            panel_description.set_style_max_height(lv.dpx(115), lv.STATE.DEFAULT)

            self.modal_ota_rinkhals.label_description = lvr.subtitle(panel_description)
            self.modal_ota_rinkhals.label_description.set_width(lv.SIZE_CONTENT)
            self.modal_ota_rinkhals.label_description.set_style_max_width(lv.SIZE_CONTENT, lv.STATE.DEFAULT)
            self.modal_ota_rinkhals.label_description.set_style_text_color(lvr.COLOR_DISABLED, lv.STATE.DEFAULT)

            self.modal_ota_rinkhals.label_warning = lvr.subtitle(self.modal_ota_rinkhals)
            self.modal_ota_rinkhals.label_warning.set_width(lv.pct(100))
            self.modal_ota_rinkhals.label_warning.set_long_mode(lv.LABEL_LONG_MODE.WRAP)
            self.modal_ota_rinkhals.label_warning.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)
            self.modal_ota_rinkhals.label_warning.set_style_text_color(lvr.COLOR_DANGER, lv.STATE.DEFAULT)

            self.modal_ota_rinkhals.panel_progress = lvr.panel(self.modal_ota_rinkhals, flex_flow=lv.FLEX_FLOW.COLUMN, flex_align=lv.FLEX_ALIGN.CENTER)
            self.modal_ota_rinkhals.panel_progress.set_width(lv.pct(100))
            self.modal_ota_rinkhals.panel_progress.set_style_pad_row(lv.dpx(2), lv.STATE.DEFAULT)

            panel_progress_background = lvr.panel(self.modal_ota_rinkhals.panel_progress)
            panel_progress_background.set_size(lv.pct(100), lv.dpx(10))
            panel_progress_background.set_style_pad_all(0, lv.STATE.DEFAULT)
            panel_progress_background.set_style_bg_color(lv.color_lighten(lvr.COLOR_BACKGROUND, 48), lv.STATE.DEFAULT)
            panel_progress_background.set_style_bg_opa(lv.OPA.COVER, lv.STATE.DEFAULT)
            panel_progress_background.remove_flag(lv.OBJ_FLAG.SCROLLABLE)

            self.modal_ota_rinkhals.obj_progress_bar = lvr.panel(panel_progress_background)
            self.modal_ota_rinkhals.obj_progress_bar.set_align(lv.ALIGN.LEFT_MID)
            self.modal_ota_rinkhals.obj_progress_bar.set_style_bg_color(lvr.COLOR_PRIMARY, lv.STATE.DEFAULT)
            self.modal_ota_rinkhals.obj_progress_bar.set_style_bg_opa(lv.OPA.COVER, lv.STATE.DEFAULT)
            self.modal_ota_rinkhals.obj_progress_bar.set_size(lv.pct(24), lv.pct(100))

            self.modal_ota_rinkhals.label_progress_text = lvr.label(self.modal_ota_rinkhals.panel_progress)
            self.modal_ota_rinkhals.label_progress_text.set_text('Ready')

            panel_actions = lvr.panel(self.modal_ota_rinkhals)
            panel_actions.set_width(lv.pct(100))
            panel_actions.set_flex_flow(lv.FLEX_FLOW.ROW)
            panel_actions.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            panel_actions.set_style_pad_column(lv.dpx(15), lv.STATE.DEFAULT)
            panel_actions.set_style_pad_all(0, lv.STATE.DEFAULT)
            panel_actions.set_style_pad_top(lvr.get_global_margin(), lv.STATE.DEFAULT)

            self.modal_ota_rinkhals.button_uninstall = lvr.button(panel_actions)
            self.modal_ota_rinkhals.button_uninstall.set_width(lv.pct(45))
            self.modal_ota_rinkhals.button_uninstall.set_style_text_color(lvr.COLOR_DANGER, lv.STATE.DEFAULT)
            self.modal_ota_rinkhals.button_uninstall.set_text('Uninstall')
            self.modal_ota_rinkhals.button_uninstall.add_flag(lv.OBJ_FLAG.HIDDEN)

            self.modal_ota_rinkhals.button_action = lvr.button(panel_actions)
            self.modal_ota_rinkhals.button_action.set_width(lv.pct(45))
            self.modal_ota_rinkhals.button_action.set_text('Download')
    def layout_ota_firmware(self):
        self.screen_ota_firmware = lvr.panel(self.root_screen, tag='screen_ota_firmware')
        if self.screen_ota_firmware:
            self.screen_ota_firmware.add_flag(lv.OBJ_FLAG.HIDDEN)
            self.screen_ota_firmware.set_size(lv.pct(100), lv.pct(100))
            self.screen_ota_firmware.set_style_pad_all(0, lv.STATE.DEFAULT)
            self.screen_ota_firmware.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.screen_ota_firmware.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self.screen_ota_firmware.set_style_pad_row(0, lv.STATE.DEFAULT)

            title_bar = lvr.title_bar(self.screen_ota_firmware)
            title_bar.set_y(-lvr.get_title_bar_height())
            
            title = lvr.title(title_bar)
            title.set_text('Manage firmware')
            title.center()

            icon_back = lvr.button_icon(title_bar)
            icon_back.set_align(lv.ALIGN.LEFT_MID)
            icon_back.set_text('')
            icon_back.add_event_cb(lambda e: self.show_screen(self.screen_ota), lv.EVENT_CODE.CLICKED, None)

            self.screen_ota_firmware.icon_refresh = lvr.button_icon(title_bar)
            self.screen_ota_firmware.icon_refresh.set_text('')
            self.screen_ota_firmware.icon_refresh.set_align(lv.ALIGN.RIGHT_MID)

            self.screen_ota_firmware.panel_versions = lvr.panel(self.screen_ota_firmware, flex_flow=lv.FLEX_FLOW.COLUMN)
            self.screen_ota_firmware.panel_versions.set_width(lv.pct(100))
            self.screen_ota_firmware.panel_versions.set_style_pad_all(0, lv.STATE.DEFAULT)
            self.screen_ota_firmware.panel_versions.set_style_pad_row(0, lv.STATE.DEFAULT)
            self.screen_ota_firmware.panel_versions.set_flex_grow(1)

        self.modal_ota_firmware = lvr.modal(self.root_modal, tag='modal_ota_firmware')
        if self.modal_ota_firmware:
            self.modal_ota_firmware.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.modal_ota_firmware.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

            self.modal_ota_firmware.label_title = lvr.title(self.modal_ota_firmware)
            self.modal_ota_firmware.label_title.set_width(lv.pct(100))
            self.modal_ota_firmware.label_title.set_height(lvr.get_font_title().get_line_height())
            self.modal_ota_firmware.label_title.set_style_pad_bottom(lvr.get_global_margin(), lv.STATE.DEFAULT)
            self.modal_ota_firmware.label_title.set_long_mode(lv.LABEL_LONG_MODE.DOTS)
            self.modal_ota_firmware.label_title.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)

            panel_description = lvr.panel(self.modal_ota_firmware)
            panel_description.set_size(lv.pct(100), lv.SIZE_CONTENT)
            panel_description.set_style_max_height(lv.dpx(115), lv.STATE.DEFAULT)

            self.modal_ota_firmware.label_description = lvr.subtitle(panel_description)
            self.modal_ota_firmware.label_description.set_width(lv.SIZE_CONTENT)
            self.modal_ota_firmware.label_description.set_style_max_width(lv.SIZE_CONTENT, lv.STATE.DEFAULT)
            self.modal_ota_firmware.label_description.set_style_text_color(lvr.COLOR_DISABLED, lv.STATE.DEFAULT)

            self.modal_ota_firmware.label_warning = lvr.subtitle(self.modal_ota_firmware)
            self.modal_ota_firmware.label_warning.set_width(lv.pct(100))
            self.modal_ota_firmware.label_warning.set_long_mode(lv.LABEL_LONG_MODE.WRAP)
            self.modal_ota_firmware.label_warning.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)
            self.modal_ota_firmware.label_warning.set_style_text_color(lvr.COLOR_DANGER, lv.STATE.DEFAULT)

            self.modal_ota_firmware.panel_progress = lvr.panel(self.modal_ota_firmware, flex_flow=lv.FLEX_FLOW.COLUMN, flex_align=lv.FLEX_ALIGN.CENTER)
            self.modal_ota_firmware.panel_progress.set_width(lv.pct(100))
            self.modal_ota_firmware.panel_progress.set_style_pad_row(lv.dpx(2), lv.STATE.DEFAULT)

            panel_progress_background = lvr.panel(self.modal_ota_firmware.panel_progress)
            panel_progress_background.set_size(lv.pct(100), lv.dpx(10))
            panel_progress_background.set_style_pad_all(0, lv.STATE.DEFAULT)
            panel_progress_background.set_style_bg_color(lv.color_lighten(lvr.COLOR_BACKGROUND, 48), lv.STATE.DEFAULT)
            panel_progress_background.set_style_bg_opa(lv.OPA.COVER, lv.STATE.DEFAULT)
            panel_progress_background.remove_flag(lv.OBJ_FLAG.SCROLLABLE)

            self.modal_ota_firmware.obj_progress_bar = lvr.panel(panel_progress_background)
            self.modal_ota_firmware.obj_progress_bar.set_align(lv.ALIGN.LEFT_MID)
            self.modal_ota_firmware.obj_progress_bar.set_style_bg_color(lvr.COLOR_PRIMARY, lv.STATE.DEFAULT)
            self.modal_ota_firmware.obj_progress_bar.set_style_bg_opa(lv.OPA.COVER, lv.STATE.DEFAULT)
            self.modal_ota_firmware.obj_progress_bar.set_size(lv.pct(24), lv.pct(100))

            self.modal_ota_firmware.label_progress_text = lvr.label(self.modal_ota_firmware.panel_progress)
            self.modal_ota_firmware.label_progress_text.set_text('Ready')

            panel_actions = lvr.panel(self.modal_ota_firmware)
            panel_actions.set_width(lv.pct(100))
            panel_actions.set_flex_flow(lv.FLEX_FLOW.ROW)
            panel_actions.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            panel_actions.set_style_pad_column(lv.dpx(15), lv.STATE.DEFAULT)
            panel_actions.set_style_pad_all(0, lv.STATE.DEFAULT)
            panel_actions.set_style_pad_top(lvr.get_global_margin(), lv.STATE.DEFAULT)

            self.modal_ota_firmware.button_cancel = lvr.button(panel_actions)
            self.modal_ota_firmware.button_cancel.set_width(lv.pct(45))
            self.modal_ota_firmware.button_cancel.set_text('Cancel')
            self.modal_ota_firmware.button_cancel.add_event_cb(lambda e: self.hide_modal(), lv.EVENT_CODE.CLICKED, None)
            
            self.modal_ota_firmware.button_action = lvr.button(panel_actions)
            self.modal_ota_firmware.button_action.set_width(lv.pct(45))
            self.modal_ota_firmware.button_action.set_text('Download')

    def show_ota(self, force=False):
        def refresh_rinkhals(force):
            lv.lock()
            self.screen_ota.button_rinkhals_refresh.set_state(lv.STATE.DISABLED, True)
            self.screen_ota.label_rinkhals_current_value.set_text('-')
            self.screen_ota.label_rinkhals_latest_value.set_text('-')
            lv.unlock()

            rinkhals_current = Rinkhals.get_current_version()

            lv.lock()
            if rinkhals_current:
                self.screen_ota.label_rinkhals_current_value.set_text(rinkhals_current.version)
            else:
                self.screen_ota.label_rinkhals_current_value.set_text('Not found')
            lv.unlock()

            if force or not self.cache_rinkhals_latest:
                self.cache_rinkhals_latest = Rinkhals.get_latest_version()

            lv.lock()
            if self.cache_rinkhals_latest:
                self.screen_ota.label_rinkhals_latest_value.set_text(self.cache_rinkhals_latest.version)
            else:
                self.screen_ota.label_rinkhals_latest_value.set_text('?')
            lv.unlock()

            lv.lock()
            self.screen_ota.button_rinkhals_refresh.set_state(lv.STATE.DISABLED, False)
            lv.unlock()
        def refresh_firmware(force):
            lv.lock()
            self.screen_ota.button_firmware_refresh.set_state(lv.STATE.DISABLED, True)
            self.screen_ota.label_firmware_current_value.set_text('-')
            self.screen_ota.label_firmware_latest_value.set_text('-')
            lv.unlock()

            firmware_current_version = Firmware.get_current_version()

            lv.lock()
            if firmware_current_version:
                self.screen_ota.label_firmware_current_value.set_text(firmware_current_version)
            else:
                self.screen_ota.label_firmware_current_value.set_text('Unknown')
            lv.unlock()

            if force or not self.cache_firmware_latest:
                self.cache_firmware_latest = Firmware.get_latest_version()

            lv.lock()
            if self.cache_firmware_latest:
                self.screen_ota.label_firmware_latest_value.set_text(self.cache_firmware_latest.version)
            else:
                self.screen_ota.label_firmware_latest_value.set_text('Error')
            lv.unlock()

            lv.lock()
            self.screen_ota.button_firmware_refresh.set_state(lv.STATE.DISABLED, False)
            lv.unlock()

        self.screen_ota.button_rinkhals_refresh.clear_event_cb()
        self.screen_ota.button_rinkhals_refresh.add_event_cb(lambda e: run_async(lambda: refresh_rinkhals(True)), lv.EVENT_CODE.CLICKED, None)
        run_async(lambda: refresh_rinkhals(force))

        self.screen_ota.button_firmware_refresh.clear_event_cb()
        self.screen_ota.button_firmware_refresh.add_event_cb(lambda e: run_async(lambda: refresh_firmware(True)), lv.EVENT_CODE.CLICKED, None)
        run_async(lambda: refresh_firmware(force))
    def show_ota_rinkhals(self, force=False):
        def refresh_available(force):
            lv.lock()
            self.screen_ota_rinkhals.panel_versions.clean()
            lv.unlock()

            rinkhals_current = Rinkhals.get_current_version()
            rinkhals_installed = Rinkhals.get_installed_versions()

            if force or not self.cache_rinkhals_available:
                include_test_versions = self.screen_ota_rinkhals.checkbox_include_test.get_checked()
                self.cache_rinkhals_available = Rinkhals.get_available_versions(include_test_versions)

            rinkhals_versions = self.cache_rinkhals_available
            if rinkhals_current:
                rinkhals_versions_current = ([ v for v in rinkhals_versions if v.version == rinkhals_current.version ] or [None])[0]
                if not rinkhals_versions_current:
                    rinkhals_versions.insert(0, rinkhals_current)
                else:
                    rinkhals_versions_current.path = rinkhals_current.path

            rinkhals_versions.sort(key=lambda v: v.version, reverse=True)

            test_done = False
            latest_done = False

            for v in rinkhals_versions:
                lv.lock()

                panel_version = lvr.panel(self.screen_ota_rinkhals.panel_versions)
                panel_version.set_size(lv.pct(100), lv.dpx(70))
                panel_version.set_style_border_side(lv.BORDER_SIDE.BOTTOM, lv.STATE.DEFAULT)
                panel_version.add_event_cb(lambda e, v=v: self.show_ota_rinkhals_modal(v), lv.EVENT_CODE.CLICKED, None)
                panel_version.set_state(lv.STATE.DISABLED, False)

                label_version = lvr.label(panel_version)
                label_version.set_align(lv.ALIGN.LEFT_MID)
                label_version.set_text(v.version)

                if rinkhals_current and v.version == rinkhals_current.version:
                    if v.version != 'dev':
                        test_done = True
                        latest_done = True

                    tag_version = lvr.tag(panel_version)
                    tag_version.set_align(lv.ALIGN.RIGHT_MID)
                    tag_version.remove_flag(lv.OBJ_FLAG.CLICKABLE)
                    tag_version.set_color(lvr.COLOR_PRIMARY)
                    tag_version.set_icon('')
                    tag_version.set_text('Current')
                elif any([ i for i in rinkhals_installed if v.version == i.version ]):
                    if not v.test:
                        latest_done = True

                    tag_version = lvr.tag(panel_version)
                    tag_version.set_align(lv.ALIGN.RIGHT_MID)
                    tag_version.remove_flag(lv.OBJ_FLAG.CLICKABLE)
                    tag_version.set_color(lvr.COLOR_PRIMARY)
                    tag_version.set_icon('')
                    tag_version.set_text('Installed')
                elif v.test and not test_done:
                    test_done = True

                    tag_version = lvr.tag(panel_version)
                    tag_version.set_align(lv.ALIGN.RIGHT_MID)
                    tag_version.remove_flag(lv.OBJ_FLAG.CLICKABLE)
                    tag_version.set_color(lv.color_make(200, 130, 0))
                    tag_version.set_icon('')
                    tag_version.set_text('Test')
                elif not v.test and not latest_done:
                    latest_done = True

                    tag_version = lvr.tag(panel_version)
                    tag_version.set_align(lv.ALIGN.RIGHT_MID)
                    tag_version.remove_flag(lv.OBJ_FLAG.CLICKABLE)
                    tag_version.set_color(lv.color_make(0, 180, 0))
                    tag_version.set_icon('')
                    tag_version.set_text('Latest')

                lv.unlock()
        def checkbox_include_test_cb(e):
            include_test_versions = self.screen_ota_rinkhals.checkbox_include_test.get_checked()
            self.screen_ota_rinkhals.checkbox_include_test.set_checked(not include_test_versions)
            run_async(lambda: refresh_available(True))

        self.screen_ota_rinkhals.checkbox_include_test.clear_event_cb()
        self.screen_ota_rinkhals.checkbox_include_test.add_event_cb(checkbox_include_test_cb, lv.EVENT_CODE.CLICKED, None)

        self.screen_ota_rinkhals.icon_refresh.clear_event_cb()
        self.screen_ota_rinkhals.icon_refresh.add_event_cb(lambda e: run_async(lambda: refresh_available(True)), lv.EVENT_CODE.CLICKED, None)

        run_async(lambda: refresh_available(force))
    def show_ota_firmware(self):
        def refresh_available(force):
            lv.lock()
            self.screen_ota_firmware.panel_versions.clean()
            lv.unlock()

            firmware_current = Firmware.get_current_version()

            if force or not self.cache_firmware_available:
                self.cache_firmware_latest = Firmware.get_latest_version()
                self.cache_firmware_available = Firmware.get_available_versions()

            firmware_versions = self.cache_firmware_available
            if self.cache_firmware_latest:
                firmware_versions_latest = ([ v for v in firmware_versions if v.version == self.cache_firmware_latest.version ] or [None])[0]
                if not firmware_versions_latest:
                    firmware_versions.insert(0, self.cache_firmware_latest)
                else:
                    firmware_versions_latest.url = self.cache_firmware_latest.url
            
            if firmware_current:
                firmware_versions_current = ([ v for v in firmware_versions if v.version == firmware_current ] or [None])[0]
                if not firmware_versions_current:
                    version = FirmwareVersion()
                    version.version = firmware_current
                    version.date = None
                    version.changes = None
                    version.url = None
                    firmware_versions.insert(0, version)

            firmware_versions.sort(key=lambda v: v.version, reverse=True)

            latest_done = False

            for v in firmware_versions:
                lv.lock()

                panel_version = lvr.panel(self.screen_ota_firmware.panel_versions)
                panel_version.set_size(lv.pct(100), lv.dpx(70))
                panel_version.set_style_border_side(lv.BORDER_SIDE.BOTTOM, lv.STATE.DEFAULT)

                if v.url:
                    panel_version.set_state(lv.STATE.DISABLED, False)
                    panel_version.add_event_cb(lambda e, v=v: self.show_ota_firmware_modal(v), lv.EVENT_CODE.CLICKED, None)

                label_version = lvr.label(panel_version)
                label_version.set_align(lv.ALIGN.TOP_LEFT if v.date else lv.ALIGN.LEFT_MID)
                label_version.set_text(v.version)

                if v.date:
                    label_date = lvr.subtitle(panel_version)
                    label_date.set_align(lv.ALIGN.BOTTOM_LEFT)
                    label_date.set_style_text_color(lvr.COLOR_DISABLED, lv.STATE.DEFAULT)
                    from datetime import datetime
                    label_date.set_text(f'Date: {datetime.fromtimestamp(v.date).strftime("%Y-%m-%d")}')

                if firmware_current and v.version == firmware_current:
                    latest_done = True

                    tag_version = lvr.tag(panel_version)
                    tag_version.set_align(lv.ALIGN.RIGHT_MID)
                    tag_version.remove_flag(lv.OBJ_FLAG.CLICKABLE)
                    tag_version.set_color(lvr.COLOR_PRIMARY)
                    tag_version.set_icon('')
                    tag_version.set_text('Current')
                elif not latest_done:
                    latest_done = True

                    tag_version = lvr.tag(panel_version)
                    tag_version.set_align(lv.ALIGN.RIGHT_MID)
                    tag_version.remove_flag(lv.OBJ_FLAG.CLICKABLE)
                    tag_version.set_color(lv.color_make(0, 180, 0))
                    tag_version.set_icon('')
                    tag_version.set_text('Latest')

                lv.unlock()

        self.screen_ota_firmware.icon_refresh.clear_event_cb()
        self.screen_ota_firmware.icon_refresh.add_event_cb(lambda e: run_async(lambda: refresh_available(True)), lv.EVENT_CODE.CLICKED, None)

        run_async(lambda: refresh_available(False))
    def show_ota_rinkhals_modal(self, version: RinkhalsVersion):
        self.modal_ota_rinkhals.label_title.set_text(f'Rinkhals {version.version}')

        changes = version.changes or ''
        changes = changes.replace('\r\n', '\n')
        changes = changes.splitlines()
        changes = [ l for l in changes if 'Supported printers' not in l and not l.startswith('|') ]
        changes = [ l for l in changes if 'New Contributors' not in l and not l.startswith('* @') ]
        changes = [ l for l in changes if 'Full Changelog' not in l ]
        changes = [ l for l in changes if '##' not in l ]
        changes = '\n'.join(changes)
        changes = changes.replace('\n\n\n', '\n\n')
        changes = changes.strip()

        if changes:
            self.modal_ota_rinkhals.label_description.set_text(changes)
            self.modal_ota_rinkhals.label_description.remove_flag(lv.OBJ_FLAG.HIDDEN)
        else:
            self.modal_ota_rinkhals.label_description.add_flag(lv.OBJ_FLAG.HIDDEN)

        rinkhals_current = Rinkhals.get_current_version()
        rinkhals_installed = Rinkhals.get_installed_versions()

        for v in rinkhals_installed:
            if version.version == v.version:
                version.path = v.path
                break

        action_text = 'Install'
        warning_text = None
        action_uninstall = False

        if rinkhals_current and version.version == rinkhals_current.version:
            action_text = 'Re-install'
            action_uninstall = True
        elif any([ v for v in rinkhals_installed if version.version == v.version ]):
            action_text = 'Re-install'
            action_uninstall = True
        elif version.test:
            warning_text = 'This is a test version, it might not be completely stable'
        elif rinkhals_current and version.version < rinkhals_current.version:
            warning_text = 'This version is older than the currently installed one'
        elif rinkhals_current and version.version > rinkhals_current.version:
            action_text = 'Upgrade'

        if warning_text:
            self.modal_ota_rinkhals.label_warning.set_text(warning_text)
            self.modal_ota_rinkhals.label_warning.remove_flag(lv.OBJ_FLAG.HIDDEN)
        else:
            self.modal_ota_rinkhals.label_warning.add_flag(lv.OBJ_FLAG.HIDDEN)

        if action_uninstall:
            self.modal_ota_rinkhals.button_uninstall.remove_flag(lv.OBJ_FLAG.HIDDEN)
        else:
            self.modal_ota_rinkhals.button_uninstall.add_flag(lv.OBJ_FLAG.HIDDEN)

        def download_version():
            with lvr.lock():
                self.modal_ota_rinkhals.button_action.set_state(lv.STATE.DISABLED, True)
                self.modal_ota_rinkhals.button_uninstall.set_state(lv.STATE.DISABLED, True)
                self.modal_ota_rinkhals.panel_progress.remove_flag(lv.OBJ_FLAG.HIDDEN)
                self.modal_ota_rinkhals.obj_progress_bar.set_style_bg_color(lvr.COLOR_PRIMARY, lv.STATE.DEFAULT)
                self.modal_ota_rinkhals.obj_progress_bar.set_width(lv.pct(0))
                self.modal_ota_rinkhals.label_progress_text.set_text('Starting...')

            target_directory = f'{RINKHALS_BASE}/tmp'
            os.makedirs(target_directory, exist_ok=True)
            target_path = f'{target_directory}/update-download.swu' if USING_SIMULATOR else '/useremain/update.swu'

            try:
                logging.info(f'Downloading Rinkhals {version.version} from {version.url}...')

                import requests
                with requests.get(version.url, stream=True) as r:
                    r.raise_for_status()
                    with open(target_path, 'wb') as f:
                        total_length = int(r.headers.get('content-length', 0))
                        downloaded = 0
                        last_update_time = 0

                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                if self.modal_ota_rinkhals.has_flag(lv.OBJ_FLAG.HIDDEN):
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

                                    with lvr.lock():
                                        self.modal_ota_rinkhals.obj_progress_bar.set_width(lv.pct(progress))
                                        self.modal_ota_rinkhals.label_progress_text.set_text(f'{progress}% ({downloaded_mb:.1f}M / {total_mb:.1f}M)')

                logging.info('Download completed.')

                if version.sha256:
                    with lvr.lock():
                        self.modal_ota_rinkhals.label_progress_text.set_text('Checking...')

                    file_sha256 = hash_sha256(target_path)
                    if file_sha256 != version.sha256:
                        raise Exception('Hash check failed')

                with lvr.lock():
                    self.modal_ota_rinkhals.obj_progress_bar.set_width(lv.pct(100))
                    self.modal_ota_rinkhals.label_progress_text.set_text('Ready to install')
                    self.modal_ota_rinkhals.button_action.set_text(action_text)
                    self.modal_ota_rinkhals.button_action.set_style_text_color(lvr.COLOR_DANGER if warning_text else lvr.COLOR_TEXT, lv.STATE.DEFAULT)
                    self.modal_ota_rinkhals.button_action.clear_event_cb()
                    self.modal_ota_rinkhals.button_action.add_event_cb(lambda e: run_async(install_version), lv.EVENT_CODE.CLICKED, None)
            except Exception as e:
                logging.info(f'Download failed. {e}')

                with lvr.lock():
                    self.modal_ota_rinkhals.obj_progress_bar.set_style_bg_color(lvr.COLOR_DANGER, lv.STATE.DEFAULT)
                    self.modal_ota_rinkhals.label_progress_text.set_text('Failed')
                
            with lvr.lock():
                self.modal_ota_rinkhals.button_uninstall.set_state(lv.STATE.DISABLED, False)
                self.modal_ota_rinkhals.button_action.set_state(lv.STATE.DISABLED, False)
        def install_version():
            for i in range(1):
                with lvr.lock():
                    self.modal_ota_rinkhals.button_action.set_state(lv.STATE.DISABLED, True)
                    self.modal_ota_rinkhals.button_uninstall.set_state(lv.STATE.DISABLED, True)
                    self.root_modal.clear_event_cb()

                logging.info(f'Extracting Rinkhals update...')
                with lvr.lock():
                    self.modal_ota_rinkhals.label_progress_text.set_text('Extracting...')

                if USING_SIMULATOR:
                    time.sleep(1)
                else:
                    if not self.extract_swu():
                        break

                logging.info('Starting Rinkhals update...')
                with lvr.lock():
                    self.modal_ota_rinkhals.label_progress_text.set_text('Installing...')

                if USING_SIMULATOR:
                    time.sleep(1)
                    self.quit()
                else:
                    self.install_swu('async')

                return
            
            lv.lock()
            self.modal_ota_rinkhals.obj_progress_bar.set_style_bg_color(lvr.COLOR_DANGER, lv.STATE.DEFAULT)
            self.modal_ota_rinkhals.label_progress_text.set_text('Extraction failed')
            self.modal_ota_rinkhals.button_action.set_state(lv.STATE.DISABLED, False)
            self.modal_ota_rinkhals.button_uninstall.set_state(lv.STATE.DISABLED, False)
            lv.unlock()
        def uninstall_version():
            lv.lock()
            self.modal_ota_rinkhals.button_action.set_state(lv.STATE.DISABLED, True)
            self.modal_ota_rinkhals.button_uninstall.set_state(lv.STATE.DISABLED, True)
            self.modal_ota_rinkhals.panel_progress.remove_flag(lv.OBJ_FLAG.HIDDEN)
            self.modal_ota_rinkhals.obj_progress_bar.set_style_bg_color(lvr.COLOR_PRIMARY, lv.STATE.DEFAULT)
            self.modal_ota_rinkhals.obj_progress_bar.set_width(lv.pct(0))
            self.modal_ota_rinkhals.label_progress_text.set_text('Removing files...')
            self.root_modal.clear_event_cb()
            lv.unlock()

            logging.info(f'Removing Rinkhals {version.version} from {version.path}...')
            import shutil
            shutil.rmtree(version.path, ignore_errors=True)
            logging.info(f'Removed Rinkhals {version.version} from {version.path}')

            self.hide_modal()
            self.show_screen(self.screen_ota_rinkhals)
            self.layout_ota_rinkhals(force=True)

        self.modal_ota_rinkhals.panel_progress.add_flag(lv.OBJ_FLAG.HIDDEN)
        self.modal_ota_rinkhals.button_action.set_text('Download')
        self.modal_ota_rinkhals.button_action.set_style_text_color(lvr.COLOR_TEXT, lv.STATE.DEFAULT)
        self.modal_ota_rinkhals.button_action.set_state(lv.STATE.DISABLED, False)
        self.modal_ota_rinkhals.button_action.clear_event_cb()
        self.modal_ota_rinkhals.button_action.add_event_cb(lambda e: run_async(download_version), lv.EVENT_CODE.CLICKED, None)
        self.modal_ota_rinkhals.button_uninstall.add_event_cb(lambda e: run_async(uninstall_version), lv.EVENT_CODE.CLICKED, None)

        self.root_modal.add_event_cb(lambda e: self.hide_modal(), lv.EVENT_CODE.CLICKED, None)
        self.show_modal(self.modal_ota_rinkhals)
    def show_ota_firmware_modal(self, version: FirmwareVersion):
        self.modal_ota_firmware.label_title.set_text(version.version)

        changes = version.changes or ''
        changes = changes.strip()

        if changes:
            self.modal_ota_firmware.label_description.set_text(changes)
            self.modal_ota_firmware.label_description.remove_flag(lv.OBJ_FLAG.HIDDEN)
        else:
            self.modal_ota_firmware.label_description.add_flag(lv.OBJ_FLAG.HIDDEN)

        firmware_current = Firmware.get_current_version()
        if firmware_current and version.version < firmware_current:
            warning_test = 'This version is older than the currently installed one'
        else:
            warning_test = None

        if warning_test:
            self.modal_ota_firmware.label_warning.set_text(warning_test)
            self.modal_ota_firmware.label_warning.remove_flag(lv.OBJ_FLAG.HIDDEN)
        else:
            self.modal_ota_firmware.label_warning.add_flag(lv.OBJ_FLAG.HIDDEN)

        def download_version():
            lv.lock()
            self.modal_ota_firmware.button_action.set_state(lv.STATE.DISABLED, True)
            self.modal_ota_firmware.panel_progress.remove_flag(lv.OBJ_FLAG.HIDDEN)
            self.modal_ota_firmware.obj_progress_bar.set_style_bg_color(lvr.COLOR_PRIMARY, lv.STATE.DEFAULT)
            self.modal_ota_firmware.obj_progress_bar.set_width(lv.pct(0))
            self.modal_ota_firmware.label_progress_text.set_text('Starting...')
            lv.unlock()

            target_directory = f'{RINKHALS_BASE}/tmp'
            os.makedirs(target_directory, exist_ok=True)
            target_path = f'{target_directory}/update-download.swu' if USING_SIMULATOR else '/useremain/update.swu'

            try:
                logging.info(f'Downloading Rinkhals {version.version} from {version.url}...')

                import requests

                printer_info = PrinterInfo.get()
                current_version = Rinkhals.get_current_version()

                headers = {
                    'User-Agent': f'Rinkhals/{current_version.version if current_version else "Unknown"} ({printer_info.model_code if printer_info else "Unknown"})'
                }

                if 'anycubic' in version.url:
                    headers = {}

                with requests.get(version.url, stream=True, headers=headers) as r:
                    r.raise_for_status()
                    with open(target_path, 'wb') as f:
                        downloaded = 0
                        last_update_time = 0

                        estimate = False
                        total_length = r.headers.get('content-length')
                        if total_length:
                            total_length = int(total_length)
                        else:
                            estimate = True
                            total_length = 150 * 1024 * 1024

                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                if self.modal_ota_firmware.has_flag(lv.OBJ_FLAG.HIDDEN):
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
                                    self.modal_ota_firmware.obj_progress_bar.set_width(lv.pct(progress))
                                    if estimate:
                                        self.modal_ota_firmware.label_progress_text.set_text(f'~{progress}% ({downloaded_mb:.1f}M / ~{total_mb:.1f}M)')
                                    else:
                                        self.modal_ota_firmware.label_progress_text.set_text(f'{progress}% ({downloaded_mb:.1f}M / {total_mb:.1f}M)')
                                    lv.unlock()

                logging.info('Download completed.')

                lv.lock()
                self.modal_ota_firmware.obj_progress_bar.set_width(lv.pct(100))
                self.modal_ota_firmware.label_progress_text.set_text('Ready to install')
                self.modal_ota_firmware.button_action.set_text('Install')
                self.modal_ota_firmware.button_action.set_style_text_color(lvr.COLOR_DANGER if warning_test else lvr.COLOR_TEXT, lv.STATE.DEFAULT)
                self.modal_ota_firmware.button_action.clear_event_cb()
                self.modal_ota_firmware.button_action.add_event_cb(lambda e: run_async(install_version), lv.EVENT_CODE.CLICKED, None)
                lv.unlock()
            except Exception as e:
                logging.info(f'Download failed. {e}')

                lv.lock()
                self.modal_ota_firmware.obj_progress_bar.set_style_bg_color(lvr.COLOR_DANGER, lv.STATE.DEFAULT)
                self.modal_ota_firmware.label_progress_text.set_text('Failed')
                lv.unlock()
                
            lv.lock()
            self.modal_ota_firmware.button_action.set_state(lv.STATE.DISABLED, False)
            lv.unlock()
        def install_version():
            for i in range(1):
                lv.lock()
                self.modal_ota_firmware.button_action.set_state(lv.STATE.DISABLED, True)
                self.modal_ota_firmware.button_cancel.set_state(lv.STATE.DISABLED, True)
                self.modal_ota_firmware.label_progress_text.set_text('Extracting...')
                lv.unlock()

                logging.info(f'Extracting system update...')

                if USING_SIMULATOR:
                    time.sleep(1)
                else:
                    if not self.extract_swu():
                        break

                lv.lock()
                self.modal_ota_firmware.label_progress_text.set_text('Installing...')
                lv.unlock()

                logging.info('Starting system update...')

                if USING_SIMULATOR:
                    time.sleep(1)
                    self.quit()
                else:
                    self.install_swu()

                return
            
            lv.lock()
            self.modal_ota_firmware.obj_progress_bar.set_style_bg_color(lvr.COLOR_DANGER, lv.STATE.DEFAULT)
            self.modal_ota_firmware.label_progress_text.set_text('Extraction failed')
            self.modal_ota_firmware.button_action.set_state(lv.STATE.DISABLED, False)
            self.modal_ota_firmware.button_cancel.set_state(lv.STATE.DISABLED, False)
            lv.unlock()

        self.modal_ota_firmware.button_action.set_style_text_color(lvr.COLOR_TEXT, lv.STATE.DEFAULT)
        self.modal_ota_firmware.panel_progress.add_flag(lv.OBJ_FLAG.HIDDEN)
        self.modal_ota_firmware.button_cancel.set_state(lv.STATE.DISABLED, False)
        self.modal_ota_firmware.button_action.set_text('Download')
        self.modal_ota_firmware.button_action.set_state(lv.STATE.DISABLED, False)
        self.modal_ota_firmware.button_action.clear_event_cb()
        self.modal_ota_firmware.button_action.add_event_cb(lambda e: run_async(download_version), lv.EVENT_CODE.CLICKED, None)

        self.show_modal(self.modal_ota_firmware)

    def extract_swu(self):
        if self.printer_info.model_code == 'K2P' or self.printer_info.model_code == 'K3' or self.printer_info.model_code == 'K3V2':
            password = 'U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w='
        elif self.printer_info.model_code == 'KS1' or self.printer_info.model_code == 'KS1M':
            password = 'U2FsdGVkX1+lG6cHmshPLI/LaQr9cZCjA8HZt6Y8qmbB7riY'
        elif self.printer_info.model_code == 'K3M':
            password = '4DKXtEGStWHpPgZm8Xna9qluzAI8VJzpOsEIgd8brTLiXs8fLSu3vRx8o7fMf4h6'
            
        if system('rm -rf /useremain/update_swu') != 0:
            return False
        if system(f'unzip -P {password} /useremain/update.swu -d /useremain') != 0:
            return False
        if system('rm /useremain/update.swu') != 0:
            return False

        if os.path.isfile('/useremain/update_swu/setup.tar.gz.md5'):
            with open('/useremain/update_swu/setup.tar.gz.md5', 'r') as f:
                theoritical_hash = f.read().strip()

            file_hash = hash_md5('/useremain/update_swu/setup.tar.gz')
            if file_hash.lower() != theoritical_hash.lower():
                logging.error('setup.tar.gz md5 doesn\'t match. Failing install.')
                return False

        if system('tar zxf /useremain/update_swu/setup.tar.gz -C /useremain/update_swu') != 0:
            return False
        if system('chmod +x /useremain/update_swu/update.sh') != 0:
            return False

        return True
    def install_swu(self, params=''):
        # Patch the update script
        with open('/useremain/update_swu/update.sh', 'r+') as f:
            update_script = f.read()
            update_script = update_script.replace('rm -rf ${swu_path}/update.swu', 'echo')
            update_script = update_script.replace('rm -f $USB_PATH/update.swu', '')
            update_script = update_script.replace('reboot', 'echo')

            f.truncate(0)
            f.seek(0)
            f.write(update_script)

        # Run the update script
        system(f'/useremain/update_swu/update.sh {params}')

        if os.path.exists('/useremain/rinkhals/.version'):
            if os.path.exists('/userdata/app/gk/start.sh'):
                with open('/userdata/app/gk/start.sh', 'r') as f:
                    script_content = f.read()
                    if 'Rinkhals/begin' not in script_content:
                        system(f'cat {SCRIPT_PATH}/start.sh.patch >> /userdata/app/gk/start.sh')
            if os.path.exists('/userdata/app/gk/restart_k3c.sh'):
                with open('/userdata/app/gk/start.sh', 'r') as f:
                    script_content = f.read()
                    if 'Rinkhals/begin' not in script_content:
                        system(f'cat {SCRIPT_PATH}/start.sh.patch >> /userdata/app/gk/restart_k3c.sh')

        # Store the reboot marker
        os.makedirs('/useremain/rinkhals', exist_ok=True)
        open('/useremain/rinkhals/.reboot-marker', 'w').close()

        # Sync and reboot
        system('sync && reboot')
