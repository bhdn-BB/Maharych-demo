package audio

import (
	"net/http/httptest"
	"testing"
)

func TestWebSocketOriginUsesConfiguredOrigins(t *testing.T) {
	handler := NewHandler(nil, nil, nil, []string{"http://localhost:3000"})
	request := httptest.NewRequest("GET", "/api/v1/interviews/id/audio", nil)
	request.Header.Set("Origin", "https://untrusted.example")
	if handler.upgrader.CheckOrigin(request) {
		t.Fatal("untrusted browser origin was accepted")
	}
	request.Header.Set("Origin", "http://localhost:3000")
	if !handler.upgrader.CheckOrigin(request) {
		t.Fatal("configured browser origin was rejected")
	}
}
