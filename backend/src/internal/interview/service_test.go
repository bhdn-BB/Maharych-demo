package interview

import (
	"context"
	"errors"
	"testing"

	"github.com/google/uuid"
	"maharych-api/src/internal/model"
	"maharych-api/src/internal/profile"

	"gorm.io/gorm"
)

type testRepository struct {
	created    int
	findErr    error
	listUser   uint
	listLimit  int
	listOffset int
	existing   *model.Interview
	saved      int
}

func (r *testRepository) Create(_ context.Context, _ *model.Interview) error {
	r.created++
	return nil
}
func (r *testRepository) FindByIDAndUser(_ context.Context, _ string, _ uint) (*model.Interview, error) {
	if r.findErr != nil {
		return nil, r.findErr
	}
	if r.existing != nil {
		return r.existing, nil
	}
	return nil, ErrNotFound
}
func (r *testRepository) FindByID(_ context.Context, _ string) (*model.Interview, error) {
	if r.findErr != nil {
		return nil, r.findErr
	}
	if r.existing != nil {
		return r.existing, nil
	}
	return nil, ErrNotFound
}
func (r *testRepository) Save(_ context.Context, _ *model.Interview) error {
	r.saved++
	return nil
}
func (r *testRepository) ListByUser(_ context.Context, userID uint, limit, offset int) ([]model.Interview, int64, error) {
	r.listUser, r.listLimit, r.listOffset = userID, limit, offset
	return []model.Interview{{UserID: userID}}, 1, nil
}

func TestListUsesOwnerAndPagination(t *testing.T) {
	repo := &testRepository{}
	service := NewService(repo, nil, nil, nil)
	items, total, err := service.List(context.Background(), 7, 2, 10)
	if err != nil || total != 1 || len(items) != 1 || repo.listUser != 7 || repo.listLimit != 10 || repo.listOffset != 10 {
		t.Fatalf("wrong list: items=%+v total=%d repo=%+v err=%v", items, total, repo, err)
	}
}

func TestSaveStreamTerminalUsesExistingStageMapping(t *testing.T) {
	for _, tc := range []struct{ stage, status string }{
		{"finished", "completed"},
		{"abandoned", "abandoned"},
	} {
		t.Run(tc.stage, func(t *testing.T) {
			item := &model.Interview{Status: "in_progress"}
			repo := &testRepository{existing: item}
			service := NewService(repo, nil, nil, nil)
			if err := service.SaveStreamTerminal(context.Background(), item, tc.stage); err != nil {
				t.Fatal(err)
			}
			if item.Status != tc.status || item.EndedAt == nil || repo.saved != 1 {
				t.Fatalf("terminal state = %+v, saves = %d", item, repo.saved)
			}
		})
	}
}

type testProfileReader struct{ exists bool }

func (r testProfileReader) Get(_ context.Context, userID uint) (*model.Profile, error) {
	if !r.exists {
		return nil, profile.ErrNotFound
	}
	return &model.Profile{UserID: userID}, nil
}

func TestGetPreservesStorageFailure(t *testing.T) {
	storageFailure := errors.New("database unavailable")
	service := NewService(&testRepository{findErr: storageFailure}, testProfileReader{}, testOptionReader{}, nil)
	_, err := service.Get(context.Background(), "id", 7)
	if !errors.Is(err, storageFailure) || errors.Is(err, ErrNotFound) {
		t.Fatalf("storage failure was misclassified: %v", err)
	}
}

type testOptionReader map[string]bool

func (r testOptionReader) FindByCategoryAndKey(_ context.Context, category, key string) (*model.InterviewOption, error) {
	if !r[category+":"+key] {
		return nil, gorm.ErrRecordNotFound
	}
	return &model.InterviewOption{Category: category, Key: key}, nil
}

func TestStartValidatesProfileAndOptionsBeforeSaving(t *testing.T) {
	repo := &testRepository{}
	options := testOptionReader{
		"level:middle": true, "position:backend": true, "focus:algorithms": true, "focus:behavioral": true,
	}
	missingProfile := NewService(repo, testProfileReader{}, options, nil)
	_, err := missingProfile.Start(context.Background(), 7, "middle", "backend", "algorithms", nil, "uk")
	if !errors.Is(err, ErrProfileRequired) || repo.created != 0 {
		t.Fatalf("expected missing profile without persistence, got %v and %d creates", err, repo.created)
	}

	service := NewService(repo, testProfileReader{exists: true}, options, nil)
	_, err = service.Start(context.Background(), 7, "middle", "unknown", "algorithms", nil, "uk")
	if !errors.Is(err, ErrInvalidOption) || repo.created != 0 {
		t.Fatalf("expected invalid option without persistence, got %v and %d creates", err, repo.created)
	}

	taskID := uuid.New()
	if _, err := service.Start(context.Background(), 7, "middle", "backend", "algorithms", &taskID, "uk"); !errors.Is(err, ErrInvalidOption) || repo.created != 0 {
		t.Fatalf("retired task-based interview was accepted: %v", err)
	}
	created, err := service.Start(context.Background(), 7, "middle", "backend", "algorithms", nil, "uk")
	if err != nil || created.UserID != 7 || repo.created != 1 || created.TaskID != nil || created.ScenarioVersion != 2 {
		t.Fatalf("valid interview was not saved: interview=%+v err=%v creates=%d", created, err, repo.created)
	}
	behavioral, err := service.Start(context.Background(), 7, "middle", "backend", "behavioral", nil, "uk")
	if err != nil || behavioral.Focus != "behavioral" {
		t.Fatalf("behavioral interview was not accepted: %+v, %v", behavioral, err)
	}
}

// queryOnlyRepository intentionally has no write methods.
type queryOnlyRepository struct{}

func (queryOnlyRepository) FindByIDAndUser(_ context.Context, _ string, userID uint) (*model.Interview, error) {
	return &model.Interview{UserID: userID}, nil
}

func (queryOnlyRepository) ListByUser(_ context.Context, userID uint, _, _ int) ([]model.Interview, int64, error) {
	return []model.Interview{{UserID: userID}}, 1, nil
}

func TestQueriesCanUseReadOnlyRepository(t *testing.T) {
	queries := &Queries{repo: queryOnlyRepository{}}
	item, err := queries.Get(context.Background(), "id", 7)
	if err != nil || item.UserID != 7 {
		t.Fatalf("get: item=%+v err=%v", item, err)
	}
	items, total, err := queries.List(context.Background(), 7, 1, 10)
	if err != nil || total != 1 || len(items) != 1 || items[0].UserID != 7 {
		t.Fatalf("list: items=%+v total=%d err=%v", items, total, err)
	}
}
