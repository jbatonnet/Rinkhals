import os
import time
import json
import logging
import psutil
import paho.mqtt.client as mqtt

#from dotenv import load_dotenv

process_commands = {
    "gklib": "gklib",
    "gkapi": "gkapi",
    "K3SysUi": "K3SysUi",
    "Moonraker": "moonraker.py",
    "Rinkhals proxy": "moonraker-proxy.py",
    "Rinkhals UI": "rinkhals-ui.py",
    "mjpg-streamer": "mjpg_streamer",
    "Rinkhals monitor": "rinkhals-monitor",
    "nginx": "nginx: worker",
    "OctoApp": "octoapp",
}
process_cache = {}

def get_process_id(process_name):
    if process_name == "rinkhals-monitor":
        return os.getpid()
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return proc.info['pid']
    return None

def is_process_alive(pid):
    return psutil.pid_exists(pid)

def check_processes():
    for process_name in process_commands:
        p = process_cache.get(process_name)
        if p and is_process_alive(p.pid):
            continue
        if p:
            logging.info(f"Process {process_name} with PID {p.pid} is not alive")
        process_cmd = process_commands[process_name]
        pid = get_process_id(process_cmd)
        if pid is None:
            continue
        p = psutil.Process(pid)
        logging.info(f"Found process {process_name} with PID {pid}")
        process_cache[process_name] = p

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

    #load_dotenv()
    #logging.info("Loading environment from .env file")

    mqtt_username = os.getenv("MQTT_USERNAME", "")
    mqtt_password = os.getenv("MQTT_PASSWORD", "")

    config_file_path = "/userdata/app/gk/config/device_account.json"
    if os.path.exists(config_file_path):
        with open(config_file_path) as file:
            json_data = json.load(file)
            mqtt_username = json_data.get("username", mqtt_username)
            mqtt_password = json_data.get("password", mqtt_password)

    broker_ip = os.getenv("MQTT_IP", "127.0.0.1")
    broker_port = int(os.getenv("MQTT_PORT", "2883"))

    client = mqtt.Client()
    if mqtt_username:
        client.username_pw_set(mqtt_username, mqtt_password)

    def on_connect(client, userdata, flags, rc):
        logging.info(f"Connected to MQTT broker at {broker_ip}:{broker_port}")

    def on_disconnect(client, userdata, rc):
        logging.info("Disconnected from MQTT broker")
        while True:
            try:
                client.reconnect()
                logging.info("Reconnected successfully")
                break
            except Exception as e:
                logging.error(f"Reconnection failed: {e}")
                time.sleep(1)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(broker_ip, broker_port, 60)

    device_id = ""
    device_id_path = "/useremain/dev/device_id"
    if os.path.exists(device_id_path):
        with open(device_id_path) as file:
            device_id = file.read().strip()

    device_id = os.getenv("DEVICE_ID", device_id)

    discovery_payload = {
        "device": {
            "ids": device_id,
            "name": device_id,
            "manufacturer": "Anycubic",
            "model": "Kobra 3",
            "serial_number": device_id
        },
        "origin": {
            "name": "rinkhals-monitor"
        },
        "components": {
            "memory_usage": {
                "name": "Memory usage",
                "platform": "sensor",
                "device_class": "data_size",
                "state_class": "measurement",
                "suggested_display_precision": 1,
                "unit_of_measurement": "MB",
                "value_template": "{{ value_json.memory_usage }}",
                "unique_id": f"{device_id}_memory_usage"
            },
            "total_memory": {
                "name": "Total memory",
                "platform": "sensor",
                "device_class": "data_size",
                "state_class": "measurement",
                "suggested_display_precision": 1,
                "unit_of_measurement": "MB",
                "value_template": "{{ value_json.total_memory }}",
                "unique_id": f"{device_id}_total_memory"
            },
            "cpu_usage": {
                "name": "CPU usage",
                "platform": "sensor",
                "state_class": "measurement",
                "suggested_display_precision": 1,
                "unit_of_measurement": "%",
                "value_template": "{{ value_json.cpu_usage }}",
                "unique_id": f"{device_id}_cpu_usage"
            },
            "cpu_load": {
                "name": "CPU load",
                "platform": "sensor",
                "suggested_display_precision": 1,
                "state_class": "measurement",
                "value_template": "{{ value_json.cpu_load }}",
                "unique_id": f"{device_id}_cpu_load"
            }
        }
    }

    for process_name in process_commands:
        sanitized_process_name = process_name.replace(" ", "_").replace("-", "_")
        discovery_payload["components"][f"{sanitized_process_name}_cpu_usage"] = {
            "name": f"{process_name} CPU usage",
            "platform": "sensor",
            "state_class": "measurement",
            "suggested_display_precision": 1,
            "unit_of_measurement": "%",
            "value_template": f"{{{{ value_json.processes.{sanitized_process_name}.cpu_usage }}}}",
            "unique_id": f"{device_id}_{sanitized_process_name}_cpu_usage"
        }
        discovery_payload["components"][f"{sanitized_process_name}_memory_usage"] = {
            "name": f"{process_name} memory usage",
            "platform": "sensor",
            "device_class": "data_size",
            "state_class": "measurement",
            "suggested_display_precision": 1,
            "unit_of_measurement": "MB",
            "value_template": f"{{{{ value_json.processes.{sanitized_process_name}.memory_usage }}}}",
            "unique_id": f"{device_id}_{sanitized_process_name}_memory_usage"
        }

    home_assistant_discovery_topic = f"homeassistant/device/{device_id}/config"
    client.publish(home_assistant_discovery_topic, json.dumps(discovery_payload), qos=0, retain=True)
    logging.info(f"Published Home Assistant discovery topic for device {device_id}")

    def update_information():
        info = {}
        v_mem = psutil.virtual_memory()
        info["memory_usage"] = v_mem.used / 1024 / 1024
        info["total_memory"] = v_mem.total / 1024 / 1024

        cpu_percent = psutil.cpu_percent(interval=1)
        info["cpu_usage"] = cpu_percent

        # load_avg = os.getloadavg()
        # info["cpu_load"] = load_avg[0]

        check_processes()
        
        process_usage = {}
        for process_name in process_commands:
            p = process_cache.get(process_name)
            if not p:
                continue
            sanitized_process_name = process_name.replace(" ", "_").replace("-", "_")
            cpu_percent = p.cpu_percent(interval=1)
            mem_info = p.memory_info()
            process_usage[sanitized_process_name] = {
                "cpu_usage": cpu_percent,
                "memory_usage": mem_info.rss / 1024 / 1024
            }
        info["processes"] = process_usage

        info_json = json.dumps(info)
        #logging.info(f"Memory Usage: {info['memory_usage']} MB / {info['total_memory']} MB, CPU Usage: {info['cpu_usage']}%, CPU Load: {info['cpu_load']}")
        logging.info(f"Memory Usage: {info['memory_usage']} MB / {info['total_memory']} MB, CPU Usage: {info['cpu_usage']}%")

        client.publish(f"rinkhals/monitor/{device_id}/state", info_json, qos=0, retain=False)

    check_processes()
    for process_name in process_commands:
        p = process_cache.get(process_name)
        if p:
            p.cpu_percent(interval=1)

    time.sleep(2)
    update_information()

    while True:
        time.sleep(30)
        update_information()

if __name__ == "__main__":
    main()
