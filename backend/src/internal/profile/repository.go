package profile

import (
	"context"

	"maharych-api/src/internal/model"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type Repository interface {
	FindByUserID(ctx context.Context, userID uint) (*model.Profile, error)
	Upsert(ctx context.Context, profile *model.Profile) error
}

type repository struct {
	db *gorm.DB
}

func NewRepository(db *gorm.DB) Repository {
	return &repository{db: db}
}

func (r *repository) FindByUserID(ctx context.Context, userID uint) (*model.Profile, error) {
	var profile model.Profile
	if err := r.db.WithContext(ctx).First(&profile, "user_id = ?", userID).Error; err != nil {
		return nil, err
	}
	return &profile, nil
}

func (r *repository) Upsert(ctx context.Context, profile *model.Profile) error {
	return r.db.WithContext(ctx).Clauses(clause.OnConflict{
		Columns: []clause.Column{{Name: "user_id"}},
		DoUpdates: clause.AssignmentColumns([]string{
			"name", "surname", "phone_number", "linked_in_url", "git_hub_url",
			"years_of_experience", "tech_stack", "resume", "updated_at",
		}),
	}).Create(profile).Error
}
