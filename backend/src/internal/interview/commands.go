package interview

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"maharych-api/src/internal/broker"
	"maharych-api/src/internal/model"
	"maharych-api/src/internal/profile"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

func (s *Commands) Start(ctx context.Context, userID uint, level, position, focus string, taskID *uuid.UUID, language string, voiceIDs ...string) (*model.Interview, error) {
	voiceID := ""
	if len(voiceIDs) > 0 {
		voiceID = voiceIDs[0]
	}
	switch voiceID {
	case "", "anna", "sophia", "daniel", "alex":
	default:
		return nil, ErrInvalidOption
	}
	lang := "uk"
	if language != "" {
		lang = language
	}
	if lang != "uk" && lang != "en" {
		return nil, ErrInvalidOption
	}
	if taskID != nil || !model.IsSupportedInterviewFocus(focus) {
		return nil, ErrInvalidOption
	}
	if _, err := s.profiles.Get(ctx, userID); errors.Is(err, profile.ErrNotFound) {
		return nil, ErrProfileRequired
	} else if err != nil {
		return nil, fmt.Errorf("load candidate profile: %w", err)
	}

	for _, selected := range []struct{ category, key string }{
		{"level", level}, {"position", position}, {"focus", focus},
	} {
		if _, err := s.options.FindByCategoryAndKey(ctx, selected.category, selected.key); errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrInvalidOption
		} else if err != nil {
			return nil, fmt.Errorf("load interview option: %w", err)
		}
	}
	interview := model.Interview{
		VoiceID:         voiceID,
		UserID:          userID,
		Level:           level,
		Position:        position,
		Focus:           focus,
		Language:        lang,
		Status:          StatusInProgress,
		StartedAt:       time.Now(),
		ScenarioVersion: 2,
	}

	if err := s.repo.Create(ctx, &interview); err != nil {
		return nil, fmt.Errorf("failed to create interview: %w", err)
	}

	return &interview, nil
}

// End requests asynchronous finalization. A fresh request moves the interview to
// "finalizing" and enqueues the work; the terminal status is stored later by HandleFinished.
// Repeating End while finalizing re-enqueues the (idempotent) request, which recovers from a lost event.
func (s *Commands) End(ctx context.Context, id string, userID uint) (*model.Interview, error) {
	interview, err := s.repo.FindByIDAndUser(ctx, id, userID)
	if errors.Is(err, ErrNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("find interview: %w", err)
	}

	switch interview.Status {
	case StatusCompleted, StatusAbandoned:
		return interview, nil
	case StatusInProgress, StatusFinalizing:
	default:
		return nil, ErrNotInProgress
	}
	if s.finisher == nil {
		return nil, ErrFinalizerUnavailable
	}

	previous := interview.Status
	if previous == StatusInProgress {
		interview.Status = StatusFinalizing
		if err := s.repo.Save(ctx, interview); err != nil {
			interview.Status = previous
			return nil, fmt.Errorf("mark interview finalizing: %w", err)
		}
	}
	if err := s.finisher.RequestFinish(ctx, id); err != nil {
		if previous == StatusInProgress { // keep the interview usable when the request was not accepted
			interview.Status = previous
			_ = s.repo.Save(context.WithoutCancel(ctx), interview)
		}
		return nil, fmt.Errorf("request interview finalization: %w", err)
	}
	return interview, nil
}

// HandleFinished applies an "interview.finished" event from the AI service. It is idempotent.
func (s *Commands) HandleFinished(ctx context.Context, body []byte) error {
	var event struct {
		InterviewID string `json:"interview_id"`
		Stage       string `json:"stage"`
	}
	if err := json.Unmarshal(body, &event); err != nil || event.InterviewID == "" {
		return fmt.Errorf("%w: malformed finished event", broker.ErrDiscard)
	}
	item, err := s.repo.FindByID(ctx, event.InterviewID)
	if errors.Is(err, ErrNotFound) {
		return fmt.Errorf("%w: unknown interview %s", broker.ErrDiscard, event.InterviewID)
	}
	if err != nil {
		return fmt.Errorf("find interview: %w", err)
	}
	if item.Status == StatusCompleted || item.Status == StatusAbandoned {
		return nil // duplicate delivery
	}
	switch event.Stage {
	case "finished":
		return s.SaveTerminal(ctx, item, StatusCompleted)
	case "abandoned":
		return s.SaveTerminal(ctx, item, StatusAbandoned)
	case "failed": // finalization exhausted its retries: let the candidate try again
		item.Status = StatusInProgress
		return s.repo.Save(ctx, item)
	}
	return fmt.Errorf("%w: unknown stage %q", broker.ErrDiscard, event.Stage)
}

// SaveTerminal persists the status selected by the AI finalizer or stream.
func (s *Commands) SaveTerminal(ctx context.Context, item *model.Interview, status string) error {
	now := time.Now()
	item.Status = status
	item.EndedAt = &now
	return s.repo.Save(ctx, item)
}

// SaveStreamTerminal applies the existing gateway mapping for a terminal AI event.
func (s *Commands) SaveStreamTerminal(ctx context.Context, item *model.Interview, stage string) error {
	status := StatusCompleted
	if stage == "abandoned" {
		status = StatusAbandoned
	}
	return s.SaveTerminal(ctx, item, status)
}
