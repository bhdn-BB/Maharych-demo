package interviewoption

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	svc *Service
}

func NewHandler(svc *Service) *Handler {
	return &Handler{svc: svc}
}

// GetAll godoc
// @Summary     Get interview options
// @Description Returns all available levels, positions, and focus areas
// @Tags        interview-options
// @Produce     json
// @Success     200 {object} OptionsResponse
// @Router      /interview-options [get]
func (h *Handler) GetAll(c *gin.Context) {
	resp, err := h.svc.GetAll(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch interview options"})
		return
	}

	c.JSON(http.StatusOK, resp)
}
