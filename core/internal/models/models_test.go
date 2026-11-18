package models

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

func collect(t *testing.T) (*strings.Builder, DeltaFunc) {
	t.Helper()
	var b strings.Builder
	return &b, func(d string) error { b.WriteString(d); return nil }
}

func TestReadSSE(t *testing.T) {
	in := ": keep-alive\n\nevent: a\ndata: one\ndata: two\n\ndata: three\n\n"
	var got []sseEvent
	if err := readSSE(strings.NewReader(in), func(e sseEvent) error { got = append(got, e); return nil }); err != nil {
		t.Fatal(err)
	}
	if len(got) != 2 || got[0].Event != "a" || got[0].Data != "one\ntwo" || got[1].Data != "three" {
		t.Fatalf("unexpected events: %+v", got)
	}
}

func openAIStream(w http.ResponseWriter, parts []string, usage bool, done bool) {
	w.Header().Set("Content-Type", "text/event-stream")
	for _, p := range parts {
		b, _ := json.Marshal(map[string]any{"model": "gpt-test-2026", "choices": []any{map[string]any{"delta": map[string]string{"content": p}}}})
		fmt.Fprintf(w, "data: %s\n\n", b)
	}
	if usage {
		fmt.Fprint(w, `data: {"choices":[],"usage":{"prompt_tokens":12,"completion_tokens":3}}`+"\n\n")
	}
	if done {
		fmt.Fprint(w, "data: [DONE]\n\n")
	}
}

func TestOpenAIChatStream(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/chat/completions" || r.Header.Get("Authorization") != "Bearer k" {
			t.Errorf("bad request: %s auth=%q", r.URL.Path, r.Header.Get("Authorization"))
		}
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		if body["model"] != "gpt-test" || body["stream"] != true {
			t.Errorf("bad body: %v", body)
		}
		openAIStream(w, []string{"Hel", "lo"}, true, true)
	}))
	defer srv.Close()

	p := NewOpenAI(OpenAIConfig{BaseURL: srv.URL + "/v1/", APIKey: "k", Model: "gpt-test"})
	out, fn := collect(t)
	u, err := p.ChatStream(context.Background(), ChatRequest{Messages: []Message{{Role: "user", Content: "hi"}}}, fn)
	if err != nil {
		t.Fatal(err)
	}
	if out.String() != "Hello" || u.InputTokens != 12 || u.OutputTokens != 3 || u.ResolvedModel != "gpt-test-2026" || u.Provider != "openai" {
		t.Fatalf("got %q %+v", out.String(), u)
	}
}

func TestAzureOpenAIURLAndHeader(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/openai/deployments/chat-dep/chat/completions" || r.URL.Query().Get("api-version") != "2024-10-21" {
			t.Errorf("bad azure url: %s", r.URL.String())
		}
		if r.Header.Get("api-key") != "az" || r.Header.Get("Authorization") != "" {
			t.Errorf("bad azure auth headers")
		}
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		if _, has := body["model"]; has {
			t.Errorf("azure body must not include model")
		}
		openAIStream(w, []string{"ok"}, false, true)
	}))
	defer srv.Close()
	p := NewOpenAI(OpenAIConfig{BaseURL: srv.URL, APIKey: "az", Model: "chat-dep", Azure: true})
	out, fn := collect(t)
	if _, err := p.ChatStream(context.Background(), ChatRequest{}, fn); err != nil || out.String() != "ok" {
		t.Fatalf("err=%v out=%q", err, out.String())
	}
	if p.Name() != "azure-openai/chat-dep" {
		t.Fatalf("name %q", p.Name())
	}
}

func TestOpenAIErrors(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, `{"error":"rate limited"}`, http.StatusTooManyRequests)
	}))
	defer srv.Close()

	p := NewOpenAI(OpenAIConfig{BaseURL: srv.URL, Model: "m"})
	_, err := p.ChatStream(context.Background(), ChatRequest{}, func(string) error { return nil })
	var pe *ProviderError
	if !errors.As(err, &pe) || pe.Status != 429 || !Retryable(err) {
		t.Fatalf("want retryable 429, got %v", err)
	}

	// A stream that ends without [DONE] is an error (and retryable).
	srv2 := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		openAIStream(w, []string{"partial"}, false, false)
	}))
	defer srv2.Close()
	_, err = NewOpenAI(OpenAIConfig{BaseURL: srv2.URL, Model: "m"}).ChatStream(context.Background(), ChatRequest{}, func(string) error { return nil })
	if err == nil || !strings.Contains(err.Error(), "[DONE]") {
		t.Fatalf("want truncated-stream error, got %v", err)
	}
}

