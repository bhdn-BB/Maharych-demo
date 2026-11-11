package config

import (
	"fmt"
	"os"
	"strings"

	"github.com/joho/godotenv"
)

type DB struct {
	Host     string
	Port     string
	User     string
	Password string
	Name     string
	URL      string
}

func (d DB) DSN() string {
	if d.URL != "" {
		return d.URL
	}
	return fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		d.Host, d.Port, d.User, d.Password, d.Name,
	)
}

type Config struct {
	JWTSecret         string
	CORSOrigins       []string
	DB                DB
	AIServiceGRPCAddr string
	AIServiceHTTPURL  string
	GoogleClientID    string
	// RabbitMQURL enables asynchronous interview finalization; empty disables it.
	RabbitMQURL string
	// AdminEmails lists emails that receive the admin role after Google sign-in.
	AdminEmails []string
}

// minJWTSecretLength is the shortest HS256 secret accepted at startup.
const minJWTSecretLength = 32

func Load() (*Config, error) {
	_ = godotenv.Load()

	requiredKeys := []string{
		"JWT_SECRET",
		"CORS_ORIGINS",
		"DB_HOST",
		"DB_PORT",
		"DB_USER",
		"DB_PASSWORD",
		"DB_NAME",
		"AI_SERVICE_GRPC_ADDR",
	}
	required := make(map[string]string, len(requiredKeys))

	var missing []string
	for _, key := range requiredKeys {
		v := os.Getenv(key)
		if v == "" {
			missing = append(missing, key)
		}
		required[key] = v
	}

	if len(missing) > 0 {
		return nil, fmt.Errorf("missing required environment variables: %v", missing)
	}

	if len(required["JWT_SECRET"]) < minJWTSecretLength {
		return nil, fmt.Errorf("JWT_SECRET must be at least %d characters", minJWTSecretLength)
	}

	var origins []string
	for _, o := range strings.Split(required["CORS_ORIGINS"], ",") {
		if trimmed := strings.TrimSpace(o); trimmed != "" {
			origins = append(origins, trimmed)
		}
	}

	return &Config{
		JWTSecret:   required["JWT_SECRET"],
		CORSOrigins: origins,
		DB: DB{
			Host:     required["DB_HOST"],
			Port:     required["DB_PORT"],
			User:     required["DB_USER"],
			Password: required["DB_PASSWORD"],
			Name:     required["DB_NAME"],
			URL:      os.Getenv("DATABASE_URL"),
		},
		AIServiceGRPCAddr: required["AI_SERVICE_GRPC_ADDR"],
		AIServiceHTTPURL:  envOrDefault("AI_SERVICE_HTTP_URL", "http://localhost:8000"),
		GoogleClientID:    os.Getenv("GOOGLE_CLIENT_ID"),
		RabbitMQURL:       os.Getenv("RABBITMQ_URL"),
		AdminEmails:       splitList(os.Getenv("ADMIN_EMAILS")),
	}, nil
}

func splitList(raw string) []string {
	var out []string
	for _, v := range strings.Split(raw, ",") {
		if trimmed := strings.ToLower(strings.TrimSpace(v)); trimmed != "" {
			out = append(out, trimmed)
		}
	}
	return out
}

func envOrDefault(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
