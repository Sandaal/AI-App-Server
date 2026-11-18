package blob

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Sandaal/AI-App-Server/core/internal/storage"
)

func TestPutGetDedupDelete(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	s, err := Open(dir)
	if err != nil {
		t.Fatal(err)
	}
	ref, err := s.Put(ctx, strings.NewReader("hello"))
	if err != nil {
		t.Fatal(err)
	}
	// SHA-256 of "hello"
	if ref.Hash != "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824" || ref.Size != 5 {
		t.Fatalf("ref %+v", ref)
	}
	ref2, err := s.Put(ctx, strings.NewReader("hello"))
	if err != nil || ref2 != ref {
		t.Fatalf("dedup: %v %+v", err, ref2)
	}
	if n, _ := os.ReadDir(filepath.Join(dir, "tmp")); len(n) != 0 {
		t.Fatalf("temp files left behind: %d", len(n))
	}

	rc, err := s.Open(ctx, ref.Hash)
	if err != nil {
		t.Fatal(err)
	}
	b, _ := io.ReadAll(rc)
	rc.Close()
	if string(b) != "hello" {
		t.Fatalf("content %q", b)
	}
	if ok, _ := s.Has(ctx, ref.Hash); !ok {
		t.Fatal("Has = false")
	}
	if err := s.Delete(ctx, ref.Hash); err != nil {
		t.Fatal(err)
	}
	if _, err := s.Open(ctx, ref.Hash); !errors.Is(err, storage.ErrNotFound) {
		t.Fatalf("want ErrNotFound, got %v", err)
	}
}

func TestRejectsBadHash(t *testing.T) {
	s, _ := Open(t.TempDir())
	for _, h := range []string{"", "../../etc/passwd", strings.Repeat("A", 64)} {
		if _, err := s.Open(context.Background(), h); err == nil || errors.Is(err, storage.ErrNotFound) {
			t.Fatalf("hash %q should be rejected as invalid, got %v", h, err)
		}
	}
}

func TestPutCancelled(t *testing.T) {
	s, _ := Open(t.TempDir())
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := s.Put(ctx, strings.NewReader("x")); !errors.Is(err, context.Canceled) {
		t.Fatalf("want context.Canceled, got %v", err)
	}
}
