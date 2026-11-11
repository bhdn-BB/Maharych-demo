package auth

import (
	"bytes"
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestValidatePassword(t *testing.T) {
	cases := []struct {
		name     string
		password string
		valid    bool
	}{
		{"policy compliant", "Secret-Password1", true},
		{"exactly eight runes", "Abcdefg1", true},
		{"cyrillic upper-case counts", "Пароль2026", true},
		{"exactly 72 bytes", "A1" + strings.Repeat("x", 70), true},
		{"empty", "", false},
		{"single digit (accepted before the fix)", "1", false},
		{"seven runes", "Abcdef1", false},
		{"no upper-case letter", "lowercase-only-1", false},
		{"no digit", "NoDigitsHere", false},
		{"73 bytes would crash bcrypt", "A1" + strings.Repeat("x", 71), false},
		{"multibyte input over 72 bytes", "A1" + strings.Repeat("ї", 36), false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := ValidatePassword(tc.password)
			if tc.valid && err != nil {
				t.Fatalf("expected valid, got %v", err)
			}
			if !tc.valid && !errors.Is(err, ErrWeakPassword) {
				t.Fatalf("expected ErrWeakPassword, got %v", err)
			}
		})
	}
}

func TestRegisterRejectsWeakPasswordBeforeTouchingStorage(t *testing.T) {
	users := &memoryUsers{}
	svc := NewService(users, "secret", "")
	if _, _, err := svc.Register(context.Background(), "weak@example.com", "1"); !errors.Is(err, ErrWeakPassword) {
		t.Fatalf("expected ErrWeakPassword, got %v", err)
	}
	if found, _ := users.FindByEmail(context.Background(), "weak@example.com"); found != nil {
		t.Fatal("a rejected registration must not create a user")
	}
}

func TestLoginStillAcceptsLegacyWeakPasswords(t *testing.T) {
	users := &memoryUsers{}
	svc := NewService(users, "secret", "")
	if _, _, err := svc.Register(context.Background(), "legacy@example.com", "Legacy-Pass1"); err != nil {
		t.Fatal(err)
	}
	// Simulate an account created before the policy existed.
	user, _ := users.FindByEmail(context.Background(), "legacy@example.com")
	if err := user.SetPassword("1"); err != nil {
		t.Fatal(err)
	}
	if _, _, err := svc.Login(context.Background(), "legacy@example.com", "1"); err != nil {
		t.Fatalf("existing accounts must keep signing in: %v", err)
	}
}

func TestRegisterHTTPMapsPolicyViolationsTo400(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.POST("/register", NewHandler(NewService(&memoryUsers{}, "secret", "")).Register)
	for name, password := range map[string]string{
		"too weak": "1",
		"too long": "A1" + strings.Repeat("x", 80),
	} {
		t.Run(name, func(t *testing.T) {
			body := `{"email":"user@example.com","password":"` + password + `"}`
			req := httptest.NewRequest(http.MethodPost, "/register", bytes.NewBufferString(body))
			req.Header.Set("Content-Type", "application/json")
			rec := httptest.NewRecorder()
			router.ServeHTTP(rec, req)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("expected 400, got %d %s", rec.Code, rec.Body.String())
			}
			if strings.Contains(rec.Body.String(), password) {
				t.Fatal("the response must not echo the password")
			}
		})
	}
}
