// Package flatvec is the Phase 0 vector index: exact (brute-force) cosine
// search over vectors held in memory, persisted to one file per index with
// atomic snapshots. It is exact and simple. Measured cost is linear in size:
// about 170 ms per query at 100K vectors of 1536 dimensions on one core (2026-11),
// so it suits Phase 0 collections of up to ~10-20K chunks. Phase 1 replaces it
// with HNSW behind the same storage.VectorIndex interface.
package flatvec

import (
	"container/heap"
	"context"
	"encoding/gob"
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sync"

	"github.com/Sandaal/AI-App-Server/core/internal/storage"
)

type record struct {
	Text     string
	Vector   []float32 // unit-normalized
	Metadata map[string]string
}

type collection struct {
	Dim     int
	Records map[string]record
}

// Index is an in-memory exact vector index. Safe for concurrent use.
type Index struct {
	mu    sync.RWMutex
	path  string // snapshot file; empty = memory only
	colls map[string]*collection
	dirty bool
}

// Open loads the index from path, or starts empty if the file does not exist.
// Pass an empty path for a memory-only index.
func Open(path string) (*Index, error) {
	ix := &Index{path: path, colls: map[string]*collection{}}
	if path == "" {
		return ix, nil
	}
	f, err := os.Open(path)
	if errors.Is(err, os.ErrNotExist) {
		return ix, nil
	}
	if err != nil {
		return nil, err
	}
	defer f.Close()
	if err := gob.NewDecoder(f).Decode(&ix.colls); err != nil {
		return nil, fmt.Errorf("load vector index %s: %w", path, err)
	}
	return ix, nil
}

func normalize(v []float32) ([]float32, error) {
	var sum float64
	for _, x := range v {
		sum += float64(x) * float64(x)
	}
	if sum == 0 || math.IsNaN(sum) || math.IsInf(sum, 0) {
		return nil, errors.New("vector must be non-zero and finite")
	}
	inv := float32(1 / math.Sqrt(sum))
	out := make([]float32, len(v))
	for i, x := range v {
		out[i] = x * inv
	}
	return out, nil
}

// Upsert adds or replaces records. All vectors in a collection must share one dimension.
func (ix *Index) Upsert(_ context.Context, coll string, recs []storage.VectorRecord) error {
	if coll == "" {
		return errors.New("collection name is required")
	}
	// Validate and normalize everything before changing state.
	prepared := make([]record, len(recs))
	dim := 0
	ix.mu.RLock()
	if c, ok := ix.colls[coll]; ok {
		dim = c.Dim
	}
	ix.mu.RUnlock()
	for i, r := range recs {
		if r.ID == "" {
			return fmt.Errorf("record %d: id is required", i)
		}
		if dim == 0 {
			dim = len(r.Vector)
		}
		if len(r.Vector) != dim {
			return fmt.Errorf("record %q: dimension %d, collection uses %d", r.ID, len(r.Vector), dim)
		}
		v, err := normalize(r.Vector)
		if err != nil {
			return fmt.Errorf("record %q: %w", r.ID, err)
		}
		prepared[i] = record{Text: r.Text, Vector: v, Metadata: r.Metadata}
	}

	ix.mu.Lock()
	defer ix.mu.Unlock()
	c, ok := ix.colls[coll]
	if !ok {
		c = &collection{Dim: dim, Records: map[string]record{}}
		ix.colls[coll] = c
	} else if c.Dim != dim {
		return fmt.Errorf("collection %q dimension changed concurrently", coll)
	}
	for i, r := range recs {
		c.Records[r.ID] = prepared[i]
	}
	ix.dirty = true
	return nil
}

// Delete removes records by id. Missing ids are ignored.
func (ix *Index) Delete(_ context.Context, coll string, ids []string) error {
	ix.mu.Lock()
	defer ix.mu.Unlock()
	c, ok := ix.colls[coll]
	if !ok {
		return nil
	}
	for _, id := range ids {
		delete(c.Records, id)
	}
	ix.dirty = true
	return nil
}

// Search returns up to k records by cosine similarity, best first.
func (ix *Index) Search(ctx context.Context, coll string, query []float32, k int, filter map[string]string) ([]storage.VectorHit, error) {
	if k <= 0 {
		return nil, nil
	}
	q, err := normalize(query)
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	ix.mu.RLock()
	defer ix.mu.RUnlock()
	c, ok := ix.colls[coll]
	if !ok {
		return nil, nil
	}
	if len(q) != c.Dim {
		return nil, fmt.Errorf("query dimension %d, collection uses %d", len(q), c.Dim)
	}

	h := &minHeap{}
	n := 0
	for id, r := range c.Records {
		if n++; n%4096 == 0 && ctx.Err() != nil {
			return nil, ctx.Err()
		}
		if !matches(r.Metadata, filter) {
			continue
		}
		var dot float32
		for i := range q {
			dot += q[i] * r.Vector[i]
		}
		if h.Len() < k {
			heap.Push(h, scored{id, dot})
		} else if dot > (*h)[0].score || (dot == (*h)[0].score && id < (*h)[0].id) {
			(*h)[0] = scored{id, dot}
			heap.Fix(h, 0)
		}
	}
	hits := make([]storage.VectorHit, h.Len())
	for i := len(hits) - 1; i >= 0; i-- {
		s := heap.Pop(h).(scored)
		r := c.Records[s.id]
		hits[i] = storage.VectorHit{ID: s.id, Score: s.score, Text: r.Text, Metadata: r.Metadata}
	}
	return hits, nil
}

// Count returns the number of records in a collection.
func (ix *Index) Count(coll string) int {
	ix.mu.RLock()
	defer ix.mu.RUnlock()
	if c, ok := ix.colls[coll]; ok {
		return len(c.Records)
	}
	return 0
}

// Save writes a snapshot atomically if anything changed since the last save.
func (ix *Index) Save() error {
	if ix.path == "" {
		return nil
	}
	// Full lock: the snapshot must be consistent and dirty is updated below.
	// Searches wait during a save; acceptable at Phase 0 sizes.
	ix.mu.Lock()
	defer ix.mu.Unlock()
	if !ix.dirty {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(ix.path), 0o700); err != nil {
		return err
	}
	tmp, err := os.CreateTemp(filepath.Dir(ix.path), filepath.Base(ix.path)+".tmp-*")
	if err != nil {
		return err
	}
	defer os.Remove(tmp.Name())
	err = gob.NewEncoder(tmp).Encode(ix.colls)
	if err == nil {
		err = tmp.Sync()
	}
	if cerr := tmp.Close(); err == nil {
		err = cerr
	}
	if err != nil {
		return err
	}
	if err := os.Rename(tmp.Name(), ix.path); err != nil {
		return err
	}
	ix.dirty = false
	return nil
}

func matches(md, filter map[string]string) bool {
	for k, v := range filter {
		if md[k] != v {
			return false
		}
	}
	return true
}

type scored struct {
	id    string
	score float32
}

// minHeap keeps the current top-k with the worst at the root. Ties break by id
// so results are deterministic.
type minHeap []scored

func (h minHeap) Len() int { return len(h) }
func (h minHeap) Less(i, j int) bool {
	if h[i].score != h[j].score {
		return h[i].score < h[j].score
	}
	return h[i].id > h[j].id
}
func (h minHeap) Swap(i, j int) { h[i], h[j] = h[j], h[i] }
func (h *minHeap) Push(x any)   { *h = append(*h, x.(scored)) }
func (h *minHeap) Pop() any {
	old := *h
	x := old[len(old)-1]
	*h = old[:len(old)-1]
	return x
}

var _ storage.VectorIndex = (*Index)(nil)
