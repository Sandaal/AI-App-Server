// Package blob is the built-in content-addressed file store. Files are stored
// by SHA-256 under <dir>/objects/<first 2 hex>/<rest>, so identical content is
// stored once. Writes are atomic: temp file, fsync, rename.
package blob

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"

	"github.com/Sandaal/AI-App-Server/core/internal/storage"
)

var hashRE = regexp.MustCompile(`^[0-9a-f]{64}$`)

// Store is a content-addressed blob store on local disk.
type Store struct{ dir string }

// Open creates the store directories if needed.
func Open(dir string) (*Store, error) {
	for _, d := range []string{filepath.Join(dir, "objects"), filepath.Join(dir, "tmp")} {
		if err := os.MkdirAll(d, 0o700); err != nil {
			return nil, err
		}
	}
	return &Store{dir: dir}, nil
}

func (s *Store) path(hash string) (string, error) {
	if !hashRE.MatchString(hash) {
		return "", fmt.Errorf("invalid blob hash %q", hash)
	}
	return filepath.Join(s.dir, "objects", hash[:2], hash[2:]), nil
}

// Put stores the content of r and returns its reference.
func (s *Store) Put(ctx context.Context, r io.Reader) (storage.BlobRef, error) {
	tmp, err := os.CreateTemp(filepath.Join(s.dir, "tmp"), "put-*")
	if err != nil {
		return storage.BlobRef{}, err
	}
	tmpName := tmp.Name()
	defer os.Remove(tmpName) // no-op after a successful rename

	h := sha256.New()
	n, err := io.Copy(io.MultiWriter(tmp, h), &ctxReader{ctx: ctx, r: r})
	if err == nil {
		err = tmp.Sync()
	}
	if cerr := tmp.Close(); err == nil {
		err = cerr
	}
	if err != nil {
		return storage.BlobRef{}, err
	}

	ref := storage.BlobRef{Hash: hex.EncodeToString(h.Sum(nil)), Size: n}
	dst, _ := s.path(ref.Hash)
	if _, err := os.Stat(dst); err == nil {
		return ref, nil // already stored
	}
	if err := os.MkdirAll(filepath.Dir(dst), 0o700); err != nil {
		return storage.BlobRef{}, err
	}
	if err := os.Rename(tmpName, dst); err != nil {
		return storage.BlobRef{}, err
	}
	return ref, nil
}

// Open returns a reader for a stored blob.
func (s *Store) Open(_ context.Context, hash string) (io.ReadCloser, error) {
	p, err := s.path(hash)
	if err != nil {
		return nil, err
	}
	f, err := os.Open(p)
	if errors.Is(err, os.ErrNotExist) {
		return nil, storage.ErrNotFound
	}
	return f, err
}

// Has reports whether a blob exists.
func (s *Store) Has(_ context.Context, hash string) (bool, error) {
	p, err := s.path(hash)
	if err != nil {
		return false, err
	}
	_, err = os.Stat(p)
	if errors.Is(err, os.ErrNotExist) {
		return false, nil
	}
	return err == nil, err
}

// Delete removes a blob. Reference counting across apps is Phase 1.
func (s *Store) Delete(_ context.Context, hash string) error {
	p, err := s.path(hash)
	if err != nil {
		return err
	}
	err = os.Remove(p)
	if errors.Is(err, os.ErrNotExist) {
		return storage.ErrNotFound
	}
	return err
}

type ctxReader struct {
	ctx context.Context
	r   io.Reader
}

func (c *ctxReader) Read(p []byte) (int, error) {
	if err := c.ctx.Err(); err != nil {
		return 0, err
	}
	return c.r.Read(p)
}

var _ storage.BlobStore = (*Store)(nil)
