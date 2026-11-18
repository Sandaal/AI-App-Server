// Package buildinfo holds version information set at build time with -ldflags.
package buildinfo

// Set with: go build -ldflags "-X github.com/Sandaal/AI-App-Server/core/internal/buildinfo.Version=v0.1.0"
var (
	Version = "dev"
	Commit  = "none"
)
