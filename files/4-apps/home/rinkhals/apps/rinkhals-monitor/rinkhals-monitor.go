// docker run --rm -it -v .\files:/files -w /files/4-rinkhals/home/rinkhals/apps/rinkhals-monitor --entrypoint=/bin/sh golang:1.23.4 -c "GOOS=linux GOARCH=arm go build -v"

package main

import (
	"fmt"
	"log"
	"time"
	"os"
	"strings"
	"encoding/json"
	"syscall"
	"os/exec"
	"runtime"
	"strconv"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	"github.com/joho/godotenv"
	"github.com/shirou/gopsutil/cpu"
	"github.com/shirou/gopsutil/mem"
	"github.com/shirou/gopsutil/load"
	"github.com/shirou/gopsutil/process"
)

var processCommands = map[string]string {
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
var processCache = map[string]*process.Process {}

func getProcessID(processName string) (int, error) {
	if processName == "rinkhals-monitor" {
		return os.Getpid(), nil
	}
	if runtime.GOOS != "linux" {
		return 0, fmt.Errorf("getProcessID is only supported on Linux")
	}
	cmd := exec.Command("sh", "-c", fmt.Sprintf("ps | grep %s | grep -v grep | awk '{print $1}'", processName))
	output, err := cmd.Output()
	if err != nil {
		return 0, err
	}
	pidStr := strings.TrimSpace(string(output))
	if pidStr == "" {
		return 0, fmt.Errorf("process %s not found", processName)
	}
	pid, err := strconv.Atoi(pidStr)
	if err != nil {
		return 0, err
	}
	return pid, nil
}
func isProcessAlive(pid int) bool {
	p, err := os.FindProcess(pid)
	if err != nil {
		log.Printf("Error finding process with PID %d: %v", pid, err)
		return false
	}
	err = p.Signal(syscall.Signal(0))
	return err == nil
}
func checkProcesses() {
	for processName := range processCommands {
		p, exists := processCache[processName]

		if exists && isProcessAlive(int(p.Pid)) {
			continue
		}
		if exists {
			log.Printf("Process %s with PID %d is not alive", processName, p.Pid)
		}

		processCmd, _ := processCommands[processName]
		pid, err := getProcessID(processCmd)
		if err != nil || pid == 0 {
			continue
		}

		p, err = process.NewProcess(int32(pid))
		if err != nil {
			log.Printf("Error creating process object for PID %d: %v", pid, err)
			continue
		}

		log.Printf("Found process %s with PID %d", processName, pid)
		processCache[processName] = p
	}
}

func main() {
    log.SetFlags(log.Ldate | log.Ltime)

	// Load environment variables from .env file
    err := godotenv.Load()
    if err == nil {
        log.Println("Loading environment from .env file")
    }

	// Check if we can get system information on this platform
	_, err = mem.VirtualMemory()
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s\n", err)
		return
	}

	_, err = cpu.Info()
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s\n", err)
		return
	}

	// Retrieve username and password
	mqttUsername := ""
	mqttPassword := ""

	configFilePath := "/userdata/app/gk/config/device_account.json"
	if _, err := os.Stat(configFilePath); !os.IsNotExist(err) {
		file, _ := os.Open(configFilePath)
		defer file.Close()
	
		data, _ := os.ReadFile(configFilePath)
	
		var jsonData map[string]interface{}
		err = json.Unmarshal(data, &jsonData)
	
		mqttUsername, _ = jsonData["username"].(string)
		mqttPassword, _ = jsonData["password"].(string)
	}

	if os.Getenv("MQTT_USERNAME") != "" {
		mqttUsername = os.Getenv("MQTT_USERNAME")
	}
	if os.Getenv("MQTT_PASSWORD") != "" {
		mqttPassword = os.Getenv("MQTT_PASSWORD")
	}

	// Connect to the Mochi MQTT broker
	opts := mqtt.NewClientOptions()

	brokerIP := os.Getenv("MQTT_IP")
	if brokerIP == "" {
		brokerIP = "127.0.0.1"
	}

	brokerPort := os.Getenv("MQTT_PORT")
	if brokerPort == "" {
		brokerPort = "2883"
	}
	opts.AddBroker(fmt.Sprintf("tcp://%s:%s", brokerIP, brokerPort))

	log.Printf("Connecting to MQTT broker at %s:%s", brokerIP, brokerPort)

	if mqttUsername != "" {
		opts.SetUsername(mqttUsername)
	}
	if mqttPassword != "" {
		opts.SetPassword(mqttPassword)
	}
	opts.SetPassword(mqttPassword)

	opts.OnConnectionLost = func(client mqtt.Client, err error) {
		log.Printf("Connection lost: %v", err)
		for {
			if token := client.Connect(); token.Wait() && token.Error() == nil {
				log.Println("Reconnected successfully")
				break
			} else {
				log.Printf("Reconnection failed: %v", token.Error())
			}
			time.Sleep(1 * time.Second)
		}
	}

	mqttClient := mqtt.NewClient(opts)
	if token := mqttClient.Connect(); token.Wait() && token.Error() != nil {
		panic(token.Error())
	}

	// Retrieve current device ID
	deviceID := ""
	
	deviceIDPath := "/useremain/dev/device_id"
	if _, err := os.Stat(deviceIDPath); !os.IsNotExist(err) {
		deviceIDBytes, err := os.ReadFile(deviceIDPath)
		if err != nil {
			log.Fatalf("Error reading device ID: %v", err)
		}
		deviceID = strings.TrimSpace(string(deviceIDBytes))
	}

	if os.Getenv("DEVICE_ID") != "" {
		deviceID = os.Getenv("DEVICE_ID")
	}
	
	// Publish the Home Assistant MQTT discovery topic information
	discoveryPayload := fmt.Sprint(`{
		"device": {
			"ids": "`, deviceID, `",
			"name": "`, deviceID, `",
			"manufacturer": "Anycubic",
			"model": "Kobra 3",
			"serial_number": "`, deviceID, `"
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
				"unique_id": "`, deviceID, `_memory_usage"
			},
			"total_memory": {
				"name": "Total memory",
				"platform": "sensor",
				"device_class": "data_size",
				"state_class": "measurement",
				"suggested_display_precision": 1,
				"unit_of_measurement": "MB",
				"value_template": "{{ value_json.total_memory }}",
				"unique_id": "`, deviceID, `_total_memory"
			},
			"cpu_usage": {
				"name": "CPU usage",
				"platform": "sensor",
				"state_class": "measurement",
				"suggested_display_precision": 1,
				"unit_of_measurement": "%",
				"value_template": "{{ value_json.cpu_usage }}",
				"unique_id": "`, deviceID, `_cpu_usage"
			},
			"cpu_load": {
				"name": "CPU load",
				"platform": "sensor",
				"suggested_display_precision": 1,
				"state_class": "measurement",
				"value_template": "{{ value_json.cpu_load }}",
				"unique_id": "`, deviceID, `_cpu_load"
			}
			[[processes]]
		},
		"state_topic": "rinkhals/monitor/`, deviceID, `/state"
	}`)

	for processName := range processCommands {
		sanitizedProcessName := strings.ReplaceAll(processName, " ", "_")
		sanitizedProcessName = strings.ReplaceAll(sanitizedProcessName, "-", "_")

		discoveryPayloadProcessCPU := fmt.Sprint(`,
			"`, sanitizedProcessName, `_cpu_usage": {
				"name": "`, processName, ` CPU usage",
				"platform": "sensor",
				"state_class": "measurement",
				"suggested_display_precision": 1,
				"unit_of_measurement": "%",
				"value_template": "{{ value_json.processes.`, sanitizedProcessName, `.cpu_usage }}",
				"unique_id": "`, deviceID, `_`, sanitizedProcessName, `_cpu_usage"
			}
			[[processes]]`)
		discoveryPayload = strings.Replace(discoveryPayload, "[[processes]]", discoveryPayloadProcessCPU, 1)
		
		discoveryPayloadProcessMemory := fmt.Sprint(`,
			"`, sanitizedProcessName, `_memory_usage": {
				"name": "`, processName, ` memory usage",
				"platform": "sensor",
				"device_class": "data_size",
				"state_class": "measurement",
				"suggested_display_precision": 1,
				"unit_of_measurement": "MB",
				"value_template": "{{ value_json.processes.`, sanitizedProcessName, `.memory_usage }}",
				"unique_id": "`, deviceID, `_`, sanitizedProcessName, `_memory_usage"
			}
			[[processes]]`)
		discoveryPayload = strings.Replace(discoveryPayload, "[[processes]]", discoveryPayloadProcessMemory, 1)
	}

	discoveryPayload = strings.Replace(discoveryPayload, "[[processes]]", "", 1)

	homeAssistantDiscoveryTopic := fmt.Sprintf("homeassistant/device/%s/config", deviceID)
	token := mqttClient.Publish(homeAssistantDiscoveryTopic, 0, true, discoveryPayload)
	token.Wait()

	log.Printf("Published Home Assistant discovery topic for device %s", deviceID)

	// Loop to get monitoring info and send to MQTT broker
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	updateInformation := func() {
		info := make(map[string]interface{})
		vMem, err := mem.VirtualMemory()
		if err == nil {
			info["memory_usage"] = vMem.Used / 1024 / 1024
			info["total_memory"] = vMem.Total / 1024 / 1024
		}

		cpuPercent, err := cpu.Percent(0, false)
		if err == nil && len(cpuPercent) > 0 {
			info["cpu_usage"] = cpuPercent[0]
		}

		loadAvg, err := load.Avg()
		if err == nil {
			info["cpu_load"] = loadAvg.Load1
		}

		checkProcesses()

		processUsage := make(map[string]map[string]float64)

		for processName := range processCommands {
			p, exists := processCache[processName]

			if !exists {
				continue
			}

			sanitizedProcessName := strings.ReplaceAll(processName, " ", "_")
			sanitizedProcessName = strings.ReplaceAll(sanitizedProcessName, "-", "_")

			cpuPercent, err := p.Percent(0)
			if err != nil {
				log.Printf("Error getting CPU percent for PID %d: %v", p.Pid, err)
				continue
			}

			memInfo, err := p.MemoryInfo()
			if err != nil {
				log.Printf("Error getting memory info for PID %d: %v", p.Pid, err)
				continue
			}

			processUsage[sanitizedProcessName] = map[string]float64{
				"cpu_usage": cpuPercent,
				"memory_usage": float64(memInfo.RSS) / 1024 / 1024,
			}
		}
		info["processes"] = processUsage

		infoJSON, err := json.Marshal(info)
		if err != nil {
			log.Printf("Error marshalling JSON: %v", err)
			return
		}

		log.Print("Memory Usage: ", info["memory_usage"], " MB / ", info["total_memory"], " MB, CPU Usage: ", info["cpu_usage"], "%, CPU Load: ", info["cpu_load"])

		token := mqttClient.Publish(fmt.Sprintf("rinkhals/monitor/%s/state", deviceID), 0, false, infoJSON)
		token.Wait()
	}

	// Cache the initial CPU percent
	checkProcesses()

	for processName := range processCommands {
		p, exists := processCache[processName]
		if !exists {
			continue
		}

		p.Percent(0)
	}

	time.Sleep(2 * time.Second)
	
	updateInformation()

	for range ticker.C {
		updateInformation()
	}
}
