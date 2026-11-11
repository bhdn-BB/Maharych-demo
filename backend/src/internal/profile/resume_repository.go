package profile

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// ResumeRepository communicates with the private document extraction service.
type ResumeRepository struct {
	baseURL string
	client  *http.Client
}

func NewResumeRepository(baseURL string) *ResumeRepository {
	return &ResumeRepository{baseURL: strings.TrimRight(baseURL, "/"), client: &http.Client{Timeout: 30 * time.Second}}
}

func (r *ResumeRepository) Parse(ctx context.Context, kind string, data []byte) (int, []byte, error) {
	target := r.baseURL + "/api/v1/resume/parse?kind=" + url.QueryEscape(kind)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, target, bytes.NewReader(data))
	if err != nil {
		return 0, nil, fmt.Errorf("construct resume request: %w", err)
	}
	req.Header.Set("Content-Type", "application/octet-stream")
	resp, err := r.client.Do(req)
	if err != nil {
		return 0, nil, fmt.Errorf("request resume extraction: %w", err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 256*1024))
	if err != nil {
		return 0, nil, fmt.Errorf("read resume extraction response: %w", err)
	}
	return resp.StatusCode, body, nil
}
