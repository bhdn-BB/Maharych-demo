package middleware

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

const authUserKey = "authUser"

type AuthUser struct {
	ID    uint
	Email string
	Role  string
}

// RequireAdmin must run after AuthRequired; it rejects non-admin users with 403.
func RequireAdmin() gin.HandlerFunc {
	return func(c *gin.Context) {
		if CurrentUser(c).Role != "admin" {
			c.JSON(http.StatusForbidden, gin.H{"error": "admin access required"})
			c.Abort()
			return
		}
		c.Next()
	}
}

func CurrentUser(c *gin.Context) AuthUser {
	return c.MustGet(authUserKey).(AuthUser)
}

func AuthRequired(jwtSecret string) gin.HandlerFunc {
	return func(c *gin.Context) {
		header := c.GetHeader("Authorization")
		if header == "" || !strings.HasPrefix(header, "Bearer ") {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "missing or invalid authorization header"})
			c.Abort()
			return
		}

		tokenString := strings.TrimPrefix(header, "Bearer ")

		user, err := ParseAuthUser(tokenString, jwtSecret)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid token"})
			c.Abort()
			return
		}

		c.Set(authUserKey, user)
		c.Next()
	}
}
