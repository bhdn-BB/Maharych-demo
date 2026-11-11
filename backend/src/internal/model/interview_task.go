package model

import (
	"github.com/google/uuid"
	"gorm.io/gorm"
)

// InterviewTask is a reusable task from the system catalog or a user's library.
type InterviewTask struct {
	ID                 uuid.UUID      `gorm:"type:uuid;primaryKey" json:"id"`
	OwnerID            *uint          `gorm:"index" json:"ownerId,omitempty"`
	Focus              string         `gorm:"not null;size:30;index" json:"focus"`
	Title              string         `gorm:"not null;size:120" json:"title"`
	Description        string         `gorm:"type:text;not null" json:"description"`
	EvaluationCriteria string         `gorm:"type:text;not null" json:"-"`
	Active             bool           `gorm:"not null" json:"active"`
	SortOrder          int            `gorm:"not null;default:0" json:"sortOrder"`
	DeletedAt          gorm.DeletedAt `gorm:"index" json:"-"`
}

func (task *InterviewTask) BeforeCreate(*gorm.DB) error {
	if task.ID == uuid.Nil {
		task.ID = uuid.New()
	}
	return nil
}
