package profile

import (
	"context"
	"errors"
	"testing"

	"maharych-api/src/internal/model"

	"gorm.io/gorm"
)

type memoryRepository struct {
	profiles map[uint]*model.Profile
}

func (r *memoryRepository) FindByUserID(_ context.Context, userID uint) (*model.Profile, error) {
	profile, exists := r.profiles[userID]
	if !exists {
		return nil, gorm.ErrRecordNotFound
	}
	copy := *profile
	return &copy, nil
}

func (r *memoryRepository) Upsert(_ context.Context, profile *model.Profile) error {
	copy := *profile
	r.profiles[profile.UserID] = &copy
	return nil
}

func TestPutKeepsProfilesSeparateAndReplacesData(t *testing.T) {
	repo := &memoryRepository{profiles: make(map[uint]*model.Profile)}
	service := NewService(repo)
	years := 3
	req := PutRequest{
		Name: " Oksana ", Surname: " Shevchenko ", PhoneNumber: "+380501234567",
		YearsOfExperience: &years, TechStack: []string{" Go ", "go", "React"},
	}

	first, err := service.Put(context.Background(), 1, req)
	if err != nil {
		t.Fatal(err)
	}
	if first.UserID != 1 || first.Name != "Oksana" || len(first.TechStack) != 2 {
		t.Fatalf("unexpected normalized profile: %+v", first)
	}

	req.Name = "Olena"
	if _, err := service.Put(context.Background(), 2, req); err != nil {
		t.Fatal(err)
	}
	req.Name = "Iryna"
	if _, err := service.Put(context.Background(), 1, req); err != nil {
		t.Fatal(err)
	}
	if len(repo.profiles) != 2 || repo.profiles[1].Name != "Iryna" || repo.profiles[2].Name != "Olena" {
		t.Fatalf("upsert did not preserve one profile per user: %+v", repo.profiles)
	}
}

func TestGetMissingProfile(t *testing.T) {
	service := NewService(&memoryRepository{profiles: make(map[uint]*model.Profile)})
	_, err := service.Get(context.Background(), 17)
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}
}

func TestPutRejectsIncompleteProfile(t *testing.T) {
	service := NewService(&memoryRepository{profiles: make(map[uint]*model.Profile)})
	years := 0
	_, err := service.Put(context.Background(), 1, PutRequest{
		Name: "A", Surname: "Candidate", PhoneNumber: "+380501234567",
		YearsOfExperience: &years,
	})
	if !errors.Is(err, ErrInvalid) {
		t.Fatalf("expected ErrInvalid, got %v", err)
	}
}
