package models

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// Price is the cost per million tokens for one provider model.
type Price struct {
	InputPerMTok  float64
	OutputPerMTok float64
}

// Route is a logical model: a primary target followed by fallbacks, in order.
type Route struct {
	Targets []Provider
}

// GatewayConfig controls retries.
type GatewayConfig struct {
	RetriesPerTarget int           // extra attempts on a retryable error before falling back (default 1)
	RetryBackoff     time.Duration // base backoff, doubled each retry (default 500ms)
}

// Gateway maps logical model names (from app manifests) to provider targets.
type Gateway struct {
	cfg GatewayConfig
	log *slog.Logger

	mu       sync.RWMutex
	routes   map[string]Route    // chat routes
	embed    map[string]Embedder // embedding routes
	prices   map[string]Price    // keyed by Provider.Name()
	sleepCtx func(context.Context, time.Duration) error
}

// NewGateway returns an empty gateway.
func NewGateway(cfg GatewayConfig, log *slog.Logger) *Gateway {
	if cfg.RetriesPerTarget < 0 {
		cfg.RetriesPerTarget = 0
	} else if cfg.RetriesPerTarget == 0 {
		cfg.RetriesPerTarget = 1
	}
	if cfg.RetryBackoff <= 0 {
		cfg.RetryBackoff = 500 * time.Millisecond
	}
	return &Gateway{
		cfg: cfg, log: log,
		routes: map[string]Route{}, embed: map[string]Embedder{}, prices: map[string]Price{},
		sleepCtx: sleepCtx,
	}
}

// SetRoute registers or replaces a logical chat model.
func (g *Gateway) SetRoute(name string, r Route) error {
	if len(r.Targets) == 0 {
		return fmt.Errorf("route %q has no targets", name)
	}
	g.mu.Lock()
	g.routes[name] = r
	g.mu.Unlock()
	return nil
}

// SetEmbedder registers or replaces a logical embedding model.
func (g *Gateway) SetEmbedder(name string, e Embedder) {
	g.mu.Lock()
	g.embed[name] = e
	g.mu.Unlock()
}

// SetPrice sets the price used for cost accounting of one provider model.
func (g *Gateway) SetPrice(providerName string, p Price) {
	g.mu.Lock()
	g.prices[providerName] = p
	g.mu.Unlock()
}

// ErrUnknownModel is returned for a logical name with no route.
var ErrUnknownModel = errors.New("unknown model")

// Chat streams a response from the logical model, retrying and falling back on
// retryable errors. Fallback only happens before any text has been streamed:
// once the caller has received output, switching models would corrupt it.
func (g *Gateway) Chat(ctx context.Context, model string, req ChatRequest, onDelta DeltaFunc) (Usage, error) {
	g.mu.RLock()
	route, ok := g.routes[model]
	g.mu.RUnlock()
	if !ok {
		return Usage{}, fmt.Errorf("%w %q", ErrUnknownModel, model)
	}

	var lastErr error
	for ti, target := range route.Targets {
		for attempt := 0; attempt <= g.cfg.RetriesPerTarget; attempt++ {
			if attempt > 0 {
				if err := g.sleepCtx(ctx, g.cfg.RetryBackoff<<(attempt-1)); err != nil {
					return Usage{}, err
				}
			}
			streamed := false
			usage, err := target.ChatStream(ctx, req, func(d string) error {
				streamed = true
				return onDelta(d)
			})
			if err == nil {
				usage.CostUSD = g.cost(target.Name(), usage)
				if ti > 0 {
					g.logInfo("model fallback used", "model", model, "target", target.Name())
				}
				return usage, nil
			}
			lastErr = err
			if streamed || !Retryable(err) {
				return usage, err
			}
			g.logWarn("model call failed", "model", model, "target", target.Name(), "attempt", attempt+1, "error", err)
		}
	}
	return Usage{}, fmt.Errorf("all targets failed for model %q: %w", model, lastErr)
}

// Embed returns embeddings from the logical embedding model.
func (g *Gateway) Embed(ctx context.Context, model string, inputs []string) ([][]float32, Usage, error) {
	g.mu.RLock()
	e, ok := g.embed[model]
	g.mu.RUnlock()
	if !ok {
		return nil, Usage{}, fmt.Errorf("%w %q", ErrUnknownModel, model)
	}
	var lastErr error
	for attempt := 0; attempt <= g.cfg.RetriesPerTarget; attempt++ {
		if attempt > 0 {
			if err := g.sleepCtx(ctx, g.cfg.RetryBackoff<<(attempt-1)); err != nil {
				return nil, Usage{}, err
			}
		}
		vecs, usage, err := e.Embed(ctx, inputs)
		if err == nil {
			usage.CostUSD = g.cost(e.Name(), usage)
			return vecs, usage, nil
		}
		lastErr = err
		if !Retryable(err) {
			break
		}
	}
	return nil, Usage{}, lastErr
}

func (g *Gateway) cost(name string, u Usage) float64 {
	g.mu.RLock()
	p, ok := g.prices[name]
	g.mu.RUnlock()
	if !ok {
		return 0
	}
	return (float64(u.InputTokens)*p.InputPerMTok + float64(u.OutputTokens)*p.OutputPerMTok) / 1e6
}

func (g *Gateway) logInfo(msg string, args ...any) {
	if g.log != nil {
		g.log.Info(msg, args...)
	}
}

func (g *Gateway) logWarn(msg string, args ...any) {
	if g.log != nil {
		g.log.Warn(msg, args...)
	}
}

func sleepCtx(ctx context.Context, d time.Duration) error {
	t := time.NewTimer(d)
	defer t.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-t.C:
		return nil
	}
}
