import asyncio
import websockets
import json
import uuid
import time
import os
from datetime import datetime

import aiohttp
from aiohttp import web

import paho.mqtt.client as paho



def log(message):
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' [moonraker-proxy] ' + message, flush = True)



# User configuration
DEBUG = 'MOONRAKER_PROXY_DEBUG' in os.environ
PRINTER_IP = os.getenv('MOONRAKER_PROXY_PRINTER_IP', default = '127.0.0.1')
PROXY_PORT = os.getenv('MOONRAKER_PROXY_PORT', default = '7125')
MOONRAKER_PORT = os.getenv('MOONRAKER_PROXY_MOONRAKER_PORT', default = '7126')

# Printer configuration
PRINTER_ID = os.getenv('MOONRAKER_PROXY_PRINTER_ID')
MQTT_USERNAME = os.getenv('MOONRAKER_PROXY_MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MOONRAKER_PROXY_MQTT_PASSWORD')
REMOTE_MODE = 'lan'

# Constants
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*"
}



mqtt_print_report = False
mqtt_print_error = None

# MQTT call
async def mqtt_printfile(file):
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

    global mqtt_print_report
    global mqtt_print_error

    mqtt_print_report = False
    mqtt_print_error = None

    def mqtt_on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe('anycubic/anycubicCloud/v1/printer/public/20024/' + PRINTER_ID + '/print/report')
        client.publish('anycubic/anycubicCloud/v1/slicer/printer/20024/' + PRINTER_ID + '/print', payload=payload, qos=1)

    def mqtt_on_message(client, userdata, msg):
        global mqtt_print_report
        global mqtt_print_error

        if DEBUG:
            log('Received MQTT print report: ' + str(msg.payload))

        payload = json.loads(msg.payload)
        state = str(payload['state'])
        log('Received MQTT print state: ' + state)

        if state == 'failed':
            mqtt_print_error = str(payload['msg'])
            log('Failed MQTT print: ' + mqtt_print_error)

        mqtt_print_report = True

    client = paho.Client(protocol = paho.MQTTv5)
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message

    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.connect(PRINTER_IP, 2883)

    n = 0
    while not mqtt_print_report:
        n = n + 1
        if n == 50:
            log('Timeout trying to print ' + file)
            return 'Timeout trying to print ' + file

        client.loop(timeout = 0.1)

    client.disconnect()
    return mqtt_print_error



# HTTP proxy
async def http_options_handler(request):
    async with aiohttp.ClientSession() as session:
        return aiohttp.web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)
async def http_handler(request):
    if DEBUG:
        log('Proxying web request "{0} {1}"'.format(request.method, request.raw_path))

    async with aiohttp.ClientSession() as session:
        data = await request.read()
        file_to_print = None

        if request.method == 'POST' and request.raw_path == '/api/files/local' and REMOTE_MODE == 'lan':
            data_str = data.decode('utf-8')

            print_index = data_str.index('form-data; name="print"')
            if print_index > -1:
                print_value = data_str[print_index + 23:print_index + 100].strip()
                if print_value.startswith('true'):
                    data_str = data_str[:200].replace('true', 'false') + data_str[200:]
                    data = data_str.encode('utf-8')

                    log('Intecepted web request with print "{0} {1}", replacing with MQTT call...'.format(request.method, request.raw_path))

                    file_to_print = data_str[data_str.index('filename="') + 10:]
                    file_to_print = file_to_print[:file_to_print.index('"')]

        async with session.request(method = request.method, url = 'http://' + PRINTER_IP + ':' + MOONRAKER_PORT + request.raw_path, data = data, headers = request.headers) as response:
            body = await response.read()

            if file_to_print:
                await asyncio.sleep(0.5)
                error = await mqtt_printfile(file_to_print)
                if error:
                    return aiohttp.web.Response(status = 400, body = '[moonraker-proxy] ' + str(error))

            return aiohttp.web.Response(status = response.status, body = body, headers = CORS_HEADERS)



# Websockets proxy
async def websocket_handler(request):
    client_ws = aiohttp.web.WebSocketResponse()
    await client_ws.prepare(request)

    async with websockets.connect('ws://' + PRINTER_IP + ':' + MOONRAKER_PORT + '/websocket') as backend_ws:

            async def client_loop():
                async for msg in client_ws:
                    if msg.type == aiohttp.WSMsgType.ERROR:
                        print('ws connection closed with exception %s' % ws.exception())
                        return

                    if msg.type == aiohttp.WSMsgType.TEXT:
                        if msg.data == 'close':
                            await ws.close()
                            return

                        if DEBUG:
                            print('Recevied new message')

                        data = json.loads(msg.data)
                        if "method" in data:
                            
                            if data["method"] == "printer.print.start" and REMOTE_MODE == 'lan':
                                log('Intercepted "printer.print.start", replacing with MQTT call...')
                                await mqtt_printfile(data['params']['filename'])
                                continue

                            elif data["method"] == "server.files.metadata":
                                log('Intercepted "server.files.metadata", replacing path...')
                                data['params']['filename'] = data['params']['filename'].replace('/useremain/app/gk/gcodes/', '')

                            elif DEBUG:
                                log('Proxying WS message "{0}}"...'.format(data["method"]))

                        await backend_ws.send(json.dumps(data))

            async def backend_loop():
                while True:
                    data = await backend_ws.recv()
                    await client_ws.send_str(data)

            await asyncio.gather(client_loop(), backend_loop())

    return client_ws



# Server config and startup
async def start_server():
    app = aiohttp.web.Application(client_max_size = None)
    app.add_routes([
        aiohttp.web.options('/{tail:.*}', http_options_handler),
        aiohttp.web.get('/websocket', websocket_handler),
        aiohttp.web.get('/{tail:.*}', http_handler),
        aiohttp.web.post('/{tail:.*}', http_handler),
    ])

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()

    log('Listening on port {0}'.format(PROXY_PORT))

    server = aiohttp.web.TCPSite(runner, "0.0.0.0", PROXY_PORT)
    await server.start()

if __name__ == "__main__":

    # We should use internal MQTT only if LAN mode is enabled
    if os.path.isfile('/useremain/dev/remote_ctrl_mode'):
        with open('/useremain/dev/remote_ctrl_mode', 'r') as f:
            REMOTE_MODE = f.read().strip()

    log('Remote mode: {0}'.format(REMOTE_MODE))

    # Retrieve printer information
    if not MQTT_USERNAME or not MQTT_PASSWORD:

        with open('/userdata/app/gk/config/device_account.json', 'r') as f:
            json_data = f.read()
            data = json.loads(json_data)

            if not MQTT_USERNAME:
                MQTT_USERNAME = data['username']
            if not MQTT_PASSWORD:
                MQTT_PASSWORD = data['password']

    if not PRINTER_ID:

        with open('/useremain/dev/device_id', 'r') as f:
            PRINTER_ID = f.read().strip()

    if DEBUG:
        log('Printer ID: {0}'.format(PRINTER_ID))

    # Start asynchonous server
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_server())
    loop.run_forever()
