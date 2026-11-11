package auth

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	svc *Service
}

func NewHandler(svc *Service) *Handler {
	return &Handler{svc: svc}
}

// Register godoc
// @Summary     Register a new user
// @Description Creates a new user account with email and password
// @Tags        auth
// @Accept      json
// @Produce     json
// @Param       body body     AuthRequest true "Registration credentials"
// @Success     201  {object} AuthResponse
// @Failure     400  {object} map[string]string
// @Failure     409  {object} map[string]string
// @Router      /auth/register [post]
func (h *Handler) Register(c *gin.Context) {
	var req AuthRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid email or password"})
		return
	}

	user, token, err := h.svc.Register(c.Request.Context(), req.Email, req.Password)
	if err != nil {
		if errors.Is(err, ErrWeakPassword) {
			c.JSON(http.StatusBadRequest, gin.H{"error": ErrWeakPassword.Error()})
			return
		}
		if errors.Is(err, ErrEmailAlreadyRegistered) {
			c.JSON(http.StatusConflict, gin.H{"error": "email already registered"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create user"})
		return
	}

	c.JSON(http.StatusCreated, AuthResponse{
		User:  UserResponse{ID: user.ID, Email: user.Email, Role: user.Role},
		Token: token,
	})
}

// Login godoc
// @Summary     Login
// @Description Authenticates a user with email and password
// @Tags        auth
// @Accept      json
// @Produce     json
// @Param       body body     AuthRequest true "Login credentials"
// @Success     200  {object} AuthResponse
// @Failure     400  {object} map[string]string
// @Failure     401  {object} map[string]string
// @Router      /auth/login [post]
func (h *Handler) Login(c *gin.Context) {
	var req AuthRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid email or password"})
		return
	}

	user, token, err := h.svc.Login(c.Request.Context(), req.Email, req.Password)
	if err != nil {
		if errors.Is(err, ErrInvalidCredentials) {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid credentials"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate token"})
		return
	}

	c.JSON(http.StatusOK, AuthResponse{
		User:  UserResponse{ID: user.ID, Email: user.Email, Role: user.Role},
		Token: token,
	})
}

// GoogleAuth godoc
// @Summary     Authenticate with Google
// @Description Verifies a Google ID token and returns a backend JWT. Creates the user if new, or links to an existing account by email.
// @Tags        auth
// @Accept      json
// @Produce     json
// @Param       body body     GoogleAuthRequest true "Google ID token"
// @Success     200  {object} AuthResponse
// @Failure     400  {object} map[string]string
// @Failure     401  {object} map[string]string
// @Failure     503  {object} map[string]string
// @Router      /auth/google [post]
func (h *Handler) GoogleAuth(c *gin.Context) {
	var req GoogleAuthRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "id_token is required"})
		return
	}

	user, token, err := h.svc.GoogleAuth(c.Request.Context(), req.IDToken)
	if err != nil {
		if errors.Is(err, ErrGoogleDisabled) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": err.Error()})
			return
		}
		if errors.Is(err, ErrInvalidGoogleToken) || errors.Is(err, ErrInvalidTokenClaims) || errors.Is(err, ErrEmailNotVerified) {
			c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to authenticate"})
		return
	}

	c.JSON(http.StatusOK, AuthResponse{
		User:  UserResponse{ID: user.ID, Email: user.Email, Role: user.Role},
		Token: token,
	})
}
