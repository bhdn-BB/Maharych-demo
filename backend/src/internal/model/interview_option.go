package model

import "gorm.io/gorm"

// IsSupportedInterviewFocus reports whether a new oral interview supports this focus.
func IsSupportedInterviewFocus(key string) bool {
	return key == "algorithms" || key == "system-design" || key == "behavioral"
}

type InterviewOption struct {
	gorm.Model
	Category    string  `gorm:"not null;size:20;index" json:"category"`
	Key         string  `gorm:"not null;size:30" json:"key"`
	Label       string  `gorm:"not null;size:50" json:"label"`
	Description *string `gorm:"size:100" json:"description,omitempty"`
	Icon        string  `gorm:"not null;size:30" json:"icon"`
	SortOrder   int     `gorm:"not null;default:0" json:"sortOrder"`
}
