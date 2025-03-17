import os
import configparser
import base64
import subprocess
import hashlib
import json
import paho.mqtt.client as mqtt
import urllib
import time
import ssl
import uuid
import traceback

from datetime import datetime


LOG_DEBUG = 0
LOG_INFO = 1
LOG_WARNING = 2
LOG_ERROR = 3

LOG_LEVEL = LOG_DEBUG if not not os.getenv('DEBUG') else LOG_INFO


def log(level, message):
    if level >= LOG_LEVEL:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + message, flush = True)
def md5(input: str) -> str:
    return hashlib.md5(input.encode('utf-8')).hexdigest()
def now() -> int:
    return round(time.time() * 1000)


class CloudProxy:

    # Configuration
    cloud_config = None
    api_config = None

    # Environment
    firmware_version = None
    model_id = None
    cloud_device_id = None
    lan_device_id = None

    # MQTT
    cloud_client = None
    lan_client = None

    def __init__(self):
        self.cloud_config = self.get_cloud_config()
        self.api_config = self.get_api_config()

        self.firmware_version = self.get_firmware_version()
        self.model_id = self.api_config['cloud']['modelId']
        self.cloud_device_id = self.cloud_config['deviceUnionId']
        self.lan_device_id = self.get_lan_device_id()

    def get_cloud_config(self):
        config = configparser.ConfigParser()
        config.read('/userdata/app/gk/config/device.ini')

        environment = config['device']['env']
        zone = config['device']['zone']

        if zone == 'cn':
            section_name = f'cloud_{environment}'
        else:
            section_name = f'cloud_{zone}_{environment}'

        cloud_config = config[section_name]
        return cloud_config
    def get_api_config(self):
        with open('/userdata/app/gk/config/api.cfg', 'r') as f:
            return json.loads(f.read())

    def get_ssl_context(self) -> ssl.SSLContext:
        cert_path = self.cloud_config['certPath']
        cert_file = f'{cert_path}/deviceCrt'
        key_file = f'{cert_path}/devicePk'
        ca_file = f'{cert_path}/caCrt'
        
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.set_ciphers(('ALL:@SECLEVEL=0'),)
        if cert_file and key_file:
            ssl_context.load_cert_chain(cert_file, key_file, None)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        if ca_file:
            ssl_context.load_verify_locations(ca_file)

        return ssl_context
    def get_firmware_version(self) -> str:
        with open('/useremain/dev/version', 'r') as f:
            return f.read().strip()
    def get_lan_device_id(self) -> str:
        with open('/useremain/dev/device_id', 'r') as f:
            return f.read()

    def get_cloud_mqtt_credentials(self):
        device_key = self.cloud_config['deviceKey']
        cert_path = self.cloud_config['certPath']

        command = f'printf "{device_key}" | openssl rsautl -encrypt -inkey {cert_path}/caCrt -certin -pkcs | base64 -w 0'
        encrypted_device_key = subprocess.check_output(['sh', '-c', command])
        encrypted_device_key = encrypted_device_key.decode('utf-8').strip()

        taco = f'{self.cloud_device_id}{encrypted_device_key}{self.cloud_device_id}'
        username = f'dev|fdm|{self.model_id}|{md5(taco)}'

        return (username, encrypted_device_key)
    def get_lan_mqtt_credentials(self):
        with open('/userdata/app/gk/config/device_account.json', 'r') as f:
            json_data = f.read()
            data = json.loads(json_data)

            mqtt_username = data['username']
            mqtt_password = data['password']

        return (mqtt_username, mqtt_password)

    def send_message(self, client, topic, payload):
        mode = 'cloud' if client == self.cloud_client else 'lan'

        log(LOG_DEBUG, f'[{mode}] Sent {topic} = {str(payload)}')

        response = topic.endswith('/response')
        report = topic.endswith('/report')
        
        if not response:
            if report:
                log(LOG_INFO, f'[{mode}] Sent report for {payload.get("type")}/{payload.get("action")}')
            else:
                log(LOG_INFO, f'[{mode}] Sent {payload.get("type")}/{payload.get("action")}')

        client.publish(topic, json.dumps(payload))

    def on_cloud_message(self, topic, payload):
        log(LOG_DEBUG, f'[cloud] Received {topic} = {str(payload)}')

        if not topic.endswith('/response'):
            if topic.endswith('/report'):
                log(LOG_INFO, f'[cloud] Received report for {payload.get("type")}/{payload.get("action")}')
            else:
                log(LOG_INFO, f'[cloud] Received {payload.get("type")}/{payload.get("action")}')

        if not topic.endswith('/response'):
            self.send_message(self.lan_client, topic.replace(self.cloud_device_id, self.lan_device_id), payload)
    def on_lan_message(self, topic, payload):
        log(LOG_DEBUG, f'[lan] Received {topic} = {str(payload)}')
 
        if not topic.endswith('/response'):
            if topic.endswith('/report'):
                log(LOG_INFO, f'[lan] Received report for {payload.get("type")}/{payload.get("action")}')
            else:
                log(LOG_INFO, f'[lan] Received {payload.get("type")}/{payload.get("action")}')

        if topic.endswith('/report') or topic.endswith('/response'):
            self.send_message(self.cloud_client, topic.replace(self.lan_device_id, self.cloud_device_id), payload)

    def connect_cloud_mqtt(self):
        mqtt_broker = self.cloud_config['mqttBroker']
        mqtt_username, mqtt_password = self.get_cloud_mqtt_credentials()

        def mqtt_on_connect(client, userdata, connect_flags, reason_code, properties):
            log(LOG_INFO, '[cloud] Connected')
            self.cloud_client.subscribe(f'anycubic/anycubicCloud/v1/+/printer/{self.model_id}/{self.cloud_device_id}/#')
        def mqtt_on_connect_fail(client, userdata):
            log(LOG_INFO, '[cloud] Failed to connect')
        def mqtt_on_log(client, userdata, level, buf):
            #log(LOG_DEBUG, buf)
            pass
        def mqtt_on_message(client, userdata, msg):
            self.on_cloud_message(msg.topic, json.loads(msg.payload.decode("utf-8")))

        mqtt_broker_endpoint = urllib.parse.urlparse(mqtt_broker)

        self.cloud_client = mqtt.Client(protocol=mqtt.MQTTv5, client_id=self.cloud_device_id)
        self.cloud_client.enable_logger()

        if mqtt_broker_endpoint.scheme == 'ssl':
            self.cloud_client.tls_set_context(self.get_ssl_context())
            self.cloud_client.tls_insecure_set(True)

        self.cloud_client.on_connect = mqtt_on_connect
        self.cloud_client.on_connect_fail = mqtt_on_connect_fail
        self.cloud_client.on_message = mqtt_on_message
        self.cloud_client.on_log = mqtt_on_log

        self.cloud_client.username_pw_set(mqtt_username, mqtt_password)
        self.cloud_client.connect(mqtt_broker_endpoint.hostname, mqtt_broker_endpoint.port or 1883)
        self.cloud_client.loop_start()

        while not self.cloud_client.is_connected():
            time.sleep(0.25)
    def connect_lan_mqtt(self):
        mqtt_username, mqtt_password = self.get_lan_mqtt_credentials()

        def mqtt_on_connect(client, userdata, connect_flags, reason_code, properties):
            log(LOG_INFO, '[lan] Connected')
            self.lan_client.subscribe(f'anycubic/anycubicCloud/v1/printer/public/{self.model_id}/{self.lan_device_id}/#')
        def mqtt_on_connect_fail(client, userdata):
            log(LOG_INFO, '[lan] Failed to connect')
        def mqtt_on_log(client, userdata, level, buf):
            #log(LOG_DEBUG, buf)
            pass
        def mqtt_on_message(client, userdata, msg):
            self.on_lan_message(msg.topic, json.loads(msg.payload.decode("utf-8")))

        self.lan_client = mqtt.Client(protocol=mqtt.MQTTv5, client_id=self.lan_device_id)
        self.lan_client.enable_logger()

        self.lan_client.tls_set_context(self.get_ssl_context())
        self.lan_client.tls_insecure_set(True)

        self.lan_client.on_connect = mqtt_on_connect
        self.lan_client.on_connect_fail = mqtt_on_connect_fail
        self.lan_client.on_message = mqtt_on_message
        self.lan_client.on_log = mqtt_on_log

        self.lan_client.username_pw_set(mqtt_username, mqtt_password)
        self.lan_client.connect('127.0.0.1', 9883)
        self.lan_client.loop_start()

        while not self.lan_client.is_connected():
            time.sleep(0.25)
    
    def main(self):

        self.connect_cloud_mqtt()
        self.connect_lan_mqtt()

        payload = {
            'type': 'lastWill',
            'action': 'onlineReport',
            'timestamp': now(),
            'msgid': str(uuid.uuid4()),
            'state': 'online',
            'code': 200,
            'msg': 'device online',
            'data': None
        }
        self.send_message(self.cloud_client, f'anycubic/anycubicCloud/v1/printer/public/{self.model_id}/{self.cloud_device_id}/lastWill/report', payload)

        payload = {
            'type': 'status',
            'action': 'workReport',
            'timestamp': now(),
            'msgid': str(uuid.uuid4()),
            'state': 'free',
            'code': 200,
            'msg': '',
            'data': None
        }
        self.send_message(self.cloud_client, f'anycubic/anycubicCloud/v1/printer/public/{self.model_id}/{self.cloud_device_id}/status/report', payload)

        payload = {
            'type': 'ota',
            'action': 'reportVersion',
            'timestamp': now(),
            'msgid': str(uuid.uuid4()),
            'state': 'done',
            'code': 200,
            'msg': 'done',
            'data': {
                'device_unionid': self.cloud_device_id,
                'machine_version': '1.1.0',
                'peripheral_version': '',
                'firmware_version': self.firmware_version,
                'model_id': self.model_id
            }
        }
        self.send_message(self.cloud_client, f'anycubic/anycubicCloud/v1/printer/public/{self.model_id}/{self.cloud_device_id}/ota/report', payload)

        while True:
            time.sleep(1)


if __name__ == "__main__":
    try:
        cloud_proxy = CloudProxy()
        cloud_proxy.main()
    except Exception as e:
        log(LOG_ERROR, str(e))
        log(LOG_ERROR, traceback.format_exc())
        os.kill(os.getpid(), 9)
