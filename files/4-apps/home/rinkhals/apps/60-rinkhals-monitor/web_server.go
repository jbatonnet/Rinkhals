package main

import (
	"crypto/subtle"
	"embed"
	"encoding/json"
	"io"
	"io/fs"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"

	"github.com/creack/pty"
	"github.com/gorilla/websocket"
)

//go:embed all:ui
var uiFiles embed.FS

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all origins for MVP
	},
}

type FileInfo struct {
	Name     string `json:"name"`
	Path     string `json:"path"`
	Type     string `json:"type"`
	Size     int64  `json:"size"`
	Modified string `json:"modified"`
	IsText   bool   `json:"isText"`
}

func isTextFile(path string, info fs.FileInfo) bool {
	if info.IsDir() {
		return false
	}
	if info.Size() == 0 {
		return true
	}

	file, err := os.Open(path)
	if err != nil {
		return false
	}
	defer file.Close()

	buf := make([]byte, 512)
	n, err := file.Read(buf)
	if err != nil && err != io.EOF {
		return false
	}

	for i := 0; i < n; i++ {
		if buf[i] == 0 {
			return false
		}
	}
	return true
}

func handleFilesList(w http.ResponseWriter, r *http.Request) {
	requestedPath := r.URL.Query().Get("path")
	if requestedPath == "" {
		requestedPath = "/"
	}

	requestedPath = filepath.Clean(requestedPath)
	entries, err := os.ReadDir(requestedPath)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	var files []FileInfo
	for _, entry := range entries {
		info, err := entry.Info()
		if err != nil {
			continue
		}

		fileType := "file"
		if entry.IsDir() {
			fileType = "folder"
		}

		filePath := filepath.Join(requestedPath, entry.Name())
		files = append(files, FileInfo{
			Name:     entry.Name(),
			Path:     filePath,
			Type:     fileType,
			Size:     info.Size(),
			Modified: info.ModTime().Format("2006-01-02 15:04:05"),
			IsText:   isTextFile(filePath, info),
		})

	}

	sort.Slice(files, func(i, j int) bool {
		if files[i].Type != files[j].Type {
			return files[i].Type == "folder"
		}
		return strings.ToLower(files[i].Name) < strings.ToLower(files[j].Name)
	})

	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(files)
}

func handleFileDownload(w http.ResponseWriter, r *http.Request) {
	requestedPath := r.URL.Query().Get("path")
	if requestedPath == "" {
		http.Error(w, "Path required", http.StatusBadRequest)
		return
	}
	requestedPath = filepath.Clean(requestedPath)

	w.Header().Set("Access-Control-Allow-Origin", "*")
	http.ServeFile(w, r, requestedPath)
}

func handleTerminal(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("WebSocket upgrade failed:", err)
		return
	}
	defer conn.Close()

	cmd := exec.Command("sh")
	cmd.Env = append(os.Environ(), "TERM=xterm-256color")

	ptmx, err := pty.Start(cmd)
	if err != nil {
		log.Println("Failed to start pty:", err)
		return
	}
	defer func() { _ = ptmx.Close() }()

	// Read from PTY and write to WebSocket
	go func() {
		buf := make([]byte, 2048)
		for {
			n, err := ptmx.Read(buf)
			if err != nil {
				if err != io.EOF {
					log.Println("PTY read error:", err)
				}
				return
			}
			if err := conn.WriteMessage(websocket.BinaryMessage, buf[:n]); err != nil {
				return
			}
		}
	}()

	// Read from WebSocket and write to PTY
	for {
		msgType, p, err := conn.ReadMessage()
		if err != nil {
			break
		}

		if msgType == websocket.BinaryMessage {
			ptmx.Write(p)
		} else if msgType == websocket.TextMessage {
			// Possibly a resize payload
			var size struct {
				Cols uint16 `json:"cols"`
				Rows uint16 `json:"rows"`
			}
			if err := json.Unmarshal(p, &size); err == nil && size.Cols > 0 && size.Rows > 0 {
				pty.Setsize(ptmx, &pty.Winsize{
					Rows: size.Rows,
					Cols: size.Cols,
				})
			} else {
				// If it's just raw text data, write it
				ptmx.Write(p)
			}
		}
	}
}

func handleTools(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" && r.Method != "GET" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	action := r.URL.Query().Get("action")
	if action == "" {
		http.Error(w, "Action required", http.StatusBadRequest)
		return
	}

	w.Header().Set("Access-Control-Allow-Origin", "*")

	var scriptPath string
	switch action {
	case "debug-bundle":
		scriptPath = "/opt/rinkhals/tools/debug-bundle.sh"
	case "config-reset":
		scriptPath = "/opt/rinkhals/tools/config-reset.sh"
	case "backup-partitions":
		scriptPath = "/opt/rinkhals/tools/backup-partitions.sh"
	case "clean-rinkhals":
		scriptPath = "/opt/rinkhals/tools/clean-rinkhals.sh"
	case "uninstall-rinkhals":
		scriptPath = "/opt/rinkhals/tools/rinkhals-uninstall.sh"
	default:
		http.Error(w, "Invalid action", http.StatusBadRequest)
		return
	}

	cmd := exec.Command("sh", scriptPath)
	output, err := cmd.CombinedOutput()
	if err != nil {
		log.Printf("Tool %s execution failed: %v, Output: %s", action, err, string(output))
		http.Error(w, "Failed to execute tool", http.StatusInternalServerError)
		return
	}

	if action == "debug-bundle" {
		w.Header().Set("Content-Disposition", "attachment; filename=debug-bundle.zip")
		http.ServeFile(w, r, "/tmp/debug-bundle.zip")
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"success": true, "output": string(output)})
}

