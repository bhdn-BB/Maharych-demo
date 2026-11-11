package admin

import (
	"errors"
	"net/http"
	"strconv"
	"strings"

	"maharych-api/src/internal/model"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type Handler struct {
	repo *Repository
}

func NewHandler(repo *Repository) *Handler { return &Handler{repo: repo} }

type OptionRequest struct {
	Category    string  `json:"category" binding:"required"`
	Key         string  `json:"key" binding:"required,max=30"`
	Label       string  `json:"label" binding:"required,max=50"`
	Description *string `json:"description" binding:"omitempty,max=100"`
	Icon        string  `json:"icon" binding:"required,max=30"`
	SortOrder   int     `json:"sortOrder"`
}

type QuestionUpdateRequest struct {
	Question *string `json:"question"`
	Criteria *string `json:"criteria"`
	Active   *bool   `json:"active"`
}

type QuestionVersionRequest struct {
	SourceID uint   `json:"sourceId" binding:"required"`
	Question string `json:"question" binding:"required"`
	Criteria string `json:"criteria" binding:"required"`
}

func validateOption(r OptionRequest) string {
	switch r.Category {
	case "level", "position":
	case "focus":
		if !model.IsSupportedInterviewFocus(r.Key) {
			return "focus key must be one of: algorithms, system-design, behavioral"
		}
	default:
		return "category must be level, position or focus"
	}
	return ""
}

func pathID(c *gin.Context) (uint, bool) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil || id == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return 0, false
	}
	return uint(id), true
}

func fail(c *gin.Context, err error, what string) {
	if errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": what + " not found"})
		return
	}
	c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to process " + what})
}

// ListOptions godoc
// @Summary Admin: list interview options
// @Tags    admin
// @Security BearerAuth
// @Produce json
// @Success 200 {array} model.InterviewOption
// @Failure 403 {object} map[string]string
// @Router  /admin/interview-options [get]
func (h *Handler) ListOptions(c *gin.Context) {
	out, err := h.repo.ListOptions(c.Request.Context())
	if err != nil {
		fail(c, err, "options")
		return
	}
	c.JSON(http.StatusOK, out)
}

// CreateOption godoc
// @Summary Admin: create interview option
// @Tags    admin
// @Security BearerAuth
// @Accept  json
// @Produce json
// @Param   body body OptionRequest true "Option"
// @Success 201 {object} model.InterviewOption
// @Router  /admin/interview-options [post]
func (h *Handler) CreateOption(c *gin.Context) {
	var req OptionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid option"})
		return
	}
	if msg := validateOption(req); msg != "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": msg})
		return
	}
	o := model.InterviewOption{Category: req.Category, Key: req.Key, Label: req.Label,
		Description: req.Description, Icon: req.Icon, SortOrder: req.SortOrder}
	if err := h.repo.CreateOption(c.Request.Context(), &o); err != nil {
		fail(c, err, "option")
		return
	}
	c.JSON(http.StatusCreated, o)
}

// UpdateOption godoc
// @Summary Admin: update interview option
// @Tags    admin
// @Security BearerAuth
// @Accept  json
// @Produce json
// @Param   id   path int           true "Option ID"
// @Param   body body OptionRequest true "Option"
// @Success 200 {object} model.InterviewOption
// @Router  /admin/interview-options/{id} [put]
func (h *Handler) UpdateOption(c *gin.Context) {
	id, ok := pathID(c)
	if !ok {
		return
	}
	var req OptionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid option"})
		return
	}
	if msg := validateOption(req); msg != "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": msg})
		return
	}
	o, err := h.repo.GetOption(c.Request.Context(), id)
	if err != nil {
		fail(c, err, "option")
		return
	}
	o.Category, o.Key, o.Label, o.Description, o.Icon, o.SortOrder =
		req.Category, req.Key, req.Label, req.Description, req.Icon, req.SortOrder
	if err := h.repo.SaveOption(c.Request.Context(), o); err != nil {
		fail(c, err, "option")
		return
	}
	c.JSON(http.StatusOK, o)
}

// DeleteOption godoc
// @Summary Admin: delete interview option
// @Tags    admin
// @Security BearerAuth
// @Param   id path int true "Option ID"
// @Success 204
// @Router  /admin/interview-options/{id} [delete]
func (h *Handler) DeleteOption(c *gin.Context) {
	id, ok := pathID(c)
	if !ok {
		return
	}
	found, err := h.repo.DeleteOption(c.Request.Context(), id)
	if err != nil {
		fail(c, err, "option")
		return
	}
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "option not found"})
		return
	}
	c.Status(http.StatusNoContent)
}

