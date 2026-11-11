package auth

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"maharych-api/src/internal/middleware"

	"github.com/gin-gonic/gin"
)

// Exercise the public HTTP contract and consume issued tokens with the API's
// actual middleware, without an auth proxy or external authentication process.
func TestDirectAuthHTTPContract(t *testing.T) {
	gin.SetMode(gin.TestMode)
	handler := NewHandler(NewService(&memoryUsers{}, "test-api-secret", ""))
	router := gin.New()
	router.POST("/api/v1/auth/register", handler.Register)
	router.POST("/api/v1/auth/login", handler.Login)
	router.POST("/api/v1/auth/google", handler.GoogleAuth)
	router.GET("/api/v1/me", middleware.AuthRequired("test-api-secret"), func(c *gin.Context) {
		user := middleware.CurrentUser(c)
		c.JSON(http.StatusOK, UserResponse{ID: user.ID, Email: user.Email, Role: user.Role})
	})

	request := func(method, path, body, token string) *httptest.ResponseRecorder {
		t.Helper()
		req := httptest.NewRequest(method, path, bytes.NewBufferString(body))
		req.Header.Set("Content-Type", "application/json")
		if token != "" {
			req.Header.Set("Authorization", "Bearer "+token)
		}
		response := httptest.NewRecorder()
		router.ServeHTTP(response, req)
		return response
	}

	registered := request(http.MethodPost, "/api/v1/auth/register", `{"email":"Candidate@Example.com","password":"Test-Password1"}`, "")
	if registered.Code != http.StatusCreated {
		t.Fatalf("register: %d %s", registered.Code, registered.Body.String())
	}
	var result AuthResponse
	if err := json.Unmarshal(registered.Body.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result.User.ID != 1 || result.User.Email != "candidate@example.com" || result.Token == "" {
		t.Fatal("registration response changed")
	}
	var payload map[string]json.RawMessage
	if err := json.Unmarshal(registered.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	var userFields map[string]json.RawMessage
	if err := json.Unmarshal(payload["user"], &userFields); err != nil {
		t.Fatal(err)
	}
	// The role is part of the contract since the admin area was added (the UI gates /admin on it).
	if len(payload) != 2 || len(userFields) != 3 || userFields["id"] == nil || userFields["email"] == nil ||
		string(userFields["role"]) != `"user"` {
		t.Fatal("auth response must expose only user ID/email/role and the API token")
	}
	response := request(http.MethodGet, "/api/v1/me", "", result.Token)
	if response.Code != http.StatusOK {
		t.Fatalf("API rejected issued token: %d", response.Code)
	}
	var identity UserResponse
	if err := json.Unmarshal(response.Body.Bytes(), &identity); err != nil {
		t.Fatal(err)
	}
	if identity != result.User {
		t.Fatal("API identity differs from registered identity")
	}

	for _, test := range []struct {
		name, path, body string
		status           int
	}{
		{"duplicate email", "/api/v1/auth/register", `{"email":"candidate@example.com","password":"Test-Password1"}`, http.StatusConflict},
		{"invalid email", "/api/v1/auth/register", `{"email":"invalid","password":"Test-Password1"}`, http.StatusBadRequest},
		{"wrong password", "/api/v1/auth/login", `{"email":"candidate@example.com","password":"wrong"}`, http.StatusUnauthorized},
		{"missing Google token", "/api/v1/auth/google", `{}`, http.StatusBadRequest},
		{"Google not configured", "/api/v1/auth/google", `{"id_token":"synthetic-token"}`, http.StatusServiceUnavailable},
	} {
		t.Run(test.name, func(t *testing.T) {
			response := request(http.MethodPost, test.path, test.body, "")
			if response.Code != test.status {
				t.Fatalf("got %d, want %d: %s", response.Code, test.status, response.Body.String())
			}
		})
	}

	loggedIn := request(http.MethodPost, "/api/v1/auth/login", `{"email":"CANDIDATE@EXAMPLE.COM","password":"Test-Password1"}`, "")
	if loggedIn.Code != http.StatusOK {
		t.Fatalf("login: %d", loggedIn.Code)
	}
	var login AuthResponse
	if err := json.Unmarshal(loggedIn.Body.Bytes(), &login); err != nil {
		t.Fatal(err)
	}
	if login.User != result.User || request(http.MethodGet, "/api/v1/me", "", login.Token).Code != http.StatusOK {
		t.Fatal("login response or JWT compatibility changed")
	}
	if request(http.MethodGet, "/api/v1/me", "", "").Code != http.StatusUnauthorized {
		t.Fatal("API must reject anonymous requests")
	}
}
