package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
)

const adminTestSecret = "0123456789abcdef0123456789abcdef"

func adminToken(t *testing.T, role string) string {
	t.Helper()
	claims := jwt.MapClaims{"sub": "7", "email": "a@b.c", "exp": time.Now().Add(time.Hour).Unix()}
	if role != "" {
		claims["role"] = role
	}
	s, err := jwt.NewWithClaims(jwt.SigningMethodHS256, claims).SignedString([]byte(adminTestSecret))
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func TestRequireAdmin(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/x", AuthRequired(adminTestSecret), RequireAdmin(), func(c *gin.Context) { c.Status(http.StatusOK) })

	cases := []struct {
		name, header string
		want         int
	}{
		{"no token", "", http.StatusUnauthorized},
		{"user role", "Bearer " + adminToken(t, "user"), http.StatusForbidden},
		{"missing role", "Bearer " + adminToken(t, ""), http.StatusForbidden},
		{"admin role", "Bearer " + adminToken(t, "admin"), http.StatusOK},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, "/x", nil)
			if tc.header != "" {
				req.Header.Set("Authorization", tc.header)
			}
			w := httptest.NewRecorder()
			r.ServeHTTP(w, req)
			if w.Code != tc.want {
				t.Fatalf("got %d, want %d", w.Code, tc.want)
			}
		})
	}
}