type FsRequest struct {
	Action      string   `json:"action"`
	Targets     []string `json:"targets"`
	Destination string   `json:"destination"`
}

func handleFileSystem(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		return
	}

	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req FsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	errors := make([]string, 0)

	switch req.Action {
	case "delete":
		for _, target := range req.Targets {
			cleanPath := filepath.Clean(target)
			if err := os.RemoveAll(cleanPath); err != nil {
				errors = append(errors, err.Error())
			}
		}
	case "move":
		destPath := filepath.Clean(req.Destination)
		for _, target := range req.Targets {
			cleanPath := filepath.Clean(target)
			newPath := filepath.Join(destPath, filepath.Base(cleanPath))
			if err := os.Rename(cleanPath, newPath); err != nil {
				errors = append(errors, err.Error())
			}
		}
	case "rename":
		if len(req.Targets) != 1 || req.Destination == "" {
			errors = append(errors, "Rename requires exactly one target and a destination")
			break
		}
		cleanPath := filepath.Clean(req.Targets[0])
		newPath := filepath.Clean(req.Destination)
		if err := os.Rename(cleanPath, newPath); err != nil {
			errors = append(errors, err.Error())
		}
	case "mkdir":
		destPath := filepath.Clean(req.Destination)
		if err := os.MkdirAll(destPath, 0755); err != nil {
			errors = append(errors, err.Error())
		}
	default:
		errors = append(errors, "Unknown action")
	}

	if len(errors) > 0 {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]interface{}{"success": false, "errors": errors})
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{"success": true})
}

func getCredentials() (string, string) {
	authFile := "/useremain/home/rinkhals/monitor_auth.txt"
	data, err := os.ReadFile(authFile)
	if err != nil {
		// Create default
		defaultAuth := "admin:rinkhals"
		os.WriteFile(authFile, []byte(defaultAuth), 0600)
		return "admin", "rinkhals"
	}
	parts := strings.SplitN(strings.TrimSpace(string(data)), ":", 2)
	if len(parts) == 2 {
		return parts[0], parts[1]
	}
	return "admin", "rinkhals" // fallback
}

func basicAuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		expectedUser, expectedPass := getCredentials()

		user, pass, ok := r.BasicAuth()
		if !ok || subtle.ConstantTimeCompare([]byte(user), []byte(expectedUser)) != 1 || subtle.ConstantTimeCompare([]byte(pass), []byte(expectedPass)) != 1 {
			w.Header().Set("WWW-Authenticate", `Basic realm="Rinkhals Terminal"`)
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func handleAuthStatus(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	user, pass := getCredentials()
	isDefault := (user == "admin" && pass == "rinkhals")

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"is_default": isDefault})
}

func handleAuthChange(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		return
	}
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Username == "" || req.Password == "" {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	authFile := "/useremain/home/rinkhals/monitor_auth.txt"
	newAuth := req.Username + ":" + req.Password
	if err := os.WriteFile(authFile, []byte(newAuth), 0600); err != nil {
		http.Error(w, "Failed to save password", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{"success": true})
}

func startWebServer() {
	uiFS, err := fs.Sub(uiFiles, "ui")
	if err != nil {
		log.Fatalf("Failed to create sub filesystem: %v", err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/api/files", handleFilesList)
	mux.HandleFunc("/api/download", handleFileDownload)
	mux.HandleFunc("/api/terminal", handleTerminal)
	mux.HandleFunc("/api/tools", handleTools)
	mux.HandleFunc("/api/fs", handleFileSystem)
	mux.HandleFunc("/api/metrics", handleMetrics)
	mux.HandleFunc("/api/saveFile", handleSaveFile)
	mux.HandleFunc("/api/services", handleServices)
	mux.HandleFunc("/api/logstream", handleLogStream)
	mux.HandleFunc("/api/auth/status", handleAuthStatus)
	mux.HandleFunc("/api/auth/change", handleAuthChange)

	mux.Handle("/", http.FileServer(http.FS(uiFS)))

	log.Println("Starting Rinkhals Web Portal on :8090")

	protectedMux := basicAuthMiddleware(mux)

	if err := http.ListenAndServe(":8090", protectedMux); err != nil {
		log.Fatalf("HTTP server failed: %v", err)
	}
}
