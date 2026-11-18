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

// OpenAIConfig configures an OpenAI-compatible provider. It also covers
// Azure OpenAI (set Azure) and any OpenAI-compatible server (Ollama, vLLM).
type OpenAIConfig struct {
	BaseURL string // e.g. https://api.openai.com/v1, or https://<res>.openai.azure.com for Azure
	APIKey  string
	Model   string // model name; for Azure, the deployment name

	Azure      bool   // use Azure OpenAI URL layout and api-key header
	APIVersion string // Azure only, e.g. "2024-10-21"

	HTTPClient *http.Client
}

// OpenAI is an adapter for OpenAI-compatible chat and embeddings APIs.
type OpenAI struct{ cfg OpenAIConfig }

// NewOpenAI returns an OpenAI-compatible provider.
func NewOpenAI(cfg OpenAIConfig) *OpenAI {
	if cfg.HTTPClient == nil {
		cfg.HTTPClient = http.DefaultClient
	}
	cfg.BaseURL = strings.TrimRight(cfg.BaseURL, "/")
	if cfg.Azure && cfg.APIVersion == "" {
		cfg.APIVersion = "2024-10-21"
	}
	return &OpenAI{cfg: cfg}
}

func (o *OpenAI) providerName() string {
	if o.cfg.Azure {
		return "azure-openai"
	}
	return "openai"
}

// Name implements Provider.
func (o *OpenAI) Name() string { return o.providerName() + "/" + o.cfg.Model }

func (o *OpenAI) url(op string) string {
	if o.cfg.Azure {
		return fmt.Sprintf("%s/openai/deployments/%s/%s?api-version=%s", o.cfg.BaseURL, o.cfg.Model, op, o.cfg.APIVersion)
	}
	return o.cfg.BaseURL + "/" + op
}

func (o *OpenAI) newRequest(ctx context.Context, op string, body any) (*http.Request, error) {
	b, err := json.Marshal(body)
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, o.url(op), bytes.NewReader(b))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	if o.cfg.Azure {
		req.Header.Set("api-key", o.cfg.APIKey)
	} else if o.cfg.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+o.cfg.APIKey)
	}
	return req, nil
}

func (o *OpenAI) do(req *http.Request) (*http.Response, error) {
	resp, err := o.cfg.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode/100 != 2 {
		defer resp.Body.Close()
		b, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
		return nil, &ProviderError{Provider: o.Name(), Status: resp.StatusCode, Body: strings.TrimSpace(string(b))}
	}
	return resp, nil
}

// ChatStream implements Provider.
func (o *OpenAI) ChatStream(ctx context.Context, cr ChatRequest, onDelta DeltaFunc) (Usage, error) {
	body := map[string]any{
		"messages":       cr.Messages,
		"stream":         true,
		"stream_options": map[string]bool{"include_usage": true},
	}
	if !o.cfg.Azure {
		body["model"] = o.cfg.Model
	}
	if cr.MaxTokens > 0 {
		body["max_tokens"] = cr.MaxTokens
	}
	if cr.Temperature != nil {
		body["temperature"] = *cr.Temperature
	}
	req, err := o.newRequest(ctx, "chat/completions", body)
	if err != nil {
		return Usage{}, err
	}
	resp, err := o.do(req)
	if err != nil {
		return Usage{}, err
	}
	defer resp.Body.Close()

	usage := Usage{Provider: o.providerName(), ResolvedModel: o.cfg.Model}
	done := false
	err = readSSE(resp.Body, func(ev sseEvent) error {
		if ev.Data == "[DONE]" {
			done = true
			return nil
		}
		var chunk struct {
			Model   string `json:"model"`
			Choices []struct {
				Delta struct {
					Content string `json:"content"`
				} `json:"delta"`
			} `json:"choices"`
			Usage *struct {
				PromptTokens     int64 `json:"prompt_tokens"`
				CompletionTokens int64 `json:"completion_tokens"`
			} `json:"usage"`
			Error *struct {
				Message string `json:"message"`
			} `json:"error"`
		}
		if err := json.Unmarshal([]byte(ev.Data), &chunk); err != nil {
			return fmt.Errorf("%s: bad stream chunk: %w", o.Name(), err)
		}
		if chunk.Error != nil {
			return &ProviderError{Provider: o.Name(), Status: 500, Body: chunk.Error.Message}
		}
		if chunk.Model != "" {
			usage.ResolvedModel = chunk.Model
		}
		if chunk.Usage != nil {
			usage.InputTokens = chunk.Usage.PromptTokens
			usage.OutputTokens = chunk.Usage.CompletionTokens
		}
		for _, c := range chunk.Choices {
			if c.Delta.Content != "" {
				if err := onDelta(c.Delta.Content); err != nil {
					return fmt.Errorf("%w: %w", ErrDeltaRejected, err)
				}
			}
		}
		return nil
	})
	if err != nil {
		return usage, err
	}
	if !done {
		return usage, errors.New(o.Name() + ": stream ended before [DONE]")
	}
	return usage, nil
}

// Embed implements Embedder.
func (o *OpenAI) Embed(ctx context.Context, inputs []string) ([][]float32, Usage, error) {
	body := map[string]any{"input": inputs}
	if !o.cfg.Azure {
		body["model"] = o.cfg.Model
	}
	req, err := o.newRequest(ctx, "embeddings", body)
	if err != nil {
		return nil, Usage{}, err
	}
	resp, err := o.do(req)
	if err != nil {
		return nil, Usage{}, err
	}
	defer resp.Body.Close()
	var out struct {
		Model string `json:"model"`
		Data  []struct {
			Index     int       `json:"index"`
			Embedding []float32 `json:"embedding"`
		} `json:"data"`
		Usage struct {
			PromptTokens int64 `json:"prompt_tokens"`
		} `json:"usage"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, Usage{}, fmt.Errorf("%s: decode embeddings: %w", o.Name(), err)
	}
	if len(out.Data) != len(inputs) {
		return nil, Usage{}, fmt.Errorf("%s: got %d embeddings for %d inputs", o.Name(), len(out.Data), len(inputs))
	}
	vecs := make([][]float32, len(inputs))
	for _, d := range out.Data {
		if d.Index < 0 || d.Index >= len(vecs) {
			return nil, Usage{}, fmt.Errorf("%s: embedding index %d out of range", o.Name(), d.Index)
		}
		vecs[d.Index] = d.Embedding
	}
	model := o.cfg.Model
	if out.Model != "" {
		model = out.Model
	}
	return vecs, Usage{InputTokens: out.Usage.PromptTokens, Provider: o.providerName(), ResolvedModel: model}, nil
}
