package auth

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"maharych-api/src/internal/model"

	"github.com/golang-jwt/jwt/v5"
	"google.golang.org/api/idtoken"
)

var (
	ErrEmailAlreadyRegistered = errors.New("email already registered")
	ErrInvalidCredentials     = errors.New("invalid credentials")
	ErrInvalidGoogleToken     = errors.New("invalid google token")
	ErrInvalidTokenClaims     = errors.New("invalid token claims")
	ErrEmailNotVerified       = errors.New("email not verified")
	ErrGoogleDisabled         = errors.New("Google sign-in is not configured")
)

type Service struct {
	repo           UserRepository
	jwtSecret      string
	googleClientID string
	adminEmails    map[string]struct{}
}

func NewService(repo UserRepository, jwtSecret, googleClientID string) *Service {
	return &Service{
		repo:           repo,
		jwtSecret:      jwtSecret,
		googleClientID: googleClientID,
	}
}

// WithAdminEmails sets the allowlist of emails that may hold the admin role.
// Admin is granted only to accounts linked to a verified Google identity, so an
// attacker cannot claim an admin address by registering it with a password.
func (s *Service) WithAdminEmails(emails []string) *Service {
	s.adminEmails = make(map[string]struct{}, len(emails))
	for _, e := range emails {
		if e = strings.ToLower(strings.TrimSpace(e)); e != "" {
			s.adminEmails[e] = struct{}{}
		}
	}
	return s
}

func (s *Service) isAdminEmail(email string) bool {
	_, ok := s.adminEmails[strings.ToLower(email)]
	return ok
}

// syncRole aligns the persisted role with the allowlist (granting and revoking).
func (s *Service) syncRole(ctx context.Context, user *model.User) error {
	want := model.RoleUser
	if user.GoogleSub != nil && s.isAdminEmail(user.Email) {
		want = model.RoleAdmin
	}
	if user.Role == want {
		return nil
	}
	user.Role = want
	if err := s.repo.Save(ctx, user); err != nil {
		return fmt.Errorf("failed to update role: %w", err)
	}
	return nil
}

func (s *Service) Register(ctx context.Context, email, password string) (*model.User, string, error) {
	email = strings.ToLower(email)
	if err := ValidatePassword(password); err != nil {
		return nil, "", err
	}

	if existing, _ := s.repo.FindByEmail(ctx, email); existing != nil {
		return nil, "", ErrEmailAlreadyRegistered
	}
	if s.isAdminEmail(email) {
		// Admin addresses must sign in with Google; password sign-up is not verified.
		return nil, "", ErrEmailAlreadyRegistered
	}

	user := model.User{Email: email, Role: model.RoleUser}
	if err := user.SetPassword(password); err != nil {
		return nil, "", fmt.Errorf("failed to hash password: %w", err)
	}

	if err := s.repo.Create(ctx, &user); err != nil {
		return nil, "", fmt.Errorf("failed to create user: %w", err)
	}

	token, err := s.generateJWT(&user)
	if err != nil {
		return nil, "", fmt.Errorf("failed to generate token: %w", err)
	}

	return &user, token, nil
}

func (s *Service) Login(ctx context.Context, email, password string) (*model.User, string, error) {
	email = strings.ToLower(email)

	user, err := s.repo.FindByEmail(ctx, email)
	if err != nil {
		return nil, "", ErrInvalidCredentials
	}

	if !user.CheckPassword(password) {
		return nil, "", ErrInvalidCredentials
	}

	if err := s.syncRole(ctx, user); err != nil {
		return nil, "", err
	}

	token, err := s.generateJWT(user)
	if err != nil {
		return nil, "", fmt.Errorf("failed to generate token: %w", err)
	}

	return user, token, nil
}

func (s *Service) GoogleAuth(ctx context.Context, idTokenStr string) (*model.User, string, error) {
	if s.googleClientID == "" {
		return nil, "", ErrGoogleDisabled
	}
	payload, err := idtoken.Validate(ctx, idTokenStr, s.googleClientID)
	if err != nil {
		return nil, "", ErrInvalidGoogleToken
	}

	googleSub, _ := payload.Claims["sub"].(string)
	email, _ := payload.Claims["email"].(string)
	emailVerified, _ := payload.Claims["email_verified"].(bool)

	if googleSub == "" || email == "" {
		return nil, "", ErrInvalidTokenClaims
	}

	if !emailVerified {
		return nil, "", ErrEmailNotVerified
	}

	email = strings.ToLower(email)

	// Try to find user by Google subject ID
	if user, err := s.repo.FindByGoogleSub(ctx, googleSub); err == nil {
		if err := s.syncRole(ctx, user); err != nil {
			return nil, "", err
		}
		token, err := s.generateJWT(user)
		if err != nil {
			return nil, "", fmt.Errorf("failed to generate token: %w", err)
		}
		return user, token, nil
	}

	// Try to find existing user by email (account linking)
	if user, err := s.repo.FindByEmail(ctx, email); err == nil {
		user.GoogleSub = &googleSub
		if s.isAdminEmail(email) {
			// Drop any password set before the Google identity was linked.
			user.Password = ""
		}
		if err := s.repo.Save(ctx, user); err != nil {
			return nil, "", fmt.Errorf("failed to link google account: %w", err)
		}
		if err := s.syncRole(ctx, user); err != nil {
			return nil, "", err
		}

		token, err := s.generateJWT(user)
		if err != nil {
			return nil, "", fmt.Errorf("failed to generate token: %w", err)
		}
		return user, token, nil
	}

	// Create new user
	user := &model.User{
		Email:        email,
		AuthProvider: "google",
		GoogleSub:    &googleSub,
		Role:         model.RoleUser,
	}
	if s.isAdminEmail(email) {
		user.Role = model.RoleAdmin
	}
	if err := s.repo.Create(ctx, user); err != nil {
		return nil, "", fmt.Errorf("failed to create user: %w", err)
	}

	token, err := s.generateJWT(user)
	if err != nil {
		return nil, "", fmt.Errorf("failed to generate token: %w", err)
	}

	return user, token, nil
}

func (s *Service) generateJWT(user *model.User) (string, error) {
	role := user.Role
	if role == "" {
		role = model.RoleUser
	}
	claims := jwt.MapClaims{
		"sub":   fmt.Sprintf("%d", user.ID),
		"email": user.Email,
		"role":  role,
		"exp":   time.Now().Add(24 * time.Hour).Unix(),
		"iat":   time.Now().Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(s.jwtSecret))
}
