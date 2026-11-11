package auth

import (
	"context"
	"errors"
	"github.com/golang-jwt/jwt/v5"
	"gorm.io/gorm"
	"maharych-api/src/internal/model"
	"testing"
)

type memoryUsers struct{ users []*model.User }

func (r *memoryUsers) FindByID(_ context.Context, id uint) (*model.User, error) {
	for _, u := range r.users {
		if u.ID == id {
			return u, nil
		}
	}
	return nil, gorm.ErrRecordNotFound
}
func (r *memoryUsers) FindByEmail(_ context.Context, email string) (*model.User, error) {
	for _, u := range r.users {
		if u.Email == email {
			return u, nil
		}
	}
	return nil, gorm.ErrRecordNotFound
}
func (r *memoryUsers) FindByGoogleSub(_ context.Context, sub string) (*model.User, error) {
	for _, u := range r.users {
		if u.GoogleSub != nil && *u.GoogleSub == sub {
			return u, nil
		}
	}
	return nil, gorm.ErrRecordNotFound
}
func (r *memoryUsers) Create(_ context.Context, u *model.User) error {
	u.ID = uint(len(r.users) + 1)
	r.users = append(r.users, u)
	return nil
}
func (r *memoryUsers) Save(context.Context, *model.User) error { return nil }

func TestCredentialsAndJWTContract(t *testing.T) {
	svc := NewService(&memoryUsers{}, "shared-secret", "")
	ctx := context.Background()
	user, tokenString, err := svc.Register(ctx, "Candidate@Example.com", "Secret-Password1")
	if err != nil {
		t.Fatal(err)
	}
	if user.GoogleSub != nil {
		t.Fatal("password-only accounts must not share an empty unique Google subject")
	}
	if user.Email != "candidate@example.com" || user.Password == "Secret-Password1" || !user.CheckPassword("Secret-Password1") {
		t.Fatal("email normalization or password hashing failed")
	}
	token, err := jwt.Parse(tokenString, func(*jwt.Token) (any, error) { return []byte("shared-secret"), nil }, jwt.WithValidMethods([]string{"HS256"}), jwt.WithExpirationRequired())
	if err != nil || !token.Valid {
		t.Fatalf("invalid issued JWT: %v", err)
	}
	claims := token.Claims.(jwt.MapClaims)
	if claims["sub"] != "1" || claims["email"] != user.Email {
		t.Fatalf("JWT contract changed: %v", claims)
	}
	if _, _, err := svc.Register(ctx, user.Email, "Another-Password2"); !errors.Is(err, ErrEmailAlreadyRegistered) {
		t.Fatalf("duplicate registration: %v", err)
	}
	if _, _, err := svc.Login(ctx, user.Email, "wrong"); !errors.Is(err, ErrInvalidCredentials) {
		t.Fatalf("wrong password: %v", err)
	}
	if _, _, err := svc.Login(ctx, "CANDIDATE@EXAMPLE.COM", "Secret-Password1"); err != nil {
		t.Fatal(err)
	}
}

func TestGoogleRequiresConfiguredAudience(t *testing.T) {
	svc := NewService(&memoryUsers{}, "shared-secret", "")
	if _, _, err := svc.GoogleAuth(context.Background(), "untrusted-token"); !errors.Is(err, ErrGoogleDisabled) {
		t.Fatalf("expected disabled Google authentication: %v", err)
	}
}
