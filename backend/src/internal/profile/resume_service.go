package profile

import (
	"context"
	"errors"
	"fmt"
	"net/http"
)

const maxResumeBytes = 5 * 1024 * 1024

var ErrResumeInvalid = errors.New("invalid resume")

type resumeParser interface {
	Parse(context.Context, string, []byte) (int, []byte, error)
}

type ResumeService struct{ parser resumeParser }

func NewResumeService(parser resumeParser) *ResumeService { return &ResumeService{parser: parser} }

func (s *ResumeService) Parse(ctx context.Context, kind string, data []byte) (int, []byte, error) {
	if kind != "pdf" && kind != "docx" {
		return 0, nil, fmt.Errorf("%w: Only PDF and DOCX files are supported", ErrResumeInvalid)
	}
	if len(data) == 0 || len(data) > maxResumeBytes {
		return 0, nil, fmt.Errorf("%w: File must be between 1 byte and 5 MiB", ErrResumeInvalid)
	}
	status, body, err := s.parser.Parse(ctx, kind, data)
	if err != nil || status >= http.StatusInternalServerError {
		return 0, nil, fmt.Errorf("resume extraction unavailable: %w", errOrStatus(err, status))
	}
	return status, body, nil
}

func errOrStatus(err error, status int) error {
	if err != nil {
		return err
	}
	return fmt.Errorf("upstream status %d", status)
}
