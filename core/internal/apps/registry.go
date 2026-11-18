// Package apps holds deployed-app metadata and the app registry.
package apps

import (
	"errors"
	"fmt"
	"regexp"
	"sort"
	"sync"
	"time"
)

// Manifest is the parsed form of ai-app.yaml. Phase 0 M0.1 defines the shape;
// a YAML-backed Loader is added in M0.1b once module downloads are available.
type Manifest struct {
	App       string   `json:"app"`
	Version   string   `json:"version"`
	Blueprint string   `json:"blueprint,omitempty"`
	Runtime   string   `json:"runtime"`
	Workers   int      `json:"workers"`
	Routes    []Route  `json:"routes"`
	Guardrail []string `json:"guardrails,omitempty"`
}

// Route maps an HTTP path within an app to a handler.
type Route struct {
	Path    string `json:"path"`
	Handler string `json:"handler"`
	Stream  bool   `json:"stream"`
}

// Loader reads a manifest from an app directory.
type Loader interface {
	Load(appDir string) (Manifest, error)
}

// Status is an app's lifecycle state.
type Status string

const (
	StatusDeployed Status = "deployed"
	StatusStopped  Status = "stopped"
)

// App is a registered application.
type App struct {
	Manifest   Manifest  `json:"manifest"`
	Dir        string    `json:"dir"`
	Status     Status    `json:"status"`
	DeployedAt time.Time `json:"deployed_at"`
}

var (
	ErrNotFound = errors.New("app not found")
	appNameRE   = regexp.MustCompile(`^[a-z][a-z0-9-]{1,62}$`)
)

// Validate checks the fields every manifest must have and applies defaults.
func (m *Manifest) Validate() error {
	if !appNameRE.MatchString(m.App) {
		return fmt.Errorf("invalid app name %q: use 2-63 lowercase letters, digits or hyphens, starting with a letter", m.App)
	}
	if m.Version == "" {
		return errors.New("version is required")
	}
	if m.Runtime == "" {
		m.Runtime = "python3.12"
	}
	if m.Workers <= 0 {
		m.Workers = 2
	}
	seen := map[string]bool{}
	for _, r := range m.Routes {
		if r.Path == "" || r.Path[0] != '/' {
			return fmt.Errorf("route path %q must start with /", r.Path)
		}
		if seen[r.Path] {
			return fmt.Errorf("duplicate route %q", r.Path)
		}
		seen[r.Path] = true
	}
	return nil
}

// Registry is the in-memory set of apps. Safe for concurrent use.
type Registry struct {
	mu   sync.RWMutex
	apps map[string]App
	now  func() time.Time
}

// NewRegistry returns an empty registry.
func NewRegistry() *Registry {
	return &Registry{apps: map[string]App{}, now: time.Now}
}

// Register adds or replaces an app after validating its manifest.
func (r *Registry) Register(m Manifest, dir string) (App, error) {
	if err := m.Validate(); err != nil {
		return App{}, err
	}
	a := App{Manifest: m, Dir: dir, Status: StatusDeployed, DeployedAt: r.now().UTC()}
	r.mu.Lock()
	r.apps[m.App] = a
	r.mu.Unlock()
	return a, nil
}

// Get returns one app by name.
func (r *Registry) Get(name string) (App, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	a, ok := r.apps[name]
	if !ok {
		return App{}, ErrNotFound
	}
	return a, nil
}

// Remove deletes an app.
func (r *Registry) Remove(name string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.apps[name]; !ok {
		return ErrNotFound
	}
	delete(r.apps, name)
	return nil
}

// List returns all apps sorted by name.
func (r *Registry) List() []App {
	r.mu.RLock()
	out := make([]App, 0, len(r.apps))
	for _, a := range r.apps {
		out = append(out, a)
	}
	r.mu.RUnlock()
	sort.Slice(out, func(i, j int) bool { return out[i].Manifest.App < out[j].Manifest.App })
	return out
}
