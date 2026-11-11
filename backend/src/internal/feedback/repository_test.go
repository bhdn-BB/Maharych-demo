package feedback

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHTTPRepositoryReadsReport(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/interview/by-interview-id/interview-1/feedback" {
			t.Errorf("wrong report path: %s", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"overall_score":8,"recommendation":"consider","summary":"Good","topic_scores":[],"top_strengths":[],"top_weaknesses":[]}`))
	}))
	defer server.Close()

	report, err := NewHTTPRepository(server.URL).GetByInterviewID(context.Background(), "interview-1")
	if err != nil || report.OverallScore != 8 || report.Recommendation != "consider" {
		t.Fatalf("wrong report: %+v, %v", report, err)
	}
}

func TestHTTPRepositoryHandlesMissingReport(t *testing.T) {
	server := httptest.NewServer(http.NotFoundHandler())
	defer server.Close()
	_, err := NewHTTPRepository(server.URL).GetByInterviewID(context.Background(), "interview-1")
	if !errors.Is(err, ErrNotReady) {
		t.Fatalf("expected unavailable feedback, got %v", err)
	}
}
