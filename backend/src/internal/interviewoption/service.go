package interviewoption

import (
	"context"
	"fmt"

	"maharych-api/src/internal/model"
)

type Service struct {
	repo Repository
}

func NewService(repo Repository) *Service {
	return &Service{repo: repo}
}

func (s *Service) GetAll(ctx context.Context) (*OptionsResponse, error) {
	all, err := s.repo.FindAllOrdered(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch interview options: %w", err)
	}

	var resp OptionsResponse
	for _, o := range all {
		switch o.Category {
		case "level":
			resp.Levels = append(resp.Levels, o)
		case "position":
			resp.Positions = append(resp.Positions, o)
		case "focus":
			if !model.IsSupportedInterviewFocus(o.Key) {
				continue
			}
			description := "Explain algorithms and time/space complexity orally"
			if o.Key == "system-design" {
				description = "CV-based service design, budget and architecture tradeoffs"
			} else if o.Key == "behavioral" {
				description = "Motivation, teamwork and real work experiences"
				o.Label = "Behavioral"
				o.Icon = "MessageSquare"
			}
			o.Description = &description
			resp.Focuses = append(resp.Focuses, o)
		}
	}

	return &resp, nil
}
