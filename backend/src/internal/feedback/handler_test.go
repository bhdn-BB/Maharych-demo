package feedback

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"maharych-api/src/internal/interview"
	"maharych-api/src/internal/middleware"
	"maharych-api/src/internal/model"

	"github.com/gin-gonic/gin"
)

type interviewRepo struct{ owner uint }

func (r interviewRepo) Create(context.Context, *model.Interview) error { return nil }
func (r interviewRepo) FindByID(context.Context, string) (*model.Interview, error) {
	return &model.Interview{UserID: r.owner}, nil
}
func (r interviewRepo) Save(context.Context, *model.Interview) error   { return nil }
func (r interviewRepo) ListByUser(context.Context, uint, int, int) ([]model.Interview, int64, error) {
	return nil, 0, nil
}
func (r interviewRepo) FindByIDAndUser(_ context.Context, _ string, userID uint) (*model.Interview, error) {
	if userID != r.owner {
		return nil, interview.ErrNotFound
	}
	return &model.Interview{UserID: r.owner}, nil
}

type reportRepo struct{ calls int }

func (r *reportRepo) GetByInterviewID(context.Context, string) (*Report, error) {
	r.calls++
	return &Report{OverallScore: 8, Summary: "Good fundamentals"}, nil
}

func TestFeedbackRequiresInterviewOwnership(t *testing.T) {
	gin.SetMode(gin.TestMode)
	reports := &reportRepo{}
	service := interview.NewService(interviewRepo{owner: 7}, nil, nil, nil)
	handler := NewHandler(service, reports)
	router := gin.New()
	router.Use(func(c *gin.Context) {
		c.Set("authUser", middleware.AuthUser{ID: 9})
	})
	router.GET("/interviews/:id/feedback", handler.Get)

	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/interviews/id/feedback", nil))
	if response.Code != http.StatusNotFound || reports.calls != 0 {
		t.Fatalf("foreign feedback was fetched: status=%d calls=%d", response.Code, reports.calls)
	}
}

func TestFeedbackReturnsStoredReportToOwner(t *testing.T) {
	gin.SetMode(gin.TestMode)
	reports := &reportRepo{}
	service := interview.NewService(interviewRepo{owner: 7}, nil, nil, nil)
	handler := NewHandler(service, reports)
	router := gin.New()
	router.Use(func(c *gin.Context) {
		c.Set("authUser", middleware.AuthUser{ID: 7})
	})
	router.GET("/interviews/:id/feedback", handler.Get)

	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/interviews/id/feedback", nil))
	var report Report
	if err := json.Unmarshal(response.Body.Bytes(), &report); err != nil {
		t.Fatal(err)
	}
	if response.Code != http.StatusOK || reports.calls != 1 || report.OverallScore != 8 {
		t.Fatalf("expected owner report: status=%d calls=%d report=%+v", response.Code, reports.calls, report)
	}
}
