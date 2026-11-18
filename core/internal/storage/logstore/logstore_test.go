package logstore

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"testing"
)

type rec struct {
	N   int    `json:"n"`
	Msg string `json:"msg"`
}

func readAll(t *testing.T, s *Store) []rec {
	t.Helper()
	var out []rec
	if err := s.Scan(func(b []byte) error {
		var r rec
		if err := json.Unmarshal(b, &r); err != nil {
			return err
		}
		out = append(out, r)
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	return out
}

func TestAppendScanReopen(t *testing.T) {
	dir := t.TempDir()
	s, err := Open(dir, Config{})
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 3; i++ {
		if err := s.Append(rec{N: i, Msg: "x"}); err != nil {
			t.Fatal(err)
		}
	}
	if got := readAll(t, s); len(got) != 3 || got[2].N != 2 {
		t.Fatalf("got %+v", got)
	}
	_ = s.Close()
	if err := s.Append(rec{}); err == nil {
		t.Fatal("append after close succeeded")
	}

	s2, _ := Open(dir, Config{})
	_ = s2.Append(rec{N: 3})
	if got := readAll(t, s2); len(got) != 4 || got[3].N != 3 {
		t.Fatalf("after reopen: %+v", got)
	}
	_ = s2.Close()
}

func TestRotationAndRetention(t *testing.T) {
	dir := t.TempDir()
	s, _ := Open(dir, Config{MaxSegmentBytes: 100, MaxSegments: 3})
	for i := 0; i < 50; i++ {
		if err := s.Append(rec{N: i, Msg: "0123456789"}); err != nil {
			t.Fatal(err)
		}
	}
	segs, _ := s.segments()
	if len(segs) != 3 {
		t.Fatalf("want 3 segments kept, got %d", len(segs))
	}
	got := readAll(t, s)
	if len(got) == 0 || got[len(got)-1].N != 49 {
		t.Fatalf("newest record missing: %+v", got)
	}
	for i := 1; i < len(got); i++ {
		if got[i].N != got[i-1].N+1 {
			t.Fatalf("records out of order or missing: %+v", got)
		}
	}
	_ = s.Close()
}

func TestTornTailIgnored(t *testing.T) {
	dir := t.TempDir()
	s, _ := Open(dir, Config{})
	_ = s.Append(rec{N: 1})
	_ = s.Close()
	// Simulate a crash mid-write: an unterminated partial line.
	f, _ := os.OpenFile(s.segPath(1), os.O_APPEND|os.O_WRONLY, 0o600)
	fmt.Fprint(f, `{"n":2,"ms`)
	f.Close()

	s2, _ := Open(dir, Config{})
	defer s2.Close()
	if got := readAll(t, s2); len(got) != 1 || got[0].N != 1 {
		t.Fatalf("got %+v", got)
	}
}

func TestConcurrentAppends(t *testing.T) {
	s, _ := Open(t.TempDir(), Config{MaxSegmentBytes: 512})
	defer s.Close()
	var wg sync.WaitGroup
	for w := 0; w < 8; w++ {
		wg.Add(1)
		go func(w int) {
			defer wg.Done()
			for i := 0; i < 50; i++ {
				_ = s.Append(rec{N: w*1000 + i})
			}
		}(w)
	}
	wg.Wait()
	if got := readAll(t, s); len(got) != 400 {
		t.Fatalf("want 400 records, got %d", len(got))
	}
}