func TestOpenAIEmbed(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/embeddings" {
			t.Errorf("path %s", r.URL.Path)
		}
		// Return out of order to check index handling.
		fmt.Fprint(w, `{"model":"emb","data":[{"index":1,"embedding":[0,1]},{"index":0,"embedding":[1,0]}],"usage":{"prompt_tokens":4}}`)
	}))
	defer srv.Close()
	vecs, u, err := NewOpenAI(OpenAIConfig{BaseURL: srv.URL, Model: "emb"}).Embed(context.Background(), []string{"a", "b"})
	if err != nil {
		t.Fatal(err)
	}
	if vecs[0][0] != 1 || vecs[1][1] != 1 || u.InputTokens != 4 {
		t.Fatalf("got %v %+v", vecs, u)
	}
}

func TestAnthropicChatStream(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/messages" || r.Header.Get("x-api-key") != "ak" || r.Header.Get("anthropic-version") == "" {
			t.Errorf("bad request %s", r.URL.Path)
		}
		var body struct {
			System    string    `json:"system"`
			Messages  []Message `json:"messages"`
			MaxTokens int       `json:"max_tokens"`
		}
		b, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(b, &body)
		if body.System != "be brief" || len(body.Messages) != 1 || body.MaxTokens != 4096 {
			t.Errorf("bad body: %s", b)
		}
		w.Header().Set("Content-Type", "text/event-stream")
		fmt.Fprint(w, "event: message_start\ndata: {\"type\":\"message_start\",\"message\":{\"model\":\"claude-test\",\"usage\":{\"input_tokens\":20,\"output_tokens\":1}}}\n\n")
		fmt.Fprint(w, "event: content_block_delta\ndata: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"text_delta\",\"text\":\"Hi \"}}\n\n")
		fmt.Fprint(w, "event: ping\ndata: {\"type\":\"ping\"}\n\n")
		fmt.Fprint(w, "event: content_block_delta\ndata: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"text_delta\",\"text\":\"there\"}}\n\n")
		fmt.Fprint(w, "event: message_delta\ndata: {\"type\":\"message_delta\",\"usage\":{\"output_tokens\":5}}\n\n")
		fmt.Fprint(w, "event: message_stop\ndata: {\"type\":\"message_stop\"}\n\n")
	}))
	defer srv.Close()

	p := NewAnthropic(AnthropicConfig{BaseURL: srv.URL, APIKey: "ak", Model: "claude-x"})
	out, fn := collect(t)
	u, err := p.ChatStream(context.Background(), ChatRequest{Messages: []Message{{Role: "system", Content: "be brief"}, {Role: "user", Content: "hello"}}}, fn)
	if err != nil {
		t.Fatal(err)
	}
	if out.String() != "Hi there" || u.InputTokens != 20 || u.OutputTokens != 5 || u.ResolvedModel != "claude-test" {
		t.Fatalf("got %q %+v", out.String(), u)
	}
}

func TestAnthropicStreamError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, "event: error\ndata: {\"type\":\"error\",\"error\":{\"type\":\"overloaded_error\",\"message\":\"Overloaded\"}}\n\n")
	}))
	defer srv.Close()
	_, err := NewAnthropic(AnthropicConfig{BaseURL: srv.URL, Model: "m"}).ChatStream(context.Background(), ChatRequest{}, func(string) error { return nil })
	if !Retryable(err) {
		t.Fatalf("overloaded should be retryable: %v", err)
	}
}

// fakeProvider scripts a sequence of outcomes.
type fakeProvider struct {
	name  string
	calls atomic.Int32
	steps []func(DeltaFunc) (Usage, error)
}

func (f *fakeProvider) Name() string { return f.name }
func (f *fakeProvider) ChatStream(_ context.Context, _ ChatRequest, on DeltaFunc) (Usage, error) {
	i := int(f.calls.Add(1)) - 1
	if i >= len(f.steps) {
		i = len(f.steps) - 1
	}
	return f.steps[i](on)
}

func fail(status int) func(DeltaFunc) (Usage, error) {
	return func(DeltaFunc) (Usage, error) { return Usage{}, &ProviderError{Status: status} }
}

func succeed(text string) func(DeltaFunc) (Usage, error) {
	return func(on DeltaFunc) (Usage, error) {
		if err := on(text); err != nil {
			return Usage{}, err
		}
		return Usage{InputTokens: 1000, OutputTokens: 500}, nil
	}
}

