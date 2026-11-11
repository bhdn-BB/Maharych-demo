package interview

import (
	"context"
	"errors"
	"fmt"

	"maharych-api/src/internal/model"
)

func (s *Queries) Get(ctx context.Context, id string, userID uint) (*model.Interview, error) {
	interview, err := s.repo.FindByIDAndUser(ctx, id, userID)
	if errors.Is(err, ErrNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("find interview: %w", err)
	}

	return interview, nil
}

func (s *Queries) List(ctx context.Context, userID uint, page, pageSize int) ([]Response, int64, error) {
	items, total, err := s.repo.ListByUser(ctx, userID, pageSize, (page-1)*pageSize)
	if err != nil {
		return nil, 0, fmt.Errorf("list interviews: %w", err)
	}
	responses := make([]Response, 0, len(items))
	for i := range items {
		responses = append(responses, ToResponse(&items[i]))
	}
	return responses, total, nil
}
