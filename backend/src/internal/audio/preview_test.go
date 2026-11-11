package audio

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestPreviewHandler(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/voices/daniel/preview" || r.URL.Query().Get("language") != "uk" {
			t.Errorf("unexpected upstream request: %s", r.URL)
		}
		w.Write([]byte("sample"))
	}))
	defer upstream.Close()
	router := gin.New()
	router.GET("/voices/:voice/preview", PreviewHandler(upstream.URL))
	for _, tc := range []struct {
		path   string
		status int
	}{
		{"/voices/daniel/preview?language=uk", http.StatusOK},
		{"/voices/unknown/preview?language=uk", http.StatusBadRequest},
		{"/voices/daniel/preview?language=fr", http.StatusBadRequest},
	} {
		t.Run(tc.path, func(t *testing.T) {
			response := httptest.NewRecorder()
			router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, tc.path, nil))
			if response.Code != tc.status {
				t.Fatalf("status = %d, want %d", response.Code, tc.status)
			}
			if tc.status == http.StatusOK && (response.Body.String() != "sample" || response.Header().Get("Content-Type") != "audio/mpeg") {
				t.Fatalf("unexpected audio response: %v %q", response.Header(), response.Body.String())
			}
		})
	}
}
