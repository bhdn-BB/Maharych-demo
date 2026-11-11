package interview

import (
	"context"
	"errors"
	"testing"

)

func TestStartDialogueDoesNotRequireCatalogTask(t *testing.T) {
	options := testOptionReader{"level:middle": true, "position:backend": true, "focus:algorithms": true, "focus:system-design": true}
	for _, focus := range []string{"algorithms", "system-design"} {
		for _, language := range []string{"uk", "en"} {
			t.Run(focus+"/"+language, func(t *testing.T) {
				repo := &testRepository{}
				svc := NewService(repo, testProfileReader{exists: true}, options, nil)
				got, err := svc.Start(context.Background(), 7, "middle", "backend", focus, nil, language)
				if err != nil {
					t.Fatal(err)
				}
				if got.TaskID != nil || got.ScenarioVersion != 2 || got.Language != language {
					t.Fatalf("unexpected setup: %+v", got)
				}
			})
		}
	}
	svc := NewService(&testRepository{}, testProfileReader{exists: true}, options, nil)
	for _, language := range []string{"fr", "uk-UA"} {
		if _, err := svc.Start(context.Background(), 7, "middle", "backend", "algorithms", nil, language); !errors.Is(err, ErrInvalidOption) {
			t.Fatalf("accepted %s: %v", language, err)
		}
	}
	for _, focus := range []string{"behavioral", "live-coding", "unknown"} {
		t.Run("reject "+focus, func(t *testing.T) {
			if _, err := svc.Start(context.Background(), 7, "middle", "backend", focus, nil, "uk"); !errors.Is(err, ErrInvalidOption) {
				t.Fatalf("accepted unsupported mode: %v", err)
			}
		})
	}
}