// ListQuestions godoc
// @Summary Admin: list question bank rows
// @Tags    admin
// @Security BearerAuth
// @Produce json
// @Param   language query string false "uk|en"
// @Param   focus    query string false "focus key"
// @Param   active   query bool   false "only active/inactive"
// @Success 200 {array} QuestionBankRow
// @Router  /admin/questions [get]
func (h *Handler) ListQuestions(c *gin.Context) {
	f := QuestionFilter{Language: c.Query("language"), Focus: c.Query("focus")}
	if v := c.Query("active"); v != "" {
		b, err := strconv.ParseBool(v)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid active"})
			return
		}
		f.Active = &b
	}
	out, err := h.repo.ListQuestions(c.Request.Context(), f)
	if err != nil {
		fail(c, err, "questions")
		return
	}
	c.JSON(http.StatusOK, out)
}

// UpdateQuestion godoc
// @Summary Admin: edit question text/criteria or toggle active
// @Tags    admin
// @Security BearerAuth
// @Accept  json
// @Produce json
// @Param   id   path int                   true "Row ID"
// @Param   body body QuestionUpdateRequest true "Fields to change"
// @Success 200 {object} QuestionBankRow
// @Router  /admin/questions/{id} [put]
func (h *Handler) UpdateQuestion(c *gin.Context) {
	id, ok := pathID(c)
	if !ok {
		return
	}
	var req QuestionUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid body"})
		return
	}
	row, err := h.repo.GetQuestion(c.Request.Context(), id)
	if err != nil {
		fail(c, err, "question")
		return
	}
	if req.Question != nil {
		if strings.TrimSpace(*req.Question) == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "question must not be empty"})
			return
		}
		row.Question = *req.Question
	}
	if req.Criteria != nil {
		if strings.TrimSpace(*req.Criteria) == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "criteria must not be empty"})
			return
		}
		row.Criteria = *req.Criteria
	}
	if req.Active != nil {
		row.Active = *req.Active
	}
	if err := h.repo.SaveQuestion(c.Request.Context(), row); err != nil {
		fail(c, err, "question")
		return
	}
	c.JSON(http.StatusOK, row)
}

// CreateQuestionVersion godoc
// @Summary Admin: create a new version of a question
// @Description Copies the source row into version max+1 for the same key/language with new text.
// @Tags    admin
// @Security BearerAuth
// @Accept  json
// @Produce json
// @Param   body body QuestionVersionRequest true "Source and new text"
// @Success 201 {object} QuestionBankRow
// @Router  /admin/questions [post]
func (h *Handler) CreateQuestionVersion(c *gin.Context) {
	var req QuestionVersionRequest
	if err := c.ShouldBindJSON(&req); err != nil ||
		strings.TrimSpace(req.Question) == "" || strings.TrimSpace(req.Criteria) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "sourceId, question and criteria are required"})
		return
	}
	src, err := h.repo.GetQuestion(c.Request.Context(), req.SourceID)
	if err != nil {
		fail(c, err, "question")
		return
	}
	created, err := h.repo.NewQuestionVersion(c.Request.Context(), src, req.Question, req.Criteria)
	if err != nil {
		fail(c, err, "question")
		return
	}
	c.JSON(http.StatusCreated, created)
}

// ListOutbox godoc
// @Summary Admin: list feedback outbox entries
// @Tags    admin
// @Security BearerAuth
// @Produce json
// @Param   pending query bool false "only unpublished"
// @Success 200 {array} OutboxRow
// @Router  /admin/feedback-outbox [get]
func (h *Handler) ListOutbox(c *gin.Context) {
	pending, _ := strconv.ParseBool(c.Query("pending"))
	out, err := h.repo.ListOutbox(c.Request.Context(), pending)
	if err != nil {
		fail(c, err, "outbox")
		return
	}
	c.JSON(http.StatusOK, out)
}

// RetryOutbox godoc
// @Summary Admin: retry a feedback outbox entry
// @Tags    admin
// @Security BearerAuth
// @Param   interviewId path string true "Interview ID"
// @Success 204
// @Router  /admin/feedback-outbox/{interviewId}/retry [post]
func (h *Handler) RetryOutbox(c *gin.Context) {
	found, err := h.repo.RetryOutbox(c.Request.Context(), c.Param("interviewId"))
	if err != nil {
		fail(c, err, "outbox")
		return
	}
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "outbox entry not found"})
		return
	}
	c.Status(http.StatusNoContent)
}
