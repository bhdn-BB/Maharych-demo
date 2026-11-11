package database

import (
	"fmt"

	"maharych-api/src/internal/model"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func Connect(dsn string) (*gorm.DB, error) {
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}
	return db, nil
}

func Migrate(db *gorm.DB) error {
	if err := db.AutoMigrate(&model.User{}); err != nil {
		return fmt.Errorf("migrate users: %w", err)
	}
	// Preserve existing account IDs while allowing multiple password-only users.
	if err := db.Exec("UPDATE users SET google_sub = NULL WHERE google_sub = ''").Error; err != nil {
		return fmt.Errorf("normalize legacy Google subjects: %w", err)
	}
	return db.AutoMigrate(&model.InterviewOption{}, &model.InterviewTask{}, &model.Interview{}, &model.Profile{})
}
