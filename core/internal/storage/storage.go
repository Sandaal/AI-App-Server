// Package storage defines the interfaces for built-in storage. Engines live in
// subpackages; external adapters (Phase 2) implement the same interfaces, so
// the pipeline and SDK never depend on a specific backend.
package storage

import (
	"context"
	"errors"
	"io"
)

// ErrNotFound is returned when a key, blob or record does not exist.
var ErrNotFound = errors.New("not found")

// KV is the key-value store (Pebble-backed in M0.4; data structures in Phase 1).
type KV interface {
	Get(ctx context.Context, namespace, key string) ([]byte, error)
	Put(ctx context.Context, namespace, key string, value []byte) error
	Delete(ctx context.Context, namespace, key string) error
}

// BlobRef identifies a stored blob by content hash.
type BlobRef struct {
	Hash string `json:"hash"` // lowercase hex SHA-256
	Size int64  `json:"size"`
}

// BlobStore is the content-addressed file store.
type BlobStore interface {
	Put(ctx context.Context, r io.Reader) (BlobRef, error)
	Open(ctx context.Context, hash string) (io.ReadCloser, error)
	Has(ctx context.Context, hash string) (bool, error)
	Delete(ctx context.Context, hash string) error
}

// VectorRecord is one entry in a vector collection.
type VectorRecord struct {
	ID       string            `json:"id"`
	Text     string            `json:"text"`
	Vector   []float32         `json:"vector"`
	Metadata map[string]string `json:"metadata,omitempty"`
}

// VectorHit is one search result.
type VectorHit struct {
	ID       string            `json:"id"`
	Score    float32           `json:"score"` // cosine similarity, -1..1
	Text     string            `json:"text"`
	Metadata map[string]string `json:"metadata,omitempty"`
}

// VectorIndex stores and searches embeddings, grouped into collections.
type VectorIndex interface {
	Upsert(ctx context.Context, collection string, records []VectorRecord) error
	Delete(ctx context.Context, collection string, ids []string) error
	// Search returns the k most similar records. filter matches metadata exactly (all keys must match).
	Search(ctx context.Context, collection string, query []float32, k int, filter map[string]string) ([]VectorHit, error)
}

// LogStore is the append-only record log (audit now; event topics in Phase 1).
type LogStore interface {
	Append(v any) error
	Scan(fn func(record []byte) error) error
	Close() error
}
