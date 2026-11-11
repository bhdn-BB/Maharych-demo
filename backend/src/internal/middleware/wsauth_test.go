package middleware

import (
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

func TestParseAuthUser(t *testing.T) {
	for _, tc := range []struct {
		name string
		sub  any
		want bool
	}{
		{"string subject", "42", true},
		{"numeric subject", 42, false},
		{"invalid subject", "no", false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{"sub": tc.sub, "email": "test@example.com", "exp": time.Now().Add(time.Hour).Unix()})
			signed, err := token.SignedString([]byte("secret"))
			if err != nil {
				t.Fatal(err)
			}
			user, err := ParseAuthUser(signed, "secret")
			if (err == nil) != tc.want {
				t.Fatalf("user=%+v err=%v", user, err)
			}
			if tc.want && (user.ID != 42 || user.Email != "test@example.com") {
				t.Fatalf("incorrect identity: %+v", user)
			}
		})
	}
}

func TestParseAuthUserRejectsUnsafeTokens(t *testing.T) {
	future := time.Now().Add(time.Hour).Unix()
	sign := func(method jwt.SigningMethod, claims jwt.MapClaims, key any) string {
		signed, err := jwt.NewWithClaims(method, claims).SignedString(key)
		if err != nil {
			t.Fatal(err)
		}
		return signed
	}
	for _, tc := range []struct {
		name  string
		token string
	}{
		{"missing exp", sign(jwt.SigningMethodHS256, jwt.MapClaims{"sub": "42"}, []byte("secret"))},
		{"expired", sign(jwt.SigningMethodHS256, jwt.MapClaims{"sub": "42", "exp": time.Now().Add(-time.Minute).Unix()}, []byte("secret"))},
		{"wrong secret", sign(jwt.SigningMethodHS256, jwt.MapClaims{"sub": "42", "exp": future}, []byte("other"))},
		{"other HMAC algorithm", sign(jwt.SigningMethodHS512, jwt.MapClaims{"sub": "42", "exp": future}, []byte("secret"))},
		{"alg none", sign(jwt.SigningMethodNone, jwt.MapClaims{"sub": "42", "exp": future}, jwt.UnsafeAllowNoneSignatureType)},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := ParseAuthUser(tc.token, "secret"); err == nil {
				t.Fatal("token must be rejected")
			}
		})
	}
}
