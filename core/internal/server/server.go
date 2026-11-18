// Package server runs the public HTTP listener and the local admin listener.
package server

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/Sandaal/AI-App-Server/core/internal/apps"
	"github.com/Sandaal/AI-App-Server/core/internal/buildinfo"
)

// Config controls the server.
type Config struct {
	Addr        string // public listener, e.g. 127.0.0.1:8080
	DataDir     string // root for all built-in storage
	AdminSocket string // Unix socket for the CLI; defaults to <DataDir>/admin.sock
}

// Server is the AI App Server core.
type Server struct {
	cfg      Config
	log      *slog.Logger
	registry *apps.Registry
	started  time.Time

	public *http.Server
	admin  *http.Server
}

// New prepares a server and its data directory.
func New(cfg Config, log *slog.Logger, reg *apps.Registry) (*Server, error) {
	if cfg.Addr == "" {
		cfg.Addr = "127.0.0.1:8080"
	}
	if cfg.DataDir == "" {
		cfg.DataDir = "./data"
	}
	if err := os.MkdirAll(cfg.DataDir, 0o700); err != nil {
		return nil, fmt.Errorf("create data dir: %w", err)
	}
	if cfg.AdminSocket == "" {
		cfg.AdminSocket = filepath.Join(cfg.DataDir, "admin.sock")
	}
	s := &Server{cfg: cfg, log: log, registry: reg}
	s.public = &http.Server{Handler: s.publicHandler(), ReadHeaderTimeout: 10 * time.Second}
	s.admin = &http.Server{Handler: s.adminHandler(), ReadHeaderTimeout: 10 * time.Second}
	return s, nil
}

func (s *Server) publicHandler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("GET /version", s.handleVersion)
	return s.withRequestLog(mux)
}

func (s *Server) adminHandler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /admin/health", s.handleHealth)
	mux.HandleFunc("GET /admin/apps", s.handleListApps)
	mux.HandleFunc("GET /admin/apps/{name}", s.handleGetApp)
	return s.withRequestLog(mux)
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"status":         "ok",
		"uptime_seconds": int(time.Since(s.started).Seconds()),
		"apps":           len(s.registry.List()),
	})
}

func (s *Server) handleVersion(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"version": buildinfo.Version, "commit": buildinfo.Commit})
}

func (s *Server) handleListApps(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"apps": s.registry.List()})
}

func (s *Server) handleGetApp(w http.ResponseWriter, r *http.Request) {
	a, err := s.registry.Get(r.PathValue("name"))
	if errors.Is(err, apps.ErrNotFound) {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "app not found"})
		return
	}
	writeJSON(w, http.StatusOK, a)
}

// Run starts both listeners and blocks until ctx is cancelled, then shuts down gracefully.
func (s *Server) Run(ctx context.Context) error {
	s.started = time.Now()

	pubLn, err := net.Listen("tcp", s.cfg.Addr)
	if err != nil {
		return fmt.Errorf("listen %s: %w", s.cfg.Addr, err)
	}
	_ = os.Remove(s.cfg.AdminSocket) // stale socket from a previous run
	admLn, err := net.Listen("unix", s.cfg.AdminSocket)
	if err != nil {
		pubLn.Close()
		return fmt.Errorf("listen admin socket: %w", err)
	}
	if err := os.Chmod(s.cfg.AdminSocket, 0o600); err != nil {
		pubLn.Close()
		admLn.Close()
		return fmt.Errorf("secure admin socket: %w", err)
	}

	s.log.Info("server started", "addr", pubLn.Addr().String(), "admin_socket", s.cfg.AdminSocket,
		"data_dir", s.cfg.DataDir, "version", buildinfo.Version)

	errc := make(chan error, 2)
	go func() { errc <- serve(s.public, pubLn) }()
	go func() { errc <- serve(s.admin, admLn) }()

	select {
	case <-ctx.Done():
	case err := <-errc:
		if err != nil {
			s.shutdown()
			return err
		}
	}
	s.shutdown()
	return nil
}

// Addr returns the configured public address.
func (s *Server) Addr() string { return s.cfg.Addr }

func (s *Server) shutdown() {
	s.log.Info("shutting down")
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	_ = s.public.Shutdown(ctx)
	_ = s.admin.Shutdown(ctx)
	_ = os.Remove(s.cfg.AdminSocket)
}

func serve(srv *http.Server, ln net.Listener) error {
	if err := srv.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

func (s *Server) withRequestLog(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		s.log.Debug("request", "method", r.Method, "path", r.URL.Path, "status", rec.status,
			"duration_ms", time.Since(start).Milliseconds())
	})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
