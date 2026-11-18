package models

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
)

// AnthropicConfig configures the Anthropic Messages API adapter.
type AnthropicConfig struct {
	BaseURL    string // default https://api.anthropic.com
	APIKey     string
	Model      string
	Version    string // anthropic-version header; default 2023-06-01
	HTTPClient *http.Client
}

// Anthropic is an adapter for the Anthropic Messages API.
type Anthropic struct{ cfg AnthropicConfig }

// NewAnthropic returns an Anthropic provider.
func NewAnthropic(cfg AnthropicConfig) *Anthropic {
	if cfg.BaseURL == "" {
		cfg.BaseURL = "https://api.anthropic.com"
	}
	cfg.BaseURL = strings.TrimRight(cfg.BaseURL, "/")
	if cfg.Version == "" {
		cfg.Version = "2023-06-01"
	}
	if cfg.HTTPClient == nil {
		cfg.HTTPClient = http.DefaultClient
	}
	return &Anthropic{cfg: cfg}
}

// Name implements Provider.
func (a *Anthropic) Name() string { return "anthropic/" + a.cfg.Model }

// ChatStream implements Provider.
func (a *Anthropic) ChatStream(ctx context.Context, cr ChatRequest, onDelta DeltaFunc) (Usage, error) {
	// The Messages API takes system prompts separately from the conversation.
	var system []string
	msgs := make([]Message, 0, len(cr.Messages))
	for _, m := range cr.Messages {
		if m.Role == "system" {
			system = append(system, m.Content)
			continue
		}
		msgs = append(msgs, m)
	}
	maxTokens := cr.MaxTokens
	if maxTokens <= 0 {
		maxTokens = 4096
	}
	body := map[string]any{"model": a.cfg.Model, "messages": msgs, "max_tokens": maxTokens, "stream": true}
	if len(system) > 0 {
		body["system"] = strings.Join(system, "\n\n")
	}
	if cr.Temperature != nil {
		body["temperature"] = *cr.Temperature
	}
	b, err := json.Marshal(body)
	if err != nil {
		return Usage{}, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, a.cfg.BaseURL+"/v1/messages", bytes.NewReader(b))
	if err != nil {
		return Usage{}, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", a.cfg.APIKey)
	req.Header.Set("anthropic-version", a.cfg.Version)

	resp, err := a.cfg.HTTPClient.Do(req)
	if err != nil {
		return Usage{}, err
	}
	defer resp.Body.Close()
	if resp.StatusCode/100 != 2 {
		eb, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
		return Usage{}, &ProviderError{Provider: a.Name(), Status: resp.StatusCode, Body: strings.TrimSpace(string(eb))}
	}

	usage := Usage{Provider: "anthropic", ResolvedModel: a.cfg.Model}
	stopped := false
	err = readSSE(resp.Body, func(ev sseEvent) error {
		var msg struct {
			Type    string `json:"type"`
			Message struct {
				Model string `json:"model"`
				Usage struct {
					InputTokens  int64 `json:"input_tokens"`
					OutputTokens int64 `json:"output_tokens"`
				} `json:"usage"`
			} `json:"message"`
			Delta struct {
				Type string `json:"type"`
				Text string `json:"text"`
			} `json:"delta"`
			Usage struct {
				OutputTokens int64 `json:"output_tokens"`
			} `json:"usage"`
			Error struct {
				Type    string `json:"type"`
				Message string `json:"message"`
			} `json:"error"`
		}
		if err := json.Unmarshal([]byte(ev.Data), &msg); err != nil {
			return fmt.Errorf("%s: bad stream event: %w", a.Name(), err)
		}
		switch msg.Type {
		case "message_start":
			if msg.Message.Model != "" {
				usage.ResolvedModel = msg.Message.Model
			}
			usage.InputTokens = msg.Message.Usage.InputTokens
			usage.OutputTokens = msg.Message.Usage.OutputTokens
		case "content_block_delta":
			if msg.Delta.Type == "text_delta" && msg.Delta.Text != "" {
				if err := onDelta(msg.Delta.Text); err != nil {
					return fmt.Errorf("%w: %w", ErrDeltaRejected, err)
				}
			}
		case "message_delta":
			usage.OutputTokens = msg.Usage.OutputTokens
		case "message_stop":
			stopped = true
		case "error":
			status := 500
			if msg.Error.Type == "overloaded_error" {
				status = 529
			}
			return &ProviderError{Provider: a.Name(), Status: status, Body: msg.Error.Message}
		}
		return nil
	})
	if err != nil {
		return usage, err
	}
	if !stopped {
		return usage, errors.New(a.Name() + ": stream ended before message_stop")
	}
	return usage, nil
}
