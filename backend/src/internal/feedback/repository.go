package feedback

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

var ErrNotReady = errors.New("feedback not available")

type Report struct {
	ScoreScale     int              `json:"score_scale"`
	Partial        bool             `json:"partial"`
	Language       string           `json:"language"`
	Questions      []QuestionAnswer `json:"questions"`
	OverallScore   float64          `json:"overall_score"`
	Recommendation string           `json:"recommendation"`
	Summary        string           `json:"summary"`
	TopicScores    []TopicScore     `json:"topic_scores"`
	TopStrengths   []string         `json:"top_strengths"`
	TopWeaknesses  []string         `json:"top_weaknesses"`
}

type QuestionAnswer struct {
	QuestionID    string `json:"question_id"`
	TopicIndex    int    `json:"topic_index"`
	Question      string `json:"question"`
	Answer        string `json:"answer"`
	Score         int    `json:"score"`
	Comment       string `json:"comment"`
	Clarification bool   `json:"clarification"`
}

type TopicScore struct {
	TopicIndex   int      `json:"topic_index"`
	Score        int      `json:"score"`
	QuestionType string   `json:"question_type"`
	Comment      string   `json:"comment"`
	Strengths    []string `json:"strengths"`
	Weaknesses   []string `json:"weaknesses"`
}

type Repository interface {
	GetByInterviewID(ctx context.Context, interviewID string) (*Report, error)
}

type PDFRepository interface {
	GetPDFByInterviewID(ctx context.Context, interviewID string) ([]byte, error)
}

type HTTPRepository struct {
	baseURL string
	client  *http.Client
}

func NewHTTPRepository(baseURL string) *HTTPRepository {
	return &HTTPRepository{
		baseURL: strings.TrimRight(baseURL, "/"),
		client:  &http.Client{Timeout: 5 * time.Second},
	}
}

func (r *HTTPRepository) GetByInterviewID(ctx context.Context, interviewID string) (*Report, error) {
	endpoint := r.baseURL + "/api/v1/interview/by-interview-id/" + url.PathEscape(interviewID) + "/feedback"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, fmt.Errorf("create feedback request: %w", err)
	}
	resp, err := r.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetch feedback: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusNotFound {
		return nil, ErrNotReady
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("feedback service returned status %d", resp.StatusCode)
	}
	var report Report
	if err := json.NewDecoder(http.MaxBytesReader(nil, resp.Body, 1<<20)).Decode(&report); err != nil {
		return nil, fmt.Errorf("decode feedback: %w", err)
	}
	return &report, nil
}

func (r *HTTPRepository) GetPDFByInterviewID(ctx context.Context, interviewID string) ([]byte, error) {
	endpoint := r.baseURL + "/api/v1/interview/by-interview-id/" + url.PathEscape(interviewID) + "/report.pdf"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, fmt.Errorf("create PDF request: %w", err)
	}
	resp, err := r.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetch PDF report: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusNotFound {
		return nil, ErrNotReady
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("PDF service returned status %d", resp.StatusCode)
	}
	pdf, err := io.ReadAll(io.LimitReader(resp.Body, (5<<20)+1))
	if err != nil {
		return nil, fmt.Errorf("read PDF report: %w", err)
	}
	if len(pdf) < 5 || len(pdf) > 5<<20 || string(pdf[:5]) != "%PDF-" {
		return nil, errors.New("invalid PDF report")
	}
	return pdf, nil
}
