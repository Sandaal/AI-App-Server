package server

import (
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/Sandaal/AI-App-Server/core/internal/apps"
)

func freeAddr(t *testing.T) string {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	return ln.Addr().String()
}

func startServer(t *testing.T, reg *apps.Registry) (addr, sock string, cancel func()) {
	t.Helper()
	// Short dir: Unix socket paths are limited to ~104 bytes on macOS.
	dir, err := os.MkdirTemp("", "aiws")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.RemoveAll(dir) })
	addr = freeAddr(t)
	srv, err := New(Config{Addr: addr, DataDir: dir}, slog.New(slog.NewTextHandler(io.Discard, nil)), reg)
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancelCtx := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- srv.Run(ctx) }()

	sock = filepath.Join(dir, "admin.sock")
	deadline := time.Now().Add(3 * time.Second)
	for {
		if resp, err := http.Get("http://" + addr + "/health"); err == nil {
			resp.Body.Close()
			if _, err := os.Stat(sock); err == nil {
				break
			}
		}
		if time.Now().After(deadline) {
			t.Fatal("server did not start")
		}
		time.Sleep(20 * time.Millisecond)
	}
	return addr, sock, func() {
		cancelCtx()
		if err := <-done; err != nil {
			t.Errorf("run returned error: %v", err)
		}
	}
}

func TestHealthAndVersion(t *testing.T) {
	addr, _, stop := startServer(t, apps.NewRegistry())
	defer stop()

	resp, err := http.Get("http://" + addr + "/health")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var body map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != 200 || body["status"] != "ok" {
		t.Fatalf("unexpected health response: %d %v", resp.StatusCode, body)
	}

	resp2, err := http.Get("http://" + addr + "/version")
	if err != nil {
		t.Fatal(err)
	}
	resp2.Body.Close()
	if resp2.StatusCode != 200 {
		t.Fatalf("version status %d", resp2.StatusCode)
	}
}

func TestAdminSocketListsApps(t *testing.T) {
	reg := apps.NewRegistry()
	if _, err := reg.Register(apps.Manifest{App: "hr-bot", Version: "0.1.0"}, "/apps/hr-bot"); err != nil {
		t.Fatal(err)
	}
	addr, sock, stop := startServer(t, reg)
	defer stop()

	// Admin endpoints must not be exposed on the public listener.
	if resp, err := http.Get("http://" + addr + "/admin/apps"); err == nil {
		resp.Body.Close()
		if resp.StatusCode != http.StatusNotFound {
			t.Fatalf("admin route reachable publicly: %d", resp.StatusCode)
		}
	}

	info, err := os.Stat(sock)
	if err != nil {
		t.Fatal(err)
	}
	if perm := info.Mode().Perm(); perm != 0o600 {
		t.Fatalf("admin socket permissions %o, want 600", perm)
	}

	client := &http.Client{Transport: &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "unix", sock)
	}}}
	resp, err := client.Get("http://admin/admin/apps")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var body struct {
		Apps []apps.App `json:"apps"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatal(err)
	}
	if len(body.Apps) != 1 || body.Apps[0].Manifest.App != "hr-bot" {
		t.Fatalf("unexpected apps: %+v", body.Apps)
	}

	resp404, err := client.Get("http://admin/admin/apps/missing")
	if err != nil {
		t.Fatal(err)
	}
	resp404.Body.Close()
	if resp404.StatusCode != http.StatusNotFound {
		t.Fatalf("want 404 for missing app, got %d", resp404.StatusCode)
	}
}

func TestShutdownRemovesSocket(t *testing.T) {
	_, sock, stop := startServer(t, apps.NewRegistry())
	stop()
	if _, err := os.Stat(sock); !os.IsNotExist(err) {
		t.Fatalf("admin socket still present after shutdown: %v", err)
	}
}
