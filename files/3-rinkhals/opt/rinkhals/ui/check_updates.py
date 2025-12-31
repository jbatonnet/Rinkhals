import os
import sys
import configparser
import subprocess
import hashlib
import json
import paho.mqtt.client as mqtt
import urllib
import time
import ssl
import uuid
import traceback
import base64


def md5(input: str) -> str:
    return hashlib.md5(input.encode('utf-8')).hexdigest()
def now() -> int:
    return round(time.time() * 1000)


ORIGINAL_LD_LIBRARY_PATH = os.environ.get('LD_LIBRARY_PATH', '')
LD_LIBRARY_PATH = ORIGINAL_LD_LIBRARY_PATH.split(':')
LD_LIBRARY_PATH = [ p for p in LD_LIBRARY_PATH if not p.startswith('/tmp') ]
LD_LIBRARY_PATH = ':'.join(LD_LIBRARY_PATH)


class CheckUpdateProgram:

    # Configuration
    cloud_config = None
    api_config = None

    # Environment
    firmware_version = None
    model_id = None
    cloud_device_id = None

    # MQTT
    cloud_client = None
    mqtt_result = None
    mqtt_error = None

    def __init__(self):
        self.cloud_config = self.get_cloud_config()
        self.api_config = self.get_api_config()

    def get_cloud_config(self):
        cloud_config_content = None

        if os.path.exists('/userdata/app/gk/config/device.ini'):
            with open('/userdata/app/gk/config/device.ini', 'r') as f:
                cloud_config_content = f.read()

        if 'CERTS_DEVICE_INI' in os.environ:
            cloud_config_content = os.environ['CERTS_DEVICE_INI']

        config = configparser.ConfigParser()
        config.read_string(cloud_config_content)

        environment = config['device']['env']
        zone = config['device']['zone']

        if zone == 'cn':
            section_name = f'cloud_{environment}'
        else:
            section_name = f'cloud_{zone}_{environment}'

        cloud_config = config[section_name]
        return cloud_config
    def get_api_config(self):
        if not os.path.exists('/userdata/app/gk/config/api.cfg'):
            return None
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
        if not os.path.exists('/useremain/dev/version'):
            return None
        with open('/useremain/dev/version', 'r') as f:
            return f.read().strip()
    def get_cloud_mqtt_credentials(self):
        device_key = self.cloud_config['deviceKey']
        cert_path = self.cloud_config['certPath']

        os.environ['LD_LIBRARY_PATH'] = LD_LIBRARY_PATH

        command = f'printf "{device_key}" | openssl rsautl -encrypt -inkey {cert_path}/caCrt -certin -pkcs | xxd -p -c 256'
        encrypted_device_key = subprocess.check_output(['sh', '-c', command])
        encrypted_device_key = encrypted_device_key.decode().strip()
        encrypted_device_key = bytes.fromhex(encrypted_device_key)
        encrypted_device_key = base64.b64encode(encrypted_device_key).decode()

        os.environ['LD_LIBRARY_PATH'] = ORIGINAL_LD_LIBRARY_PATH

        taco = f'{self.cloud_device_id}{encrypted_device_key}{self.cloud_device_id}'
        username = f'dev|fdm|{self.model_id}|{md5(taco)}'

        return (username, encrypted_device_key)

    def get_latest_update(self, model_code=None, current_version=None):
        self.firmware_version = self.get_firmware_version()
        self.model_id = self.api_config['cloud']['modelId'] if self.api_config else None
        self.cloud_device_id = self.cloud_config['deviceUnionId']

        if 'CERTS_CACRT' in os.environ and 'CERTS_DEVICECRT' in os.environ and 'CERTS_DEVICEPK' in os.environ:
            cert_path = '/tmp/rinkhals/certs'

            os.makedirs(cert_path)
            self.cloud_config['certPath'] = cert_path

            with open(f'{cert_path}/caCrt', 'w') as f:
                f.write(os.environ['CERTS_CACRT'])
            with open(f'{cert_path}/deviceCrt', 'w') as f:
                f.write(os.environ['CERTS_DEVICECRT'])
            with open(f'{cert_path}/devicePk', 'w') as f:
                f.write(os.environ['CERTS_DEVICEPK'])

        if model_code:
            if model_code == 'K2P':
                self.model_id = '20021'
                self.firmware_version = '3.1.4'
            elif model_code == 'K3':
                self.model_id = '20024'
                self.firmware_version = '2.4.0.4'
            elif model_code == 'KS1':
                self.model_id = '20025'
                self.firmware_version = '2.5.3.5'
            elif model_code == 'K3M':
                self.model_id = '20026'
                self.firmware_version = '2.4.6.5'
            elif model_code == 'K3V2':
                self.model_id = '20027'
                self.firmware_version = '1.0.5.8'
            elif model_code == 'KS1M':
                self.model_id = '20029'
                self.firmware_version = '0.1.2.3'
            elif model_code.isdigit():
                self.model_id = model_code
                self.firmware_version = '1.2.3.4'
            else:
                return None
            
        if current_version:
            self.firmware_version = current_version

        mqtt_broker = self.cloud_config['mqttBroker']
        mqtt_username, mqtt_password = self.get_cloud_mqtt_credentials()

        self.mqtt_result = None
        self.mqtt_error = None

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
            self.mqtt_error = 'Failed to connect to Anycubic MQTT server'
            self.cloud_client.disconnect()
        def mqtt_on_message(client, userdata, msg):
            ota = msg.payload.decode("utf-8")
            ota = json.loads(ota)
            data = ota.get('data') if ota else None

            self.mqtt_result = json.dumps(data) if data else ''
            self.cloud_client.disconnect()

        mqtt_broker_endpoint = urllib.parse.urlparse(mqtt_broker)

        self.cloud_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5, client_id=self.cloud_device_id)

        if mqtt_broker_endpoint.scheme == 'ssl':
            self.cloud_client.tls_set_context(self.get_ssl_context())
            self.cloud_client.tls_insecure_set(True)

        self.cloud_client.on_connect = mqtt_on_connect
        self.cloud_client.on_connect_fail = mqtt_on_connect_fail
        self.cloud_client.on_message = mqtt_on_message

        self.cloud_client.username_pw_set(mqtt_username, mqtt_password)
        self.cloud_client.connect(mqtt_broker_endpoint.hostname, mqtt_broker_endpoint.port or 1883)
        self.cloud_client.loop_forever()

        return (self.mqtt_result, self.mqtt_error)
        
    def main(self):
        model_code = os.environ.get('MODEL_CODE')
        current_version = os.environ.get('CURRENT_VERSION')

        args = sys.argv
        if len(args) > 1:
            model_code = args[1]
        if len(args) > 2:
            current_version = args[2]

        (result, error) = self.get_latest_update(model_code, current_version)

        if not error:
            if result:
                print(result)
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    try:
        program = CheckUpdateProgram()
        program.main()
    except Exception as e:
        print(traceback.format_exc())
        sys.exit(1)
