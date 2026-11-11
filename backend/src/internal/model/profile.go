package model

import "time"

// Profile stores the candidate context owned by a single user.
type Profile struct {
	UserID            uint     `gorm:"primaryKey"`
	Name              string   `gorm:"not null;size:50"`
	Surname           string   `gorm:"not null;size:50"`
	PhoneNumber       string   `gorm:"not null;size:20"`
	LinkedInURL       string   `gorm:"size:500"`
	GitHubURL         string   `gorm:"size:500"`
	YearsOfExperience int      `gorm:"not null"`
	TechStack         []string `gorm:"serializer:json;type:jsonb;not null"`
	Resume            string   `gorm:"type:text;not null"`
	CreatedAt         time.Time
	UpdatedAt         time.Time
}
