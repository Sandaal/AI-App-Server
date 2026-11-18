// Package logstore is the built-in append-only log: JSON lines written to
// numbered segment files that rotate by size. Phase 0 uses it for the audit
// log; Phase 1 builds event topics on the same segment format.
package logstore

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"

	"github.com/Sandaal/AI-App-Server/core/internal/storage"
)

const segExt = ".jsonl"

// Config controls a log store.
type Config struct {
	MaxSegmentBytes int64 // rotate after this size (default 64 MiB)
	MaxSegments     int   // keep at most this many segments; 0 = keep all
	SyncEveryWrite  bool  // fsync after each append (durable, slower)
}

// Store is an append-only JSON-lines log. Safe for concurrent use.
type Store struct {
	dir string
	cfg Config

	mu   sync.Mutex
	cur  *os.File
	w    *bufio.Writer
	seq  uint64
	size int64
}

// Open opens or creates a log in dir, appending to the newest segment.
func Open(dir string, cfg Config) (*Store, error) {
	if cfg.MaxSegmentBytes <= 0 {
		cfg.MaxSegmentBytes = 64 << 20
	}
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return nil, err
	}
	s := &Store{dir: dir, cfg: cfg}
	segs, err := s.segments()
	if err != nil {
		return nil, err
	}
	seq := uint64(1)
	if len(segs) > 0 {
		seq = segs[len(segs)-1]
	}
	if err := s.openSegment(seq); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *Store) segPath(seq uint64) string {
	return filepath.Join(s.dir, fmt.Sprintf("%020d%s", seq, segExt))
}

func (s *Store) segments() ([]uint64, error) {
	entries, err := os.ReadDir(s.dir)
	if err != nil {
		return nil, err
	}
	var out []uint64
	for _, e := range entries {
		name := e.Name()
		if e.IsDir() || !strings.HasSuffix(name, segExt) {
			continue
		}
		n, err := strconv.ParseUint(strings.TrimSuffix(name, segExt), 10, 64)
		if err != nil {
			continue
		}
		out = append(out, n)
	}
	sort.Slice(out, func(i, j int) bool { return out[i] < out[j] })
	return out, nil
}

func (s *Store) openSegment(seq uint64) error {
	f, err := os.OpenFile(s.segPath(seq), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	st, err := f.Stat()
	if err != nil {
		f.Close()
		return err
	}
	s.cur, s.w, s.seq, s.size = f, bufio.NewWriter(f), seq, st.Size()
	return nil
}

// Append writes one record as a JSON line.
func (s *Store) Append(v any) error {
	b, err := json.Marshal(v)
	if err != nil {
		return err
	}
	b = append(b, '\n')

	s.mu.Lock()
	defer s.mu.Unlock()
	if s.cur == nil {
		return errors.New("log store is closed")
	}
	if s.size > 0 && s.size+int64(len(b)) > s.cfg.MaxSegmentBytes {
		if err := s.rotateLocked(); err != nil {
			return err
		}
	}
	if _, err := s.w.Write(b); err != nil {
		return err
	}
	s.size += int64(len(b))
	if err := s.w.Flush(); err != nil {
		return err
	}
	if s.cfg.SyncEveryWrite {
		return s.cur.Sync()
	}
	return nil
}

func (s *Store) rotateLocked() error {
	if err := s.w.Flush(); err != nil {
		return err
	}
	if err := s.cur.Sync(); err != nil {
		return err
	}
	if err := s.cur.Close(); err != nil {
		return err
	}
	if err := s.openSegment(s.seq + 1); err != nil {
		return err
	}
	return s.pruneLocked()
}

func (s *Store) pruneLocked() error {
	if s.cfg.MaxSegments <= 0 {
		return nil
	}
	segs, err := s.segments()
	if err != nil {
		return err
	}
	for len(segs) > s.cfg.MaxSegments {
		if err := os.Remove(s.segPath(segs[0])); err != nil && !errors.Is(err, os.ErrNotExist) {
			return err
		}
		segs = segs[1:]
	}
	return nil
}

// Scan calls fn for every record, oldest first. A partially written last line
// (from a crash mid-write) is skipped.
func (s *Store) Scan(fn func(record []byte) error) error {
	s.mu.Lock()
	if s.w != nil {
		if err := s.w.Flush(); err != nil {
			s.mu.Unlock()
			return err
		}
	}
	segs, err := s.segments()
	s.mu.Unlock()
	if err != nil {
		return err
	}
	for _, seq := range segs {
		if err := scanFile(s.segPath(seq), fn); err != nil {
			return err
		}
	}
	return nil
}

func scanFile(path string, fn func([]byte) error) error {
	f, err := os.Open(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil // pruned between listing and opening
	}
	if err != nil {
		return err
	}
	defer f.Close()
	r := bufio.NewReaderSize(f, 64*1024)
	for {
		line, err := r.ReadBytes('\n')
		if len(line) > 0 && line[len(line)-1] == '\n' {
			if json.Valid(line[:len(line)-1]) {
				if ferr := fn(line[:len(line)-1]); ferr != nil {
					return ferr
				}
			}
		}
		if errors.Is(err, io.EOF) {
			return nil // an unterminated tail line is ignored
		}
		if err != nil {
			return err
		}
	}
}

// Close flushes and closes the current segment.
func (s *Store) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.cur == nil {
		return nil
	}
	err := s.w.Flush()
	if serr := s.cur.Sync(); err == nil {
		err = serr
	}
	if cerr := s.cur.Close(); err == nil {
		err = cerr
	}
	s.cur, s.w = nil, nil
	return err
}

var _ storage.LogStore = (*Store)(nil)
