package apps

import (
	"errors"
	"testing"
)

func validManifest() Manifest {
	return Manifest{App: "hr-bot", Version: "0.1.0", Routes: []Route{{Path: "/chat", Handler: "handlers:chat", Stream: true}}}
}

func TestValidateDefaults(t *testing.T) {
	m := validManifest()
	if err := m.Validate(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if m.Runtime != "python3.12" || m.Workers != 2 {
		t.Fatalf("defaults not applied: runtime=%q workers=%d", m.Runtime, m.Workers)
	}
}

func TestValidateRejects(t *testing.T) {
	cases := map[string]func(*Manifest){
		"bad name":        func(m *Manifest) { m.App = "HR Bot" },
		"missing version": func(m *Manifest) { m.Version = "" },
		"bad route":       func(m *Manifest) { m.Routes = []Route{{Path: "chat"}} },
		"duplicate route": func(m *Manifest) { m.Routes = append(m.Routes, Route{Path: "/chat"}) },
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			m := validManifest()
			mutate(&m)
			if err := m.Validate(); err == nil {
				t.Fatal("expected validation error")
			}
		})
	}
}

func TestRegistryLifecycle(t *testing.T) {
	r := NewRegistry()
	if _, err := r.Register(validManifest(), "/apps/hr-bot"); err != nil {
		t.Fatal(err)
	}
	if _, err := r.Register(Manifest{App: "aaa-first", Version: "1"}, "/apps/a"); err != nil {
		t.Fatal(err)
	}
	list := r.List()
	if len(list) != 2 || list[0].Manifest.App != "aaa-first" {
		t.Fatalf("list not sorted or wrong length: %+v", list)
	}
	a, err := r.Get("hr-bot")
	if err != nil || a.Status != StatusDeployed {
		t.Fatalf("get: %v %+v", err, a)
	}
	if err := r.Remove("hr-bot"); err != nil {
		t.Fatal(err)
	}
	if _, err := r.Get("hr-bot"); !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}
	if _, err := r.Register(Manifest{App: "X"}, ""); err == nil {
		t.Fatal("invalid manifest was registered")
	}
}
