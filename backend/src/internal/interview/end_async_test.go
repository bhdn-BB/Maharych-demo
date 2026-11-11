package interview

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"maharych-api/src/internal/broker"
	"maharych-api/src/internal/model"
)

type fakeFinisher struct {
	requested []string
	err       error
}

func (f *fakeFinisher) RequestFinish(_ context.Context, id string) error {
	f.requested = append(f.requested, id)
	return f.err
}

func TestEndEnqueuesFinalizationInsteadOfCompleting(t *testing.T) {
	repo := &testRepository{existing: &model.Interview{Status: StatusInProgress}}
	finisher := &fakeFinisher{}
	svc := NewService(repo, nil, nil, finisher)

	got, err := svc.End(context.Background(), "id", 7)
	if err != nil {
		t.Fatal(err)
	}
	if got.Status != StatusFinalizing || got.EndedAt != nil || repo.saved != 1 || len(finisher.requested) != 1 {
		t.Fatalf("status=%s endedAt=%v saves=%d requests=%v", got.Status, got.EndedAt, repo.saved, finisher.requested)
	}
}

func TestEndRepeatedWhileFinalizingReEnqueuesWithoutSaving(t *testing.T) {
	repo := &testRepository{existing: &model.Interview{Status: StatusFinalizing}}
	finisher := &fakeFinisher{}
	svc := NewService(repo, nil, nil, finisher)

	got, err := svc.End(context.Background(), "id", 7)
	if err != nil || got.Status != StatusFinalizing || repo.saved != 0 || len(finisher.requested) != 1 {
		t.Fatalf("status=%s saves=%d requests=%v err=%v", got.Status, repo.saved, finisher.requested, err)
	}
}

func TestEndOnTerminalInterviewDoesNothing(t *testing.T) {
	for _, status := range []string{StatusCompleted, StatusAbandoned} {
		repo := &testRepository{existing: &model.Interview{Status: status}}
		finisher := &fakeFinisher{}
		svc := NewService(repo, nil, nil, finisher)
		if _, err := svc.End(context.Background(), "id", 7); err != nil || repo.saved != 0 || len(finisher.requested) != 0 {
			t.Fatalf("%s: saves=%d requests=%v err=%v", status, repo.saved, finisher.requested, err)
		}
	}
}

func TestEndKeepsInterviewUsableWhenBrokerRejectsRequest(t *testing.T) {
	repo := &testRepository{existing: &model.Interview{Status: StatusInProgress}}
	svc := NewService(repo, nil, nil, &fakeFinisher{err: errors.New("broker down")})

	if _, err := svc.End(context.Background(), "id", 7); err == nil {
		t.Fatal("expected the broker failure to be reported")
	}
	if repo.existing.Status != StatusInProgress {
		t.Fatalf("interview left in %s after a rejected request", repo.existing.Status)
	}
}

func TestEndWithoutFinisherFailsExplicitly(t *testing.T) {
	repo := &testRepository{existing: &model.Interview{Status: StatusInProgress}}
	svc := NewService(repo, nil, nil, nil)
	if _, err := svc.End(context.Background(), "id", 7); !errors.Is(err, ErrFinalizerUnavailable) || repo.saved != 0 {
		t.Fatalf("err=%v saves=%d", err, repo.saved)
	}
}

func TestEndRejectsUnknownAndForeignInterviews(t *testing.T) {
	svc := NewService(&testRepository{}, nil, nil, &fakeFinisher{})
	if _, err := svc.End(context.Background(), "id", 7); !errors.Is(err, ErrNotFound) {
		t.Fatalf("err=%v", err)
	}
}

func finishedEvent(t *testing.T, id, stage string) []byte {
	t.Helper()
	body, err := json.Marshal(map[string]string{"interview_id": id, "stage": stage})
	if err != nil {
		t.Fatal(err)
	}
	return body
}

func TestHandleFinishedStoresTerminalStatusIdempotently(t *testing.T) {
	for _, tc := range []struct{ stage, want string }{
		{"finished", StatusCompleted},
		{"abandoned", StatusAbandoned},
		{"failed", StatusInProgress},
	} {
		t.Run(tc.stage, func(t *testing.T) {
			item := &model.Interview{Status: StatusFinalizing}
			repo := &testRepository{existing: item}
			svc := NewService(repo, nil, nil, nil)
			if err := svc.HandleFinished(context.Background(), finishedEvent(t, "id", tc.stage)); err != nil {
				t.Fatal(err)
			}
			if item.Status != tc.want || repo.saved != 1 {
				t.Fatalf("status=%s saves=%d", item.Status, repo.saved)
			}
			if tc.want != StatusInProgress {
				if item.EndedAt == nil {
					t.Fatal("terminal status must record EndedAt")
				}
				if err := svc.HandleFinished(context.Background(), finishedEvent(t, "id", tc.stage)); err != nil || repo.saved != 1 {
					t.Fatalf("duplicate delivery changed state: saves=%d err=%v", repo.saved, err)
				}
			}
		})
	}
}

func TestHandleFinishedDiscardsUnprocessableEventsButRetriesStorageErrors(t *testing.T) {
	svc := NewService(&testRepository{existing: &model.Interview{Status: StatusFinalizing}}, nil, nil, nil)
	for name, body := range map[string][]byte{
		"malformed json": []byte("{"),
		"missing id":     []byte(`{"stage":"finished"}`),
		"unknown stage":  finishedEvent(t, "id", "weird"),
	} {
		if err := svc.HandleFinished(context.Background(), body); !errors.Is(err, broker.ErrDiscard) {
			t.Fatalf("%s: want ErrDiscard, got %v", name, err)
		}
	}
	unknown := NewService(&testRepository{}, nil, nil, nil)
	if err := unknown.HandleFinished(context.Background(), finishedEvent(t, "id", "finished")); !errors.Is(err, broker.ErrDiscard) {
		t.Fatalf("unknown interview: %v", err)
	}
	storage := errors.New("database unavailable")
	failing := NewService(&testRepository{findErr: storage}, nil, nil, nil)
	if err := failing.HandleFinished(context.Background(), finishedEvent(t, "id", "finished")); !errors.Is(err, storage) || errors.Is(err, broker.ErrDiscard) {
		t.Fatalf("storage error must be retried, got %v", err)
	}
}
