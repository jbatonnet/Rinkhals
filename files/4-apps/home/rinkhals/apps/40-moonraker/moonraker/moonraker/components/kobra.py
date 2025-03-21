import os
import sys
import uuid
import json
import time
import logging
import subprocess
from datetime import datetime

import paho.mqtt.client as paho

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

        n = 0
        while not self.mqtt_print_report:
            n = n + 1
            if n == 50:
                logging.error(f'Timeout trying to print {file}')
                return f'Timeout trying to print {file}'

            client.loop(timeout = 0.1)

        client.disconnect()

        if self.mqtt_print_error:
            raise(Exception(self.mqtt_print_error))

def load_component(config):
    return Kobra(config)
