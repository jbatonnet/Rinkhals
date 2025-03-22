import os
import sys
import uuid
import json
import re
import time
import logging
import subprocess
from datetime import datetime
import paho.mqtt.client as paho
from ..utils import Sentinel

class Kobra:
    # Environment
    KOBRA_MODEL_ID = None
    KOBRA_DEVICE_ID = None
    REMOTE_MODE = 'cloud'
    MQTT_USERNAME = None
    MQTT_PASSWORD = None

    # MQTT states
    mqtt_print_report = False
    mqtt_print_error = None

    def __init__(self, config):
        self.server = config.get_server()

        try:
            command = f'. /useremain/rinkhals/.current/tools.sh && python -c "import os, json; print(json.dumps(dict(os.environ)))"'
            environment = subprocess.check_output(['sh', '-c', command])
            environment = json.loads(environment.decode('utf-8').strip())
            self.KOBRA_MODEL_ID = environment['KOBRA_MODEL_ID']
            self.KOBRA_DEVICE_ID = environment['KOBRA_DEVICE_ID']
        except:
            pass

        if os.path.isfile('/useremain/dev/remote_ctrl_mode'):
            with open('/useremain/dev/remote_ctrl_mode', 'r') as f:
                self.REMOTE_MODE = f.read().strip()

        if os.path.isfile('/userdata/app/gk/config/device_account.json'):
            with open('/userdata/app/gk/config/device_account.json', 'r') as f:
                json_data = f.read()
                data = json.loads(json_data)
                self.MQTT_USERNAME = data['username']
                self.MQTT_PASSWORD = data['password']
        
        if not self.is_using_mqtt():
            logging.warn('MQTT will not be used')

        # logging.info(f'REMOTE_MODE: {self.REMOTE_MODE}')
        # logging.info(f'KOBRA_MODEL_ID: {self.KOBRA_MODEL_ID}')
        # logging.info(f'KOBRA_DEVICE_ID: {self.KOBRA_DEVICE_ID}')
        # logging.info(f'MQTT_USERNAME: {self.MQTT_USERNAME}')
        # logging.info(f'MQTT_PASSWORD: {self.MQTT_PASSWORD}')

        for i in range(10):
            logging.debug('')
        logging.info('Starting Kobra patching...')

        #self.patch_klippy_path()
        self.patch_network_interfaces()
        self.patch_spoolman()
        self.patch_simplyprint()
        self.patch_kobra_state()
        self.patch_mqtt_print()
        self.patch_bed_mesh()
        self.patch_objects_list()
        self.patch_mainsail()
        self.patch_gcode_paths()

        logging.info('Completed Kobra patching! Yay!')
        for i in range(10):
            logging.debug('')
        
        #time.sleep(60)


    def patch_klippy_path(self):
        from .application import MoonrakerApp
        application_module = sys.modules[MoonrakerApp.__module__]

        #logging.info('> Klippy log path...')
        #setattr(application_module, 'DEFAULT_KLIPPY_LOG_PATH', '/useremain/rinkhals/.current/logs/gklib.log')
        #logging.debug(f'  DEFAULT_KLIPPY_LOG_PATH: {application_module.DEFAULT_KLIPPY_LOG_PATH}')

    def patch_network_interfaces(self):
        from .machine import Machine

        async def _parse_network_interfaces(me, sequence: int, notify: bool = True) -> None:
            logging.debug('[Kobra] Skipping call')
            return

        logging.info('> Disable network interfaces parsing...')

        logging.debug(f'  Before: {Machine._parse_network_interfaces}')
        setattr(Machine, '_parse_network_interfaces', _parse_network_interfaces)
        logging.debug(f'  After: {Machine._parse_network_interfaces}')

    def patch_spoolman(self):
        from .spoolman import SpoolManager

        def wrap_set_active_spool(original_set_active_spool):
            async def set_active_spool(me, spool_id = None, SPOOL_ID = None) -> None:
                if spool_id is None:
                    logging.info('[Kobra] Injected SPOOL_ID')
                    spool_id = int(SPOOL_ID)
                return await original_set_active_spool(me, spool_id)
            return set_active_spool

        logging.info('> Allowing SPOOL_ID parameter...')

        logging.debug(f'  Before: {SpoolManager.set_active_spool}')
        setattr(SpoolManager, 'set_active_spool', wrap_set_active_spool(SpoolManager.set_active_spool))
        logging.debug(f'  After: {SpoolManager.set_active_spool}')

    def patch_simplyprint(self):
        from ..server import Server

        def wrap_get_klippy_info(original_get_klippy_info):
            def get_klippy_info(me):
                result = original_get_klippy_info(me)
                result['klipper_path'] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
                logging.info('[Kobra] Injected klipper_path')
                return result
            return get_klippy_info

        logging.info('> Fix Simplyprint crash...')

        logging.debug(f'  Before: {Server.get_klippy_info}')
        setattr(Server, 'get_klippy_info', wrap_get_klippy_info(Server.get_klippy_info))
        logging.debug(f'  After: {Server.get_klippy_info}')

    def patch_kobra_state(self):
        from .klippy_apis import KlippyAPI
        from .klippy_connection import KlippyConnection, KlippyRequest

        def convert_kobra_state(state):
            logging.info(f'[Kobra] Converted Kobra state {state}')
            if state.lower() == 'heating':
                return 'printing'
            if state.lower() == 'onpause':
                return 'paused'
            return state

        def wrap__send_klippy_request(original__send_klippy_request):
            async def _send_klippy_request(me, method, params, default = Sentinel.MISSING, transport = None):
                result = await original__send_klippy_request(me, method, params, default, transport)
                if result and isinstance(result, dict) and 'status' in result and 'print_stats' in result['status'] and 'state' in result['status']['print_stats']:
                    result['status']['print_stats']['state'] = convert_kobra_state(result['status']['print_stats']['state'])
                return result
            return _send_klippy_request

        def wrap_send_status(original_send_status):
            def send_status(me, status, eventtime):
                if 'print_stats' in status and 'state' in status['print_stats']:
                    status['print_stats']['state'] = convert_kobra_state(status['print_stats']['state'])
                return original_send_status(me, status, eventtime)
            return send_status

        logging.info('> Automatically convert Kobra state...')

        logging.debug(f'  Before: {KlippyAPI._send_klippy_request}')
        setattr(KlippyAPI, '_send_klippy_request', wrap__send_klippy_request(KlippyAPI._send_klippy_request))
        logging.debug(f'  After: {KlippyAPI._send_klippy_request}')

        logging.debug(f'  Before: {KlippyAPI.send_status}')
        setattr(KlippyAPI, 'send_status', wrap_send_status(KlippyAPI.send_status))
        logging.debug(f'  After: {KlippyAPI.send_status}')

        def wrap__process_status_update(original__process_status_update):
            def _process_status_update(me, eventtime, status):
                if 'print_stats' in status and 'state' in status['print_stats']:
                    status['print_stats']['state'] = convert_kobra_state(status['print_stats']['state'])
                return original__process_status_update(me, eventtime, status)
            return _process_status_update

        logging.debug(f'  Before: {KlippyConnection._process_status_update}')
        setattr(KlippyConnection, '_process_status_update', wrap__process_status_update(KlippyConnection._process_status_update))
        logging.debug(f'  After: {KlippyConnection._process_status_update}')

        klippy_connection = self.server.lookup_component("klippy_connection")
        klippy_connection.unregister_method('process_status_update')
        klippy_connection.register_remote_method('process_status_update', klippy_connection._process_status_update, need_klippy_reg=False)

        def wrap_set_result(original_set_result):
            def set_result(me, result):
                if isinstance(result, dict) and 'status' in result and 'print_stats' in result['status'] and 'state' in result['status']['print_stats']:
                    result['status']['print_stats']['state'] = convert_kobra_state(result['status']['print_stats']['state'])
                original_set_result(me, result)
            return set_result

        logging.debug(f'  Before: {KlippyRequest.set_result}')
        setattr(KlippyRequest, 'set_result', wrap_set_result(KlippyRequest.set_result))
        logging.debug(f'  After: {KlippyRequest.set_result}')

    def patch_mqtt_print(self):
        from .klippy_apis import KlippyAPI

        def wrap_run_gcode(original_run_gcode):
            async def run_gcode(me, script, default = Sentinel.MISSING):
                if script.startswith('SDCARD_PRINT_FILE'):
                    script = script.replace('/useremain/app/gk/gcodes/', '')
                    script = script.replace('useremain/app/gk/gcodes/', '')
                    print(script)
                    filename = re.search("FILENAME=\"([^\"]+)\"$", script)
                    filename = filename[1] if filename else None
                    if filename and self.is_using_mqtt():
                        try:
                            self.mqtt_print_file(filename)
                        except Exception as e:
                            pass
                        return None
                return await original_run_gcode(me, script, default)
            return run_gcode

        logging.info('> Send prints to MQTT...')

        logging.debug(f'  Before: {KlippyAPI.run_gcode}')
        setattr(KlippyAPI, 'run_gcode', wrap_run_gcode(KlippyAPI.run_gcode))
        logging.debug(f'  After: {KlippyAPI.run_gcode}')

    def patch_bed_mesh(self):
        from .klippy_connection import KlippyConnection

        def wrap_request(original_request):
            async def request(me, web_request):
                rpc_method = web_request.get_endpoint()
                if rpc_method == "gcode/script":
                    script = web_request.get_str('script', "")
                    if script.lower() == "bed_mesh_map" and os.path.isfile("/userdata/app/gk/printer_data/config/printer_mutable.cfg"):
                        logging.info('[Kobra] Injected bed mesh')
                        with open("/userdata/app/gk/printer_data/config/printer_mutable.cfg", "r") as f:
                            config = json.load(f)
                            mesh = config.get("bed_mesh default")
                            if not mesh is None:
                                points = json.loads("[[" + mesh.get('points').replace("\n", "], [") + "]]")
                                return "mesh_map_output " + json.dumps({
                                    "mesh_min": (float(mesh.get('min_x')), float(mesh.get('min_y'))),
                                    "mesh_max": (float(mesh.get('max_x')), float(mesh.get('max_y'))),
                                    "z_positions": points
                                })
                            else:
                                raise self.server.error("Failed to open mesh")
                    elif script.lower().startswith("bed_mesh_calibrate"):
                        logging.info('[Kobra] Injected bed mesh calibration script')
                        web_request.get_args()["script"] = "MOVE_HEAT_POS\nM109 S140\nWIPE_NOZZLE\nBED_MESH_CALIBRATE\nSAVE_CONFIG"
                return await original_request(me, web_request)
            return request

        def wrap__request_standard(original__request_standard):
            async def _request_standard(me, web_request, timeout = None):
                args = web_request.get_args()

                # Do not send bed_mesh to goklipper, it does not support it
                want_bed_mesh = False
                if 'objects' in args and 'bed_mesh' in args['objects']:
                    want_bed_mesh = True
                    del args['objects']['bed_mesh']
                if 'objects' in args and 'bed_mesh \"default\"' in args['objects']:
                    want_bed_mesh = True
                    del args['objects']['bed_mesh \"default\"']

                result = await original__request_standard(me, web_request, timeout)

                # Add bed_mesh, so mainsail will recognize it
                if want_bed_mesh:
                    if 'status' not in result:
                        result['status'] = {}

                    result['status']['bed_mesh'] = {}
                    result['status']['bed_mesh \"default\"'] = {}

                    if os.path.isfile("/userdata/app/gk/printer_data/config/printer_mutable.cfg"):
                        with open('/userdata/app/gk/printer_data/config/printer_mutable.cfg', 'r') as f:
                            config = json.load(f)
                            mesh = config.get('bed_mesh default')
                            if not mesh is None:
                                points = json.loads("[[" + mesh.get('points').replace("\n", "], [") + "]]")

                                result['status']['bed_mesh'] = {
                                    "profile_name": "default",
                                    "mesh_min": (float(mesh.get("min_x")), float(mesh.get("min_y"))),
                                    "mesh_max": (float(mesh.get("max_x")), float(mesh.get("max_y"))),
                                    "probed_matrix": points,
                                    "mesh_matrix": points
                                }
                                result['status']['bed_mesh \"default\"'] = {
                                    "points": points,
                                    "mesh_params": {
                                        "min_x": float(mesh["min_x"]),
                                        "max_x": float(mesh["max_x"]),
                                        "min_y": float(mesh["min_y"]),
                                        "max_y": float(mesh["max_y"]),
                                        "x_count": int(mesh["x_count"]),
                                        "y_count": int(mesh["y_count"]),
                                        "mesh_x_pps": int(mesh["mesh_x_pps"]),
                                        "mesh_y_pps": int(mesh["mesh_y_pps"]),
                                        "tension": float(mesh["tension"]),
                                        "algo": mesh["algo"]
                                    }
                                }
                return result
            return _request_standard

        logging.info('> Adding Kobra bed mesh support...')

        logging.debug(f'  Before: {KlippyConnection.request}')
        setattr(KlippyConnection, 'request', wrap_request(KlippyConnection.request))
        logging.debug(f'  After: {KlippyConnection.request}')

        logging.debug(f'  Before: {KlippyConnection._request_standard}')
        setattr(KlippyConnection, '_request_standard', wrap__request_standard(KlippyConnection._request_standard))
        logging.debug(f'  After: {KlippyConnection._request_standard}')

    def patch_objects_list(self):
        from .klippy_connection import KlippyConnection

        def wrap_request(original_request):
            async def request(me, web_request):
                rpc_method = web_request.get_endpoint()
                if rpc_method == "objects/list":
                    logging.info('[Kobra] Injected objects list')
                    return {
                        "objects": [
                            "motion_report",
                            "gcode_macro pause",
                            "gcode_macro resume",
                            "gcode_macro cancel_print",
                            "gcode_macro t0",
                            "gcode_macro t1",
                            "gcode_macro t2",
                            "gcode_macro t3",
                            "configfile",
                            "heaters",
                            "respond",
                            "display_status",
                            "extruder",
                            "fan",
                            "gcode_move",
                            "heater_bed",
                            "mcu",
                            "mcu nozzle_mcu",
                            "ota_filament_hub",
                            "pause_resume",
                            "pause_resume/cancel",
                            "print_stats",
                            "toolhead",
                            "verify_heater extrude",
                            "verify_heater heater_bed",
                            "virtual_sdcard",
                            "webhooks",
                            "bed_mesh",
                            "bed_mesh \"default\""
                        ]
                    }
                return await original_request(me, web_request)
            return request

        logging.info('> Patching objects/list call...')

        logging.debug(f'  Before: {KlippyConnection.request}')
        setattr(KlippyConnection, 'request', wrap_request(KlippyConnection.request))
        logging.debug(f'  After: {KlippyConnection.request}')

    def patch_mainsail(self):
        from .klippy_connection import KlippyConnection

        def wrap__request_standard(original__request_standard):
            async def _request_standard(me, web_request, timeout = None):
                result = await original__request_standard(me, web_request, timeout)
                if 'status' in result and 'configfile' in result['status'] and 'config' in result['status']['configfile']:
                    logging.info('[Kobra] Injected Mainsail macros')
                    result['status']['configfile']['config']['gcode_macro pause'] = {}
                    result['status']['configfile']['config']['gcode_macro resume'] = {}
                    result['status']['configfile']['config']['gcode_macro cancel_print'] = {}
                return result
            return _request_standard

        logging.info('> Patching Mainsail macros...')

        logging.debug(f'  Before: {KlippyConnection._request_standard}')
        setattr(KlippyConnection, '_request_standard', wrap__request_standard(KlippyConnection._request_standard))
        logging.debug(f'  After: {KlippyConnection._request_standard}')

    def patch_gcode_paths(self):
        from .file_manager.file_manager import FileManager

        def wrap__handle_metadata_request(original__handle_metadata_request):
            async def _handle_metadata_request(me, web_request):
                if 'filename' in web_request.args:
                    logging.info('[Kobra] Replaced gcode paths')
                    web_request.args['filename'] = web_request.args['filename'].replace('/useremain/app/gk/gcodes/', '')
                return await original__handle_metadata_request(me, web_request)
            return _handle_metadata_request

        logging.info('> Patching gcode paths...')

        logging.debug(f'  Before: {FileManager._handle_metadata_request}')
        setattr(FileManager, '_handle_metadata_request', wrap__handle_metadata_request(FileManager._handle_metadata_request))
        logging.debug(f'  After: {FileManager._handle_metadata_request}')








    def is_using_mqtt(self):
        return self.REMOTE_MODE == 'lan' and self.KOBRA_MODEL_ID and self.KOBRA_DEVICE_ID and self.MQTT_USERNAME and self.MQTT_PASSWORD

    def mqtt_print_file(self, file):
        logging.info(f'Trying to print {file} using MQTT...')

        payload = """{{
            "type": "print",
            "action": "start",
            "msgid": "{0}",
            "timestamp": {1},
            "data": {{
                "taskid": "-1",
                "filename": "{2}",
                "filetype": 1
            }}
        }}""".format(uuid.uuid4(), round(time.time() * 1000), file)

        self.mqtt_print_report = False
        self.mqtt_print_error = None

        def mqtt_on_connect(client, userdata, flags, reason_code, properties):
            client.subscribe(f'anycubic/anycubicCloud/v1/printer/public/{self.KOBRA_MODEL_ID}/{self.KOBRA_DEVICE_ID}/print/report')
            client.publish(f'anycubic/anycubicCloud/v1/slicer/printer/{self.KOBRA_MODEL_ID}/{self.KOBRA_DEVICE_ID}/print', payload=payload, qos=1)

        def mqtt_on_message(client, userdata, msg):
            logging.debug(f'Received MQTT print report: {str(msg.payload)}')

            payload = json.loads(msg.payload)
            state = str(payload['state'])
            logging.info(f'Received MQTT print state: {state}')

            if state == 'failed':
                self.mqtt_print_error = str(payload['msg'])
                logging.error(f'Failed MQTT print: {self.mqtt_print_error}')

            self.mqtt_print_report = True

        client = paho.Client(protocol = paho.MQTTv5)
        client.on_connect = mqtt_on_connect
        client.on_message = mqtt_on_message

        client.username_pw_set(self.MQTT_USERNAME, self.MQTT_PASSWORD)
        client.connect('127.0.0.1', 2883)

        timeout = time.time() + 30
        while not self.mqtt_print_report:

            if time.time() > timeout:
                logging.error(f'Timeout trying to print {file}')
                return f'Timeout trying to print {file}'

            client.loop(timeout = 0.25)

        client.disconnect()

        if self.mqtt_print_error:
            raise(Exception(self.mqtt_print_error))

def load_component(config):
    return Kobra(config)
