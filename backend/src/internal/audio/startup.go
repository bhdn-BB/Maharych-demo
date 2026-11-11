package audio

import (
	"context"
	"errors"
	"fmt"
	"strconv"

	"maharych-api/src/internal/genproto/aiservicepb"
	"maharych-api/src/internal/model"
	"maharych-api/src/internal/profile"

	"gorm.io/gorm"
)

var (
	ErrProfileRequired = errors.New("candidate profile required")
	ErrInvalidSetup    = errors.New("invalid interview setup")
)

type userReader interface {
	FindByID(ctx context.Context, id uint) (*model.User, error)
}

type profileReader interface {
	Get(ctx context.Context, userID uint) (*model.Profile, error)
}

type optionReader interface {
	FindByCategoryAndKey(ctx context.Context, category, key string) (*model.InterviewOption, error)
}

// StartupBuilder translates persisted interview context into the gRPC contract.
type StartupBuilder struct {
	users    userReader
	profiles profileReader
	options  optionReader
}

func NewStartupBuilder(users userReader, profiles profileReader, options optionReader) *StartupBuilder {
	return &StartupBuilder{users: users, profiles: profiles, options: options}
}

func (b *StartupBuilder) Build(ctx context.Context, interview *model.Interview) (*aiservicepb.AudioStreamStartupOptions, error) {
	user, err := b.users.FindByID(ctx, interview.UserID)
	if err != nil {
		return nil, fmt.Errorf("load candidate account: %w", err)
	}

	candidateProfile, err := b.profiles.Get(ctx, interview.UserID)
	if errors.Is(err, profile.ErrNotFound) {
		return nil, ErrProfileRequired
	}
	if err != nil {
		return nil, fmt.Errorf("load candidate profile: %w", err)
	}
	if interview.ScenarioVersion != 2 {
		return nil, ErrInvalidSetup // legacy task-based interviews are no longer supported
	}

	grade, ok := gradeForLevel(interview.Level)
	if !ok {
		return nil, ErrInvalidSetup
	}

	position, err := b.options.FindByCategoryAndKey(ctx, "position", interview.Position)
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrInvalidSetup
	}
	if err != nil {
		return nil, fmt.Errorf("load position option: %w", err)
	}
	if _, err := b.options.FindByCategoryAndKey(ctx, "focus", interview.Focus); errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrInvalidSetup
	} else if err != nil {
		return nil, fmt.Errorf("load focus option: %w", err)
	}

	candidate := &aiservicepb.CandidateInfo{
		Name:              candidateProfile.Name,
		Surname:           candidateProfile.Surname,
		Email:             user.Email,
		PhoneNumber:       candidateProfile.PhoneNumber,
		YearsOfExperience: int32(candidateProfile.YearsOfExperience),
		TechStack:         append([]string(nil), candidateProfile.TechStack...),
		Resume:            candidateProfile.Resume,
		IsActive:          true,
	}
	if candidateProfile.LinkedInURL != "" {
		candidate.LinkedinUrl = &candidateProfile.LinkedInURL
	}
	if candidateProfile.GitHubURL != "" {
		candidate.GithubUrl = &candidateProfile.GitHubURL
	}

	return &aiservicepb.AudioStreamStartupOptions{
		VoiceId:                interview.VoiceID,
		InterviewId:            interview.ID.String(),
		Language:               interview.Language,
		ScenarioVersion:        int32(interview.ScenarioVersion),
		UserId:                 strconv.FormatUint(uint64(interview.UserID), 10),
		Focus:                  interview.Focus,
		Candidate:              candidate,
		Position: &aiservicepb.PositionInfo{
			Title: position.Label,
			Grade: grade,
		},
		Metadata: &aiservicepb.AudioMetadata{
			MimeType:   "audio/webm",
			SampleRate: 48000,
			Channels:   1,
			Encoding:   "opus",
		},
	}, nil
}

func gradeForLevel(level string) (aiservicepb.Grade, bool) {
	switch level {
	case "junior":
		return aiservicepb.Grade_GRADE_JUNIOR, true
	case "middle":
		return aiservicepb.Grade_GRADE_MIDDLE, true
	case "senior":
		return aiservicepb.Grade_GRADE_SENIOR, true
	case "lead":
		return aiservicepb.Grade_GRADE_LEAD, true
	default:
		return aiservicepb.Grade_GRADE_UNSPECIFIED, false
	}
}
