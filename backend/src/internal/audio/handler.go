package audio

import (
	"context"
	"errors"
	"log"
	"net/http"
	"time"

	"maharych-api/src/internal/genproto/aiservicepb"
	"maharych-api/src/internal/interview"
	"maharych-api/src/internal/middleware"
	"maharych-api/src/internal/model"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
)

type interviewLifecycle interface {
	Get(context.Context, string, uint) (*model.Interview, error)
	SaveStreamTerminal(context.Context, *model.Interview, string) error
}

type Handler struct {
	tickets    *TicketStore
	interviews interviewLifecycle
	startup    *StartupBuilder
	aiClient   aiservicepb.AIServiceClient
	upgrader   websocket.Upgrader
}

func NewHandler(interviews interviewLifecycle, startup *StartupBuilder, aiClient aiservicepb.AIServiceClient, allowedOrigins []string) *Handler {
	allowed := make(map[string]struct{}, len(allowedOrigins))
	for _, origin := range allowedOrigins {
		allowed[origin] = struct{}{}
	}
	return &Handler{
		tickets:    NewTicketStore(),
		interviews: interviews,
		startup:    startup,
		aiClient:   aiClient,
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool {
				origin := r.Header.Get("Origin")
				if origin == "" { // Non-browser clients do not send an Origin header.
					return true
				}
				_, ok := allowed[origin]
				return ok
			},
		},
	}
}

// Ticket godoc
// @Summary     Issue a one-time WebSocket ticket
// @Description Returns a 30-second, single-use ticket that authorizes one audio WebSocket handshake for this interview
// @Tags        interviews
// @Produce     json
// @Param       Authorization header string true "Bearer token"
// @Param       id            path   string true "Interview ID"
// @Success     200           {object} map[string]string
// @Failure     401           {object} map[string]string
// @Failure     404           {object} map[string]string
// @Router      /interviews/{id}/audio-ticket [post]
func (h *Handler) Ticket(c *gin.Context) {
	user := middleware.CurrentUser(c)
	id := c.Param("id")
	if _, err := h.interviews.Get(c.Request.Context(), id, user.ID); errors.Is(err, interview.ErrNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "interview not found"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to load interview"})
		return
	}
	ticket, err := h.tickets.Issue(user.ID, id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to issue ticket"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"ticket": ticket})
}

// Stream upgrades to the audio WebSocket. Authentication is a one-time ticket, never the API JWT.
func (h *Handler) Stream(c *gin.Context) {
	ticket := c.Query("ticket")
	if ticket == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "missing ticket"})
		return
	}
	userID, ok := h.tickets.Redeem(ticket, c.Param("id"))
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid or expired ticket"})
		return
	}
	user := middleware.AuthUser{ID: userID}

	id := c.Param("id")

	interviewModel, err := h.interviews.Get(c.Request.Context(), id, user.ID)
	if errors.Is(err, interview.ErrNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "interview not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to load interview"})
		return
	}

	if interviewModel.Status != "in_progress" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "interview is not in progress"})
		return
	}

	if h.aiClient == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "AI service unavailable"})
		return
	}

	options, err := h.startup.Build(c.Request.Context(), interviewModel)
	if errors.Is(err, ErrProfileRequired) {
		c.JSON(http.StatusConflict, gin.H{"error": "complete your candidate profile before starting the interview"})
		return
	}
	if errors.Is(err, ErrInvalidSetup) {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"error": "interview setup is invalid"})
		return
	}
	if err != nil {
		log.Printf("failed to prepare interview startup: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to prepare interview"})
		return
	}

	ws, err := h.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("websocket upgrade failed: %v", err)
		return
	}
	defer ws.Close()
	ws.SetReadLimit(8 * 1024 * 1024)

	streamCtx, cancelStream := context.WithCancel(c.Request.Context())
	defer cancelStream()
	stream, err := h.aiClient.StreamInterview(streamCtx)
	if err != nil {
		log.Printf("failed to open grpc stream: %v", err)
		ws.WriteMessage(websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseInternalServerErr, "AI service unavailable"))
		return
	}
	if err := stream.Send(&aiservicepb.AudioStreamRequest{
		Options: options, TimestampMs: time.Now().UnixMilli(),
	}); err != nil {
		log.Printf("failed to send interview startup: %v", err)
		_ = ws.WriteMessage(websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseInternalServerErr, "AI service unavailable"))
		return
	}

	bridge := NewBridge(ws, stream)
	bridge.onTerminal = func(stage string) error {
		persistCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		return h.interviews.SaveStreamTerminal(persistCtx, interviewModel, stage)
	}
	bridge.Run(cancelStream)
}
