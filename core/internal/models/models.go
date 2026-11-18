// Package models is the model gateway: a provider-neutral interface for chat
// and embeddings, provider adapters, and a Gateway that maps logical model
// names from app manifests to provider targets with retry and fallback.
package models

import (
	"context"
	"errors"
	"fmt"
)

// Message is one chat message.
type Message struct {
	Role    string `json:"role"` // system | user | assistant
	Content string `json:"content"`
}

// ChatRequest is a provider-neutral chat request.
type ChatRequest struct {
	Messages    []Message
	MaxTokens   int      // 0 = provider default (Anthropic requires a value; adapter defaults it)
	Temperature *float64 // nil = provider default
}

// Usage reports tokens and the model that actually answered.
type Usage struct {
	InputTokens   int64   `json:"input_tokens"`
	OutputTokens  int64   `json:"output_tokens"`
	Provider      string  `json:"provider"`
	ResolvedModel string  `json:"resolved_model"`
	CostUSD       float64 `json:"cost_usd"`
}

// DeltaFunc receives streamed text. Returning an error stops the stream.
type DeltaFunc func(delta string) error

// Provider is implemented by each model provider adapter.
type Provider interface {
	// Name identifies the provider and model, e.g. "openai/gpt-x".
	Name() string
	// ChatStream streams the response through onDelta and returns final usage.
	ChatStream(ctx context.Context, req ChatRequest, onDelta DeltaFunc) (Usage, error)
}

// Embedder is implemented by providers that offer embeddings.
type Embedder interface {
	Name() string
	Embed(ctx context.Context, inputs []string) ([][]float32, Usage, error)
}

// ProviderError carries an HTTP status so the gateway can decide whether to retry.
type ProviderError struct {
	Provider string
	Status   int
	Body     string
}

func (e *ProviderError) Error() string {
	return fmt.Sprintf("%s: HTTP %d: %s", e.Provider, e.Status, e.Body)
}

// Retryable reports whether a failed call is worth retrying or falling back on.
func Retryable(err error) bool {
	var pe *ProviderError
	if errors.As(err, &pe) {
		return pe.Status == 408 || pe.Status == 409 || pe.Status == 429 || pe.Status >= 500
	}
	// Network errors and unexpected stream ends are retryable; cancellation is not.
	return !errors.Is(err, context.Canceled) && !errors.Is(err, context.DeadlineExceeded) && !errors.Is(err, ErrDeltaRejected)
}

// ErrDeltaRejected wraps an error returned by the caller's DeltaFunc.
var ErrDeltaRejected = errors.New("delta handler stopped the stream")
