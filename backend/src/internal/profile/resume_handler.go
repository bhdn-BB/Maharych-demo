package profile

import (
	"errors"
	"io"
	"net/http"

	"github.com/gin-gonic/gin"
)

type ResumeHandler struct{ service *ResumeService }

func NewResumeHandler(service *ResumeService) *ResumeHandler { return &ResumeHandler{service: service} }

// Parse extracts text from an optional resume.
// @Summary Parse a PDF or DOCX resume
// @Tags profile
// @Security BearerAuth
// @Accept application/octet-stream
// @Produce json
// @Param kind query string true "File type: pdf or docx"
// @Param file body string true "Resume file bytes"
// @Success 200 {object} map[string]string
// @Failure 400 {object} map[string]string
// @Failure 502 {object} map[string]string
// @Router /profile/resume/parse [post]
func (h *ResumeHandler) Parse(c *gin.Context) {
	data, err := io.ReadAll(io.LimitReader(c.Request.Body, maxResumeBytes+1))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Could not read file"})
		return
	}
	status, body, err := h.service.Parse(c.Request.Context(), c.Query("kind"), data)
	if errors.Is(err, ErrResumeInvalid) {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "Resume extraction unavailable"})
		return
	}
	c.Data(status, "application/json", body)
}
