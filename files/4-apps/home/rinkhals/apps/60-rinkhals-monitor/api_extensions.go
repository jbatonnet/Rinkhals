package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"

	"github.com/gorilla/websocket"
)


func handleMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")

	uptimeBytes, _ := ioutil.ReadFile("/proc/uptime")
	uptimeStr := strings.Split(string(uptimeBytes), " ")[0]
	
	memBytes, _ := ioutil.ReadFile("/proc/meminfo")
	var memTotal, memFree int
	for _, line := range strings.Split(string(memBytes), "\n") {
		if strings.HasPrefix(line, "MemTotal:") {
			fmt.Sscanf(line, "MemTotal: %d kB", &memTotal)
		} else if strings.HasPrefix(line, "MemFree:") {
			fmt.Sscanf(line, "MemFree: %d kB", &memFree)
		}
	}
	memUsage := 0
	if memTotal > 0 {
		memUsage = int(float64(memTotal-memFree) / float64(memTotal) * 100)
	}

	var stat syscall.Statfs_t
	syscall.Statfs("/userdata", &stat)
	diskUsage := 0
	if stat.Blocks > 0 {
		diskUsage = int(float64(stat.Blocks-stat.Bfree) / float64(stat.Blocks) * 100)
	}

	load, _ := ioutil.ReadFile("/proc/loadavg")
	cpuLoad := strings.Split(string(load), " ")[0]

	json.NewEncoder(w).Encode(map[string]interface{}{
		"uptime":    uptimeStr,
		"cpuLoad":   cpuLoad,
		"memUsage":  memUsage,
		"diskUsage": diskUsage,
	})
}

func handleSaveFile(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		return
	}

	var req struct {
		Path    string `json:"path"`
		Content string `json:"content"`
	}
	json.NewDecoder(r.Body).Decode(&req)

	cleanPath := filepath.Clean(req.Path)
	ioutil.WriteFile(cleanPath, []byte(req.Content), 0644)
	json.NewEncoder(w).Encode(map[string]interface{}{"success": true})
}

func handleServices(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		return
	}

	if r.Method == "GET" {
		services := []map[string]string{
			{"id": "25-mainsail", "name": "Mainsail", "status": "Stopped"},
			{"id": "26-fluidd", "name": "Fluidd", "status": "Stopped"},
			{"id": "40-moonraker", "name": "Moonraker", "status": "Stopped"},
			{"id": "30-mjpg-streamer", "name": "Webcam", "status": "Stopped"},
		}

		for _, s := range services {
			out, err := exec.Command("sh", "-c", "source /useremain/rinkhals/.current/tools.sh && get_app_status "+s["id"]).CombinedOutput()
			if err == nil && strings.Contains(string(out), "started") {
				s["status"] = "Running"
			}
		}
		json.NewEncoder(w).Encode(services)
		return
	}

	var req struct {
		Action  string `json:"action"`
		Service string `json:"service"`
	}
	json.NewDecoder(r.Body).Decode(&req)

	cmdStr := fmt.Sprintf("source /useremain/rinkhals/.current/tools.sh && %s_app %s", req.Action, req.Service)
	if req.Action == "restart" {
		cmdStr = fmt.Sprintf("source /useremain/rinkhals/.current/tools.sh && stop_app %s && sleep 1 && start_app %s", req.Service, req.Service)
	}

	out, err := exec.Command("sh", "-c", cmdStr).CombinedOutput()
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": err == nil,
		"output":  string(out),
	})
}

func handleLogStream(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil { return }
	defer conn.Close()

	logPath := r.URL.Query().Get("path")
	if logPath == "" { return }
	logPath = filepath.Clean(logPath)

	cmd := exec.Command("tail", "-f", "-n", "100", logPath)
	stdout, err := cmd.StdoutPipe()
	if err != nil { return }
	
	if err := cmd.Start(); err != nil { return }
	defer cmd.Process.Kill()

	go func() {
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				cmd.Process.Kill()
				return
			}
		}
	}()

	scanner := bufio.NewScanner(stdout)
	for scanner.Scan() {
		conn.WriteMessage(websocket.TextMessage, scanner.Bytes())
	}
}
