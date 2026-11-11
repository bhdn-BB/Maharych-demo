package config

import (
	"strings"
	"testing"
)

func setRequiredEnv(t *testing.T, secret string) {
	t.Helper()
	for key, value := range map[string]string{
		"JWT_SECRET": secret, "CORS_ORIGINS": "http://localhost:3000", "DB_HOST": "h", "DB_PORT": "5432",
		"DB_USER": "u", "DB_PASSWORD": "p", "DB_NAME": "n", "AI_SERVICE_GRPC_ADDR": "ai:50051",
	} {
		t.Setenv(key, value)
	}
}

func TestLoadRejectsShortJWTSecret(t *testing.T) {
	setRequiredEnv(t, "short")
	if _, err := Load(); err == nil || !strings.Contains(err.Error(), "JWT_SECRET") {
		t.Fatalf("expected JWT_SECRET length error, got %v", err)
	}
}

func TestLoadAcceptsLongJWTSecret(t *testing.T) {
	setRequiredEnv(t, strings.Repeat("s", minJWTSecretLength))
	if _, err := Load(); err != nil {
		t.Fatal(err)
	}
}