func newTestGateway() *Gateway {
	g := NewGateway(GatewayConfig{RetriesPerTarget: 1, RetryBackoff: time.Millisecond}, nil)
	g.sleepCtx = func(context.Context, time.Duration) error { return nil }
	return g
}

func TestGatewayRetryThenSuccessWithCost(t *testing.T) {
	g := newTestGateway()
	p := &fakeProvider{name: "a", steps: []func(DeltaFunc) (Usage, error){fail(429), succeed("ok")}}
	_ = g.SetRoute("chat", Route{Targets: []Provider{p}})
	g.SetPrice("a", Price{InputPerMTok: 2, OutputPerMTok: 10})
	out, fn := collect(t)
	u, err := g.Chat(context.Background(), "chat", ChatRequest{}, fn)
	if err != nil || out.String() != "ok" || p.calls.Load() != 2 {
		t.Fatalf("err=%v out=%q calls=%d", err, out.String(), p.calls.Load())
	}
	if want := (1000*2.0 + 500*10.0) / 1e6; u.CostUSD != want {
		t.Fatalf("cost %v, want %v", u.CostUSD, want)
	}
}

func TestGatewayFallback(t *testing.T) {
	g := newTestGateway()
	primary := &fakeProvider{name: "a", steps: []func(DeltaFunc) (Usage, error){fail(503)}}
	backup := &fakeProvider{name: "b", steps: []func(DeltaFunc) (Usage, error){succeed("from b")}}
	_ = g.SetRoute("chat", Route{Targets: []Provider{primary, backup}})
	out, fn := collect(t)
	if _, err := g.Chat(context.Background(), "chat", ChatRequest{}, fn); err != nil || out.String() != "from b" {
		t.Fatalf("err=%v out=%q", err, out.String())
	}
	if primary.calls.Load() != 2 {
		t.Fatalf("primary should be tried twice (1 retry), got %d", primary.calls.Load())
	}
}

func TestGatewayNoFallbackAfterStreaming(t *testing.T) {
	g := newTestGateway()
	partial := &fakeProvider{name: "a", steps: []func(DeltaFunc) (Usage, error){func(on DeltaFunc) (Usage, error) {
		_ = on("half")
		return Usage{}, &ProviderError{Status: 500}
	}}}
	backup := &fakeProvider{name: "b", steps: []func(DeltaFunc) (Usage, error){succeed("never")}}
	_ = g.SetRoute("chat", Route{Targets: []Provider{partial, backup}})
	out, fn := collect(t)
	if _, err := g.Chat(context.Background(), "chat", ChatRequest{}, fn); err == nil {
		t.Fatal("expected error")
	}
	if out.String() != "half" || backup.calls.Load() != 0 {
		t.Fatalf("must not fall back after output: out=%q backup calls=%d", out.String(), backup.calls.Load())
	}
}

func TestGatewayNonRetryableAndUnknown(t *testing.T) {
	g := newTestGateway()
	p := &fakeProvider{name: "a", steps: []func(DeltaFunc) (Usage, error){fail(400)}}
	backup := &fakeProvider{name: "b", steps: []func(DeltaFunc) (Usage, error){succeed("x")}}
	_ = g.SetRoute("chat", Route{Targets: []Provider{p, backup}})
	if _, err := g.Chat(context.Background(), "chat", ChatRequest{}, func(string) error { return nil }); err == nil || p.calls.Load() != 1 || backup.calls.Load() != 0 {
		t.Fatalf("400 must not retry or fall back: err=%v calls=%d/%d", err, p.calls.Load(), backup.calls.Load())
	}
	if _, err := g.Chat(context.Background(), "nope", ChatRequest{}, nil); !errors.Is(err, ErrUnknownModel) {
		t.Fatalf("want ErrUnknownModel, got %v", err)
	}
	if err := g.SetRoute("empty", Route{}); err == nil {
		t.Fatal("empty route accepted")
	}
}

func TestGatewayDeltaRejectionStops(t *testing.T) {
	g := newTestGateway()
	p := &fakeProvider{name: "a", steps: []func(DeltaFunc) (Usage, error){func(on DeltaFunc) (Usage, error) {
		if err := on("x"); err != nil {
			return Usage{}, fmt.Errorf("%w: %w", ErrDeltaRejected, err)
		}
		return Usage{}, nil
	}}}
	_ = g.SetRoute("chat", Route{Targets: []Provider{p}})
	_, err := g.Chat(context.Background(), "chat", ChatRequest{}, func(string) error { return errors.New("client gone") })
	if !errors.Is(err, ErrDeltaRejected) || p.calls.Load() != 1 {
		t.Fatalf("err=%v calls=%d", err, p.calls.Load())
	}
}
