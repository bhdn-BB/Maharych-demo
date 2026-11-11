package interview

import (
	"context"
	"errors"

	"maharych-api/src/internal/model"
)

// Interview lifecycle statuses stored in interviews.status.
const (
	StatusInProgress = "in_progress"
	StatusFinalizing = "finalizing"
	StatusCompleted  = "completed"
	StatusAbandoned  = "abandoned"
)

var (
	ErrNotFound        = errors.New("interview not found")
	ErrNotInProgress   = errors.New("interview is not in progress")
	ErrProfileRequired = errors.New("candidate profile required")
	ErrInvalidOption   = errors.New("invalid interview option")
	// ErrFinalizerUnavailable means finalization cannot be requested (no broker configured).
	ErrFinalizerUnavailable = errors.New("interview finalization is unavailable")
)

type profileReader interface {
	Get(ctx context.Context, userID uint) (*model.Profile, error)
}

type optionReader interface {
	FindByCategoryAndKey(ctx context.Context, category, key string) (*model.InterviewOption, error)
}

// Service exposes the existing interview API while separating commands from queries.
type Service struct {
	*Commands
	*Queries
}

// Commands owns operations that change interview state.
type Commands struct {
	repo     CommandRepository
	profiles profileReader
	options  optionReader
	finisher Finisher
}

// Queries owns read-only interview operations.
type Queries struct {
	repo QueryRepository
}

// NewService wires the interview domain. The finisher may be nil only when finalization is
// intentionally unavailable; End then fails explicitly instead of completing without the AI.
func NewService(repo Repository, profiles profileReader, options optionReader, finisher Finisher) *Service {
	return &Service{
		Commands: &Commands{repo: repo, profiles: profiles, options: options, finisher: finisher},
		Queries:  &Queries{repo: repo},
	}
}
