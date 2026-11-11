package feedback

import (
	"context"
	"errors"
	"net/http"

	"maharych-api/src/internal/interview"
	"maharych-api/src/internal/middleware"
	"maharych-api/src/internal/model"

	"github.com/gin-gonic/gin"
)

type interviewReader interface {
	Get(context.Context, string, uint) (*model.Interview, error)
}

type Handler struct {
	interviews interviewReader
	reports    Repository
}

func NewHandler(interviews interviewReader, reports Repository) *Handler {
	return &Handler{interviews: interviews, reports: reports}
}

// Get godoc
// @Summary Get completed interview feedback
// @Tags interviews
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Param id path string true "Interview ID"
// @Success 200 {object} Report
// @Failure 401 {object} map[string]string
// @Failure 404 {object} map[string]string
// @Router /interviews/{id}/feedback [get]
func (h *Handler) Get(c *gin.Context) {
	user := middleware.CurrentUser(c)
	id := c.Param("id")
	if _, err := h.interviews.Get(c.Request.Context(), id, user.ID); err != nil {
		if errors.Is(err, interview.ErrNotFound) {
			c.JSON(http.StatusNotFound, gin.H{"error": "interview not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to load interview"})
		return
	}

	report, err := h.reports.GetByInterviewID(c.Request.Context(), id)
	if errors.Is(err, ErrNotReady) {
		c.JSON(http.StatusNotFound, gin.H{"error": "feedback not available"})
		return
	}
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "feedback service unavailable"})
		return
	}
	c.JSON(http.StatusOK, report)
}

// GetPDF godoc
// @Summary Download the completed interview PDF report
// @Tags interviews
// @Produce application/pdf
// @Param Authorization header string true "Bearer token"
// @Param id path string true "Interview ID"
// @Success 200 {file} file
// @Failure 401 {object} map[string]string
// @Failure 404 {object} map[string]string
// @Router /interviews/{id}/report.pdf [get]
func (h *Handler) GetPDF(c *gin.Context) {
	user := middleware.CurrentUser(c)
	id := c.Param("id")
	if _, err := h.interviews.Get(c.Request.Context(), id, user.ID); err != nil {
		if errors.Is(err, interview.ErrNotFound) {
			c.JSON(http.StatusNotFound, gin.H{"error": "interview not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to load interview"})
		return
	}
	repository, ok := h.reports.(PDFRepository)
	if !ok {
		c.JSON(http.StatusBadGateway, gin.H{"error": "PDF service unavailable"})
		return
	}
	pdf, err := repository.GetPDFByInterviewID(c.Request.Context(), id)
	if errors.Is(err, ErrNotReady) {
		c.JSON(http.StatusNotFound, gin.H{"error": "PDF report not ready"})
		return
	}
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "PDF service unavailable"})
		return
	}
	c.Header("Content-Disposition", "attachment; filename=interview-report.pdf")
	c.Data(http.StatusOK, "application/pdf", pdf)
}
