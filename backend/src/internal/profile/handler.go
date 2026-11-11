package profile

import (
	"errors"
	"net/http"

	"maharych-api/src/internal/middleware"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	service *Service
}

func NewHandler(service *Service) *Handler {
	return &Handler{service: service}
}

// Get godoc
// @Summary Get the authenticated user's candidate profile
// @Tags profile
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} Response
// @Failure 404 {object} map[string]string
// @Router /profile [get]
func (h *Handler) Get(c *gin.Context) {
	user := middleware.CurrentUser(c)
	profile, err := h.service.Get(c.Request.Context(), user.ID)
	if errors.Is(err, ErrNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "profile not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to load profile"})
		return
	}
	c.JSON(http.StatusOK, toResponse(profile))
}

// Put godoc
// @Summary Create or replace the authenticated user's candidate profile
// @Tags profile
// @Accept json
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Param body body PutRequest true "Candidate profile"
// @Success 200 {object} Response
// @Failure 400 {object} map[string]string
// @Router /profile [put]
func (h *Handler) Put(c *gin.Context) {
	var req PutRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid profile payload"})
		return
	}
	user := middleware.CurrentUser(c)
	profile, err := h.service.Put(c.Request.Context(), user.ID, req)
	if errors.Is(err, ErrInvalid) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "name, surname, phone and experience are required; check field lengths and URLs"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to save profile"})
		return
	}
	c.JSON(http.StatusOK, toResponse(profile))
}
