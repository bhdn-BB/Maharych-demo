package audio

import (
	"context"
	"errors"
	"testing"

	"maharych-api/src/internal/genproto/aiservicepb"
	"maharych-api/src/internal/model"
	"maharych-api/src/internal/profile"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type testUsers struct{ user *model.User }

func (r testUsers) FindByID(_ context.Context, id uint) (*model.User, error) {
	if r.user == nil || r.user.ID != id {
		return nil, gorm.ErrRecordNotFound
	}
	return r.user, nil
}

type testProfiles struct{ value *model.Profile }

func (r testProfiles) Get(_ context.Context, userID uint) (*model.Profile, error) {
	if r.value == nil || r.value.UserID != userID {
		return nil, profile.ErrNotFound
	}
	return r.value, nil
}

type testOptions map[string]*model.InterviewOption

func (r testOptions) FindByCategoryAndKey(_ context.Context, category, key string) (*model.InterviewOption, error) {
	if value, ok := r[category+":"+key]; ok {
		return value, nil
	}
	return nil, gorm.ErrRecordNotFound
}

func TestStartupBuilderUsesStoredCandidateAndInterviewOptions(t *testing.T) {
	user := &model.User{Email: "candidate@example.com"}
	user.ID = 7
	linkedIn := "https://linkedin.com/in/candidate"
	builder := NewStartupBuilder(
		testUsers{user},
		testProfiles{&model.Profile{
			UserID: 7, Name: "Oksana", Surname: "Shevchenko",
			PhoneNumber: "+380501234567", YearsOfExperience: 4,
			TechStack: []string{"Go", "PostgreSQL"}, Resume: "Backend developer",
			LinkedInURL: linkedIn,
		}},
		testOptions{
			"position:backend": {Label: "Backend"},
			"focus:algorithms": {Label: "Algorithms"},
		},
	)
	interview := &model.Interview{
		VoiceID: "daniel",
		ID:      uuid.MustParse("628b8e76-c5ab-4d67-854c-70c31b2eca16"),
		UserID:  7, Level: "middle", Position: "backend", Focus: "algorithms",
		ScenarioVersion: 2,
	}

	options, err := builder.Build(context.Background(), interview)
	if err != nil {
		t.Fatal(err)
	}
	if options.InterviewId != interview.ID.String() || options.UserId != "7" || options.Focus != "algorithms" {
		t.Fatalf("wrong interview identity: %+v", options)
	}
	if options.VoiceId != "daniel" {
		t.Fatalf("voice was not sent: %q", options.VoiceId)
	}
	if options.Candidate.Email != user.Email || options.Candidate.Name != "Oksana" ||
		options.Candidate.YearsOfExperience != 4 || len(options.Candidate.TechStack) != 2 ||
		options.Candidate.GetLinkedinUrl() != linkedIn {
		t.Fatalf("candidate context was not mapped: %+v", options.Candidate)
	}
	if options.Position.Title != "Backend" || options.Position.Grade != aiservicepb.Grade_GRADE_MIDDLE {
		t.Fatalf("position context was not mapped: %+v", options.Position)
	}
	if options.Metadata.MimeType != "audio/webm" || options.Metadata.Encoding != "opus" {
		t.Fatalf("wrong audio metadata: %+v", options.Metadata)
	}
	if options.ScenarioVersion != 2 {
		t.Fatalf("scenario version was not sent: %+v", options)
	}
}

func TestStartupBuilderRequiresProfile(t *testing.T) {
	user := &model.User{Email: "candidate@example.com"}
	user.ID = 7
	builder := NewStartupBuilder(testUsers{user}, testProfiles{}, testOptions{})
	_, err := builder.Build(context.Background(), &model.Interview{UserID: 7})
	if !errors.Is(err, ErrProfileRequired) {
		t.Fatalf("expected ErrProfileRequired, got %v", err)
	}
}

func TestStartupBuilderSendsFullPositionLabel(t *testing.T) {
	user := &model.User{Email: "candidate@example.com"}
	user.ID = 7
	builder := NewStartupBuilder(testUsers{user}, testProfiles{&model.Profile{UserID: 7}}, testOptions{
		"position:data":    {Label: "Data Science"},
		"focus:behavioral": {Label: "Behavioral"},
	})
	options, err := builder.Build(context.Background(), &model.Interview{UserID: 7, Level: "middle", Position: "data", Focus: "behavioral", ScenarioVersion: 2})
	if err != nil || options.Position.Title != "Data Science" || options.Focus != "behavioral" {
		t.Fatalf("incorrect startup context: %+v, %v", options, err)
	}
}

func TestStartupBuilderRejectsUnknownSetup(t *testing.T) {
	user := &model.User{Email: "candidate@example.com"}
	user.ID = 7
	builder := NewStartupBuilder(testUsers{user}, testProfiles{&model.Profile{UserID: 7}}, testOptions{})
	_, err := builder.Build(context.Background(), &model.Interview{UserID: 7, Level: "unknown"})
	if !errors.Is(err, ErrInvalidSetup) {
		t.Fatalf("expected ErrInvalidSetup, got %v", err)
	}
}
