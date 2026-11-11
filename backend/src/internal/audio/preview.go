package audio

import (
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// PreviewHandler proxies a fixed voice sample from the private speech service.
// @Summary Preview an interviewer voice
// @Tags voices
// @Produce audio/mpeg
// @Param Authorization header string true "Bearer token"
// @Param voice path string true "Voice: anna, sophia, daniel or alex"
// @Param language query string true "Language: uk or en"
// @Success 200 {file} file
// @Failure 400 {object} map[string]string
// @Failure 502 {object} map[string]string
// @Router /voices/{voice}/preview [get]
func PreviewHandler(baseURL string) gin.HandlerFunc {
	client := &http.Client{Timeout: 75 * time.Second}
	return func(c *gin.Context) {
		voice, language := c.Param("voice"), c.Query("language")
		switch voice {
		case "anna", "sophia", "daniel", "alex":
		default:
			c.JSON(http.StatusBadRequest, gin.H{"error": "Unsupported voice"})
			return
		}
		if language != "uk" && language != "en" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Unsupported language"})
			return
		}
		target := strings.TrimRight(baseURL, "/") + "/api/v1/voices/" + voice + "/preview?language=" + url.QueryEscape(language)
		req, err := http.NewRequestWithContext(c.Request.Context(), http.MethodGet, target, nil)
		if err != nil {
			c.JSON(http.StatusBadGateway, gin.H{"error": "Voice preview unavailable"})
			return
		}
		resp, err := client.Do(req)
		if err != nil {
			c.JSON(http.StatusBadGateway, gin.H{"error": "Voice preview unavailable"})
			return
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			c.JSON(http.StatusBadGateway, gin.H{"error": "Voice preview unavailable"})
			return
		}
		body, err := io.ReadAll(io.LimitReader(resp.Body, 16*1024*1024+1))
		if err != nil || len(body) == 0 || len(body) > 16*1024*1024 {
			c.JSON(http.StatusBadGateway, gin.H{"error": "Voice preview unavailable"})
			return
		}
		c.Header("Cache-Control", "no-store")
		c.Data(http.StatusOK, "audio/mpeg", body)
	}
}
