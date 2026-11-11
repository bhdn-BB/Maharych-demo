package profile

import (
	"bytes"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"maharych-api/src/internal/middleware"
)

func TestResumeHandlerForwardsOnlySupportedBoundedFiles(t *testing.T) {
	gin.SetMode(gin.TestMode)
	calls := 0
	service := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		if r.URL.Path != "/api/v1/resume/parse" || r.URL.Query().Get("kind") != "pdf" {
			t.Errorf("unexpected parser route: %s", r.URL.String())
		}
		data, _ := io.ReadAll(r.Body)
		if string(data) != "%PDF-example" {
			t.Errorf("file changed during forwarding")
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"text":"resume"}`))
	}))
	defer service.Close()
	router := gin.New()
	router.POST("/resume", NewResumeHandler(NewResumeService(NewResumeRepository(service.URL))).Parse)
	for _, tc := range []struct {
		name, kind string
		body       []byte
		want       int
	}{
		{"pdf", "pdf", []byte("%PDF-example"), http.StatusOK},
		{"unsupported", "txt", []byte("text"), http.StatusBadRequest},
		{"empty", "pdf", nil, http.StatusBadRequest},
		{"oversized", "pdf", make([]byte, maxResumeBytes+1), http.StatusBadRequest},
	} {
		t.Run(tc.name, func(t *testing.T) {
			response := httptest.NewRecorder()
			router.ServeHTTP(response, httptest.NewRequest(http.MethodPost, "/resume?kind="+tc.kind, bytes.NewReader(tc.body)))
			if response.Code != tc.want {
				t.Fatalf("got %d, want %d", response.Code, tc.want)
			}
		})
	}
	if calls != 1 {
		t.Fatalf("parser called %d times; want 1", calls)
	}
}

func TestResumeHandlerRequiresAuthentication(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	protected := router.Group("/api", middleware.AuthRequired("test-secret"))
	protected.POST("/profile/resume/parse", NewResumeHandler(NewResumeService(NewResumeRepository("http://127.0.0.1:1"))).Parse)
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodPost, "/api/profile/resume/parse?kind=pdf", bytes.NewReader([]byte("%PDF-example"))))
	if response.Code != http.StatusUnauthorized {
		t.Fatalf("unauthenticated upload returned %d", response.Code)
	}
}
