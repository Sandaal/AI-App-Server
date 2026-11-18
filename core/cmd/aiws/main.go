// Command aiws is the AI App Server: `aiws serve` runs the server; other
// subcommands are the developer CLI.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/Sandaal/AI-App-Server/core/internal/apps"
	"github.com/Sandaal/AI-App-Server/core/internal/buildinfo"
	"github.com/Sandaal/AI-App-Server/core/internal/server"
)

const usage = `aiws - AI App Server

Usage:
  aiws serve [--addr 127.0.0.1:8080] [--data-dir ./data] [--log-level info]
  aiws apps  [--data-dir ./data]        list deployed apps (talks to a running server)
  aiws version

More commands (new, source, deploy) arrive in later Phase 0 milestones.
`

func main() {
	if len(os.Args) < 2 {
		fmt.Fprint(os.Stderr, usage)
		os.Exit(2)
	}
	var err error
	switch os.Args[1] {
	case "serve":
		err = runServe(os.Args[2:])
	case "apps":
		err = runApps(os.Args[2:], os.Stdout)
	case "version", "--version", "-v":
		fmt.Printf("aiws %s (%s)\n", buildinfo.Version, buildinfo.Commit)
	case "help", "--help", "-h":
		fmt.Print(usage)
	default:
		fmt.Fprintf(os.Stderr, "unknown command %q\n\n%s", os.Args[1], usage)
		os.Exit(2)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

func runServe(args []string) error {
	fs := flag.NewFlagSet("serve", flag.ContinueOnError)
	addr := fs.String("addr", "127.0.0.1:8080", "public listen address")
	dataDir := fs.String("data-dir", "./data", "data directory for built-in storage")
	level := fs.String("log-level", "info", "debug | info | warn | error")
	if err := fs.Parse(args); err != nil {
		return err
	}

	var lv slog.Level
	if err := lv.UnmarshalText([]byte(*level)); err != nil {
		return fmt.Errorf("invalid --log-level %q", *level)
	}
	log := slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{Level: lv}))

	srv, err := server.New(server.Config{Addr: *addr, DataDir: *dataDir}, log, apps.NewRegistry())
	if err != nil {
		return err
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	return srv.Run(ctx)
}

func runApps(args []string, out io.Writer) error {
	fs := flag.NewFlagSet("apps", flag.ContinueOnError)
	dataDir := fs.String("data-dir", "./data", "data directory of the running server")
	if err := fs.Parse(args); err != nil {
		return err
	}
	sock := filepath.Join(*dataDir, "admin.sock")
	client := &http.Client{
		Timeout: 5 * time.Second,
		Transport: &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
			return (&net.Dialer{}).DialContext(ctx, "unix", sock)
		}},
	}
	resp, err := client.Get("http://admin/admin/apps")
	if err != nil {
		return fmt.Errorf("cannot reach server at %s (is `aiws serve` running?): %w", sock, err)
	}
	defer resp.Body.Close()

	var body struct {
		Apps []apps.App `json:"apps"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		return fmt.Errorf("decode response: %w", err)
	}
	if len(body.Apps) == 0 {
		fmt.Fprintln(out, "No apps deployed.")
		return nil
	}
	fmt.Fprintf(out, "%-24s %-10s %-10s %s\n", "APP", "VERSION", "STATUS", "DEPLOYED")
	for _, a := range body.Apps {
		fmt.Fprintf(out, "%-24s %-10s %-10s %s\n", a.Manifest.App, a.Manifest.Version, a.Status,
			a.DeployedAt.Format(time.RFC3339))
	}
	return nil
}
