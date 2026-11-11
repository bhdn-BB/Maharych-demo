package interviewoption

import (
	"context"
	"errors"
	"testing"

	"maharych-api/src/internal/model"
)

type optionFixture []model.InterviewOption

func (r optionFixture) FindAllOrdered(context.Context) ([]model.InterviewOption, error) {
	return r, nil
}

func (r optionFixture) FindByCategoryAndKey(context.Context, string, string) (*model.InterviewOption, error) {
	return nil, errors.New("option listing must not query individual options")
}

func TestOptionsExcludeRetiredModesFromExistingDatabase(t *testing.T) {
	oldDescription := "Old description"
	service := NewService(optionFixture{
		{Category: "level", Key: "middle"},
		{Category: "position", Key: "frontend"},
		{Category: "focus", Key: "algorithms", Description: &oldDescription},
		{Category: "focus", Key: "system-design", Description: &oldDescription},
		{Category: "focus", Key: "behavioral"},
		{Category: "focus", Key: "live-coding"},
		{Category: "focus", Key: "unknown"},
	})
	got, err := service.GetAll(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(got.Focuses) != 3 || got.Focuses[0].Key != "algorithms" || got.Focuses[1].Key != "system-design" || got.Focuses[2].Key != "behavioral" {
		t.Fatalf("unexpected supported focuses: %+v", got.Focuses)
	}
	if len(got.Levels) != 1 || len(got.Positions) != 1 {
		t.Fatal("unrelated option categories changed")
	}
	for _, focus := range got.Focuses {
		if focus.Description == nil || *focus.Description == oldDescription {
			t.Errorf("stale description for %s", focus.Key)
		}
	}
}
