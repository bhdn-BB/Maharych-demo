package interviewoption

import (
	"context"

	"maharych-api/src/internal/model"

	"gorm.io/gorm"
)

type Repository interface {
	FindAllOrdered(ctx context.Context) ([]model.InterviewOption, error)
	FindByCategoryAndKey(ctx context.Context, category, key string) (*model.InterviewOption, error)
}

type repository struct {
	db *gorm.DB
}

func NewRepository(db *gorm.DB) Repository {
	return &repository{db: db}
}

func (r *repository) FindAllOrdered(ctx context.Context) ([]model.InterviewOption, error) {
	var options []model.InterviewOption
	if err := r.db.WithContext(ctx).Order("category, sort_order").Find(&options).Error; err != nil {
		return nil, err
	}
	return options, nil
}

func (r *repository) FindByCategoryAndKey(ctx context.Context, category, key string) (*model.InterviewOption, error) {
	var option model.InterviewOption
	if err := r.db.WithContext(ctx).Where("category = ? AND key = ?", category, key).First(&option).Error; err != nil {
		return nil, err
	}
	return &option, nil
}
