package flatvec

import (
	"context"
	"fmt"
	"math/rand"
	"path/filepath"
	"sort"
	"sync"
	"testing"

	"github.com/Sandaal/AI-App-Server/core/internal/storage"
)

var ctx = context.Background()

func TestSearchOrderAndFilter(t *testing.T) {
	ix, _ := Open("")
	err := ix.Upsert(ctx, "docs", []storage.VectorRecord{
		{ID: "a", Text: "north", Vector: []float32{1, 0}, Metadata: map[string]string{"src": "x"}},
		{ID: "b", Text: "north-east", Vector: []float32{1, 1}, Metadata: map[string]string{"src": "y"}},
		{ID: "c", Text: "east", Vector: []float32{0, 5}, Metadata: map[string]string{"src": "x"}},
		{ID: "d", Text: "south", Vector: []float32{-1, 0}},
	})
	if err != nil {
		t.Fatal(err)
	}
	hits, err := ix.Search(ctx, "docs", []float32{2, 0}, 3, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(hits) != 3 || hits[0].ID != "a" || hits[1].ID != "b" || hits[2].ID != "c" {
		t.Fatalf("order: %+v", hits)
	}
	if hits[0].Score < 0.999 || hits[0].Text != "north" {
		t.Fatalf("top hit %+v", hits[0])
	}
	hits, _ = ix.Search(ctx, "docs", []float32{1, 0}, 10, map[string]string{"src": "x"})
	if len(hits) != 2 || hits[0].ID != "a" || hits[1].ID != "c" {
		t.Fatalf("filter: %+v", hits)
	}
}

func TestValidation(t *testing.T) {
	ix, _ := Open("")
	_ = ix.Upsert(ctx, "c", []storage.VectorRecord{{ID: "a", Vector: []float32{1, 0}}})
	bad := []storage.VectorRecord{
		{ID: "", Vector: []float32{1, 0}},
		{ID: "b", Vector: []float32{1, 0, 0}},
		{ID: "z", Vector: []float32{0, 0}},
	}
	for _, r := range bad {
		if err := ix.Upsert(ctx, "c", []storage.VectorRecord{r}); err == nil {
			t.Fatalf("accepted bad record %+v", r)
		}
	}
	// A batch with one bad record must not partially apply.
	if err := ix.Upsert(ctx, "c", []storage.VectorRecord{{ID: "ok", Vector: []float32{0, 1}}, {ID: "x", Vector: []float32{1}}}); err == nil {
		t.Fatal("bad batch accepted")
	}
	if ix.Count("c") != 1 {
		t.Fatalf("partial apply: count=%d", ix.Count("c"))
	}
	if _, err := ix.Search(ctx, "c", []float32{1, 0, 0}, 1, nil); err == nil {
		t.Fatal("wrong query dimension accepted")
	}
	if hits, err := ix.Search(ctx, "missing", []float32{1}, 1, nil); err != nil || hits != nil {
		t.Fatalf("missing collection: %v %v", hits, err)
	}
}

func TestDeleteAndPersistence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "vectors.gob")
	ix, _ := Open(path)
	_ = ix.Upsert(ctx, "c", []storage.VectorRecord{
		{ID: "a", Text: "A", Vector: []float32{1, 0}, Metadata: map[string]string{"page": "1"}},
		{ID: "b", Text: "B", Vector: []float32{0, 1}},
	})
	_ = ix.Delete(ctx, "c", []string{"b", "nope"})
	if err := ix.Save(); err != nil {
		t.Fatal(err)
	}
	re, err := Open(path)
	if err != nil {
		t.Fatal(err)
	}
	hits, _ := re.Search(ctx, "c", []float32{1, 1}, 5, nil)
	if len(hits) != 1 || hits[0].ID != "a" || hits[0].Text != "A" || hits[0].Metadata["page"] != "1" {
		t.Fatalf("after reload: %+v", hits)
	}
}

// Brute force must match a sorted reference exactly.
func TestMatchesReference(t *testing.T) {
	rng := rand.New(rand.NewSource(1))
	ix, _ := Open("")
	const n, dim, k = 2000, 32, 10
	recs := make([]storage.VectorRecord, n)
	for i := range recs {
		v := make([]float32, dim)
		for j := range v {
			v[j] = rng.Float32()*2 - 1
		}
		recs[i] = storage.VectorRecord{ID: fmt.Sprintf("r%04d", i), Vector: v}
	}
	_ = ix.Upsert(ctx, "c", recs)
	q := make([]float32, dim)
	for j := range q {
		q[j] = rng.Float32()*2 - 1
	}
	qn, _ := normalize(q)
	type pair struct {
		id    string
		score float32
	}
	ref := make([]pair, n)
	for i, r := range recs {
		v, _ := normalize(r.Vector)
		var dot float32
		for j := range v {
			dot += v[j] * qn[j]
		}
		ref[i] = pair{r.ID, dot}
	}
	sort.Slice(ref, func(i, j int) bool { return ref[i].score > ref[j].score })
	hits, _ := ix.Search(ctx, "c", q, k, nil)
	for i := 0; i < k; i++ {
		if hits[i].ID != ref[i].id {
			t.Fatalf("rank %d: got %s want %s", i, hits[i].ID, ref[i].id)
		}
	}
}

func TestConcurrentAccess(t *testing.T) {
	ix, _ := Open(filepath.Join(t.TempDir(), "v.gob"))
	var wg sync.WaitGroup
	for w := 0; w < 4; w++ {
		wg.Add(2)
		go func(w int) {
			defer wg.Done()
			for i := 0; i < 100; i++ {
				_ = ix.Upsert(ctx, "c", []storage.VectorRecord{{ID: fmt.Sprintf("%d-%d", w, i), Vector: []float32{float32(i + 1), 1}}})
				if i%25 == 0 {
					_ = ix.Save()
				}
			}
		}(w)
		go func() {
			defer wg.Done()
			for i := 0; i < 100; i++ {
				_, _ = ix.Search(ctx, "c", []float32{1, 1}, 5, nil)
			}
		}()
	}
	wg.Wait()
	if ix.Count("c") != 400 {
		t.Fatalf("count %d", ix.Count("c"))
	}
}
