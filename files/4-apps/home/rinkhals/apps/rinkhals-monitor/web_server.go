package main

import (
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

		files = append(files, FileInfo{
			Name:     entry.Name(),
			Path:     filepath.Join(requestedPath, entry.Name()),
			Type:     fileType,
			Size:     info.Size(),
			Modified: info.ModTime().Format("2006-01-02 15:04:05"),
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

func startWebServer() {
	uiFS, err := fs.Sub(uiFiles, "ui")
	if err != nil {
		log.Fatalf("Failed to create sub filesystem: %v", err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/api/files", handleFilesList)
	mux.HandleFunc("/api/download", handleFileDownload)
	mux.HandleFunc("/api/terminal", handleTerminal)
	mux.Handle("/", http.FileServer(http.FS(uiFS)))

	log.Println("Starting Rinkhals Web Portal on :8080")
	if err := http.ListenAndServe(":8080", mux); err != nil {
		log.Fatalf("HTTP server failed: %v", err)
	}
}
