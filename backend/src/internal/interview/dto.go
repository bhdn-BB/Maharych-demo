package interview

import (
	"time"

	"github.com/google/uuid"
)

type StartRequest struct {
	VoiceID  string     `json:"voiceId" binding:"omitempty,oneof=anna sophia daniel alex"`
	Language string     `json:"language" binding:"omitempty,oneof=uk en"`
	Level    string     `json:"level" binding:"required"`
	Position string     `json:"position" binding:"required"`
	Focus    string     `json:"focus" binding:"required"`
	TaskID   *uuid.UUID `json:"taskId" swaggerignore:"true"` // Reject retired task-based starts explicitly.
}

type Response struct {
	VoiceID         string     `json:"voiceId"`
	Language        string     `json:"language"`
	ScenarioVersion int        `json:"scenarioVersion"`
	ID              uuid.UUID  `json:"id"`
	UserID          uint       `json:"userId"`
	Level           string     `json:"level"`
	Position        string     `json:"position"`
	Focus           string     `json:"focus"`
	TaskID          *uuid.UUID `json:"taskId,omitempty"`
	TaskTitle       string     `json:"taskTitle"`
	TaskDescription string     `json:"taskDescription"`
	Status          string     `json:"status"`
	StartedAt       time.Time  `json:"startedAt"`
	EndedAt         *time.Time `json:"endedAt"`
}

type ListResponse struct {
	Items    []Response `json:"items"`
	Page     int        `json:"page"`
	PageSize int        `json:"pageSize"`
	Total    int64      `json:"total"`
}
