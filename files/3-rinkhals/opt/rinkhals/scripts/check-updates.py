import os
import sys
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


def md5(input: str) -> str:
    return hashlib.md5(input.encode('utf-8')).hexdigest()
def now() -> int:
    return round(time.time() * 1000)


class Program:

    # Configuration
    cloud_config = None
    api_config = None

    # Environment
    firmware_version = None
    model_id = None
    cloud_device_id = None

    # MQTT
    cloud_client = None

    def __init__(self):
        self.cloud_config = self.get_cloud_config()
        self.api_config = self.get_api_config()

        self.firmware_version = self.get_firmware_version()
        self.model_id = self.api_config['cloud']['modelId']
        self.cloud_device_id = self.cloud_config['deviceUnionId']

        args = sys.argv
        if len(args) > 1:
            if args[1].isdigit():
                self.model_id = args[1]
                self.firmware_version = '1.2.3.4'
            elif args[1] == 'K2P':
                self.model_id = '20021'
                self.firmware_version = '3.1.4'
            elif args[1] == 'K3':
                self.model_id = '20024'
                self.firmware_version = '2.3.8.9'
            elif args[1] == 'KS1':
                self.model_id = '20025'
                self.firmware_version = '2.5.1.6'
            elif args[1] == 'K3M':
                self.model_id = '20026'
                self.firmware_version = '1.2.3.4'

            if len(args) > 2:
                self.firmware_version = args[2]

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

    def get_cloud_mqtt_credentials(self):
        device_key = self.cloud_config['deviceKey']
        cert_path = self.cloud_config['certPath']

        command = f'printf "{device_key}" | openssl rsautl -encrypt -inkey {cert_path}/caCrt -certin -pkcs | base64 -w 0'
        encrypted_device_key = subprocess.check_output(['sh', '-c', command])
        encrypted_device_key = encrypted_device_key.decode('utf-8').strip()

        taco = f'{self.cloud_device_id}{encrypted_device_key}{self.cloud_device_id}'
        username = f'dev|fdm|{self.model_id}|{md5(taco)}'

        return (username, encrypted_device_key)

    def main(self):

        mqtt_broker = self.cloud_config['mqttBroker']
        mqtt_username, mqtt_password = self.get_cloud_mqtt_credentials()

        def mqtt_on_connect(client, userdata, connect_flags, reason_code, properties):
            self.cloud_client.subscribe(f'anycubic/anycubicCloud/v1/+/printer/{self.model_id}/{self.cloud_device_id}/ota')
            
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
            self.cloud_client.publish(f'anycubic/anycubicCloud/v1/printer/public/{self.model_id}/{self.cloud_device_id}/ota/report', json.dumps(payload))
        def mqtt_on_connect_fail(client, userdata):
            self.cloud_client.disconnect()
            sys.exit(1)
        def mqtt_on_message(client, userdata, msg):
            ota = msg.payload.decode("utf-8")
            ota = json.loads(ota)
            data = ota.get('data')

            if data:
                print(json.dumps(data))

            self.cloud_client.disconnect()
            sys.exit(0)

        mqtt_broker_endpoint = urllib.parse.urlparse(mqtt_broker)

        self.cloud_client = mqtt.Client(protocol=mqtt.MQTTv5, client_id=self.cloud_device_id)

        if mqtt_broker_endpoint.scheme == 'ssl':
            self.cloud_client.tls_set_context(self.get_ssl_context())
            self.cloud_client.tls_insecure_set(True)

        self.cloud_client.on_connect = mqtt_on_connect
        self.cloud_client.on_connect_fail = mqtt_on_connect_fail
        self.cloud_client.on_message = mqtt_on_message

        self.cloud_client.username_pw_set(mqtt_username, mqtt_password)
        self.cloud_client.connect(mqtt_broker_endpoint.hostname, mqtt_broker_endpoint.port or 1883)
        self.cloud_client.loop_forever()


if __name__ == "__main__":
    try:
        program = Program()
        program.main()
    except Exception as e:
        print(traceback.format_exc())
        sys.exit(1)
