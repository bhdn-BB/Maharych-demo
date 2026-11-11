package model

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type Interview struct {
	VoiceID                string         `gorm:"size:20" json:"voiceId"`
	Language               string         `gorm:"size:2" json:"language"`
	ScenarioVersion        int            `gorm:"not null;default:0" json:"scenarioVersion"`
	ID                     uuid.UUID      `gorm:"type:uuid;default:gen_random_uuid();primaryKey" json:"id"`
	CreatedAt              time.Time      `json:"-"`
	UpdatedAt              time.Time      `json:"-"`
	DeletedAt              gorm.DeletedAt `gorm:"index" json:"-"`
	UserID                 uint           `gorm:"not null;index" json:"userId"`
	Level                  string         `gorm:"not null;size:20" json:"level"`
	Position               string         `gorm:"not null;size:20" json:"position"`
	Focus                  string         `gorm:"not null;size:30" json:"focus"`
	TaskID                 *uuid.UUID     `gorm:"type:uuid;index" json:"taskId,omitempty"`
	TaskTitle              string         `gorm:"size:120" json:"taskTitle"`
	TaskDescription        string         `gorm:"type:text" json:"taskDescription"`
	TaskEvaluationCriteria string         `gorm:"type:text" json:"-"`
	Status                 string         `gorm:"not null;size:20;default:in_progress" json:"status"`
	StartedAt              time.Time      `gorm:"not null" json:"startedAt"`
	EndedAt                *time.Time     `json:"endedAt"`
}

func (i *Interview) BeforeCreate(tx *gorm.DB) error {
	if i.ID == uuid.Nil {
		i.ID = uuid.New()
	}
	return nil
}
