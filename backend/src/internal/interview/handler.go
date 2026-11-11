package interview

import (
	"log"
	"errors"
	"net/http"
	"strconv"

	"maharych-api/src/internal/middleware"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	svc *Service
}

func NewHandler(svc *Service) *Handler {
	return &Handler{svc: svc}
}

// Start godoc
// @Summary     Start a new interview
// @Description Starts a behavioral, oral algorithms, or CV-adapted system-design interview without a catalog task
// @Tags        interviews
// @Accept      json
// @Produce     json
// @Param       Authorization header string       true "Bearer token"
// @Param       body          body   StartRequest true "Interview options"
// @Success     201           {object} Response
// @Failure     400           {object} map[string]string
// @Failure     401           {object} map[string]string
// @Failure     409           {object} map[string]string
// @Router      /interviews [post]
func (h *Handler) Start(c *gin.Context) {
	user := middleware.CurrentUser(c)

	var req StartRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Check your interview level, position, type, language and voice."})
		return
	}

	interview, err := h.svc.Start(c.Request.Context(), user.ID, req.Level, req.Position, req.Focus, req.TaskID, req.Language, req.VoiceID)
	if err != nil {
		if errors.Is(err, ErrProfileRequired) {
			c.JSON(http.StatusConflict, gin.H{"error": "complete your candidate profile before starting an interview"})
			return
		}
		if errors.Is(err, ErrInvalidOption) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "unknown interview option"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create interview"})
		return
	}

	c.JSON(http.StatusCreated, ToResponse(interview))
}

// End godoc
// @Summary     End an interview
// @Description Requests asynchronous finalization of saved answers. Returns 202 with status "finalizing"; poll GET /interviews/{id} until it becomes completed or abandoned. Repeating the call is safe.
// @Tags        interviews
// @Produce     json
// @Param       Authorization header string true "Bearer token"
// @Param       id            path   string true "Interview ID"
// @Success     200           {object} Response
// @Success     202           {object} Response
// @Failure     401           {object} map[string]string
// @Failure     404           {object} map[string]string
// @Failure     503           {object} map[string]string
// @Router      /interviews/{id}/end [post]
func (h *Handler) End(c *gin.Context) {
	user := middleware.CurrentUser(c)
	id := c.Param("id")

	interview, err := h.svc.End(c.Request.Context(), id, user.ID)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			c.JSON(http.StatusNotFound, gin.H{"error": "interview not found"})
			return
		}
		if errors.Is(err, ErrNotInProgress) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "interview is not in progress"})
			return
		}
		if errors.Is(err, ErrFinalizerUnavailable) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "interview finalization is unavailable"})
			return
		}
		log.Printf("request interview finalization: %v", err)
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "could not request interview finalization, try again"})
		return
	}

	if interview.Status == StatusFinalizing {
		c.JSON(http.StatusAccepted, ToResponse(interview))
		return
	}
	c.JSON(http.StatusOK, ToResponse(interview))
}

// Get godoc
// @Summary     Get an interview by ID
// @Description Returns a single interview belonging to the authenticated user
// @Tags        interviews
// @Produce     json
// @Param       Authorization header string true "Bearer token"
// @Param       id            path   string true "Interview ID"
// @Success     200           {object} Response
// @Failure     401           {object} map[string]string
// @Failure     404           {object} map[string]string
// @Router      /interviews/{id} [get]
func (h *Handler) Get(c *gin.Context) {
	user := middleware.CurrentUser(c)
	id := c.Param("id")

	interview, err := h.svc.Get(c.Request.Context(), id, user.ID)
	if errors.Is(err, ErrNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "interview not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to load interview"})
		return
	}

	c.JSON(http.StatusOK, ToResponse(interview))
}

// List godoc
// @Summary List the current user's interviews
// @Tags interviews
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Param page query int false "Page number, starting at 1"
// @Param pageSize query int false "Items per page, up to 50"
// @Success 200 {object} ListResponse
// @Failure 401 {object} map[string]string
// @Router /interviews [get]
func (h *Handler) List(c *gin.Context) {
	user := middleware.CurrentUser(c)
	page, err := strconv.Atoi(c.DefaultQuery("page", "1"))
	if err != nil || page < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "page must be a positive integer"})
		return
	}
	pageSize, err := strconv.Atoi(c.DefaultQuery("pageSize", "10"))
	if err != nil || pageSize < 1 || pageSize > 50 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "pageSize must be between 1 and 50"})
		return
	}
	items, total, err := h.svc.List(c.Request.Context(), user.ID, page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list interviews"})
		return
	}
	c.JSON(http.StatusOK, ListResponse{Items: items, Page: page, PageSize: pageSize, Total: total})
}
