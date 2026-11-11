package profile

import (
	"context"
	"errors"
	"fmt"
	"net/url"
	"strings"
	"unicode/utf8"

	"maharych-api/src/internal/model"

	"gorm.io/gorm"
)

var (
	ErrNotFound = errors.New("profile not found")
	ErrInvalid  = errors.New("invalid profile")
)

type Service struct {
	repo Repository
}

func NewService(repo Repository) *Service {
	return &Service{repo: repo}
}

func (s *Service) Get(ctx context.Context, userID uint) (*model.Profile, error) {
	profile, err := s.repo.FindByUserID(ctx, userID)
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("find profile: %w", err)
	}
	return profile, nil
}

func (s *Service) Put(ctx context.Context, userID uint, req PutRequest) (*model.Profile, error) {
	profile, err := makeProfile(userID, req)
	if err != nil {
		return nil, err
	}
	if err := s.repo.Upsert(ctx, profile); err != nil {
		return nil, fmt.Errorf("save profile: %w", err)
	}
	return s.Get(ctx, userID)
}

func makeProfile(userID uint, req PutRequest) (*model.Profile, error) {
	name := strings.TrimSpace(req.Name)
	surname := strings.TrimSpace(req.Surname)
	phone := strings.TrimSpace(req.PhoneNumber)
	resume := strings.TrimSpace(req.Resume)
	linkedIn := strings.TrimSpace(req.LinkedInURL)
	gitHub := strings.TrimSpace(req.GitHubURL)

	if !withinRunes(name, 2, 50) || !withinRunes(surname, 2, 50) ||
		!withinRunes(phone, 10, 20) || req.YearsOfExperience == nil ||
		*req.YearsOfExperience < 0 || *req.YearsOfExperience > 50 ||
		utf8.RuneCountInString(resume) > 10000 ||
		!validHTTPURL(linkedIn) || !validHTTPURL(gitHub) {
		return nil, ErrInvalid
	}

	stack := make([]string, 0, len(req.TechStack))
	seen := make(map[string]struct{}, len(req.TechStack))
	if len(req.TechStack) > 30 {
		return nil, ErrInvalid
	}
	for _, item := range req.TechStack {
		item = strings.TrimSpace(item)
		if !withinRunes(item, 1, 50) {
			return nil, ErrInvalid
		}
		key := strings.ToLower(item)
		if _, exists := seen[key]; !exists {
			stack = append(stack, item)
			seen[key] = struct{}{}
		}
	}

	return &model.Profile{
		UserID:            userID,
		Name:              name,
		Surname:           surname,
		PhoneNumber:       phone,
		LinkedInURL:       linkedIn,
		GitHubURL:         gitHub,
		YearsOfExperience: *req.YearsOfExperience,
		TechStack:         stack,
		Resume:            resume,
	}, nil
}

func withinRunes(value string, min, max int) bool {
	count := utf8.RuneCountInString(value)
	return count >= min && count <= max
}

func validHTTPURL(value string) bool {
	if value == "" {
		return true
	}
	if utf8.RuneCountInString(value) > 500 {
		return false
	}
	parsed, err := url.Parse(value)
	return err == nil && (parsed.Scheme == "https" || parsed.Scheme == "http") && parsed.Host != ""
}
