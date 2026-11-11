package interview

import (
	"context"
	"errors"

	"maharych-api/src/internal/model"

	"gorm.io/gorm"
)

// CommandRepository provides persistence needed by state-changing operations.
type CommandRepository interface {
	Create(ctx context.Context, interview *model.Interview) error
	FindByIDAndUser(ctx context.Context, id string, userID uint) (*model.Interview, error)
	FindByID(ctx context.Context, id string) (*model.Interview, error)
	Save(ctx context.Context, interview *model.Interview) error
}

// QueryRepository provides persistence needed by read-only operations.
type QueryRepository interface {
	FindByIDAndUser(ctx context.Context, id string, userID uint) (*model.Interview, error)
	ListByUser(ctx context.Context, userID uint, limit, offset int) ([]model.Interview, int64, error)
}

// Repository combines the interfaces implemented by the database adapter.
type Repository interface {
	CommandRepository
	QueryRepository
}

type repository struct {
	db *gorm.DB
}

func NewRepository(db *gorm.DB) Repository {
	return &repository{db: db}
}

func (r *repository) Create(ctx context.Context, interview *model.Interview) error {
	return r.db.WithContext(ctx).Create(interview).Error
}

func (r *repository) FindByIDAndUser(ctx context.Context, id string, userID uint) (*model.Interview, error) {
	var interview model.Interview
	if err := r.db.WithContext(ctx).Where("id = ? AND user_id = ? AND scenario_version = ?", id, userID, 2).First(&interview).Error; err != nil {
		return nil, translateNotFound(err)
	}
	return &interview, nil
}

// FindByID loads an interview regardless of owner; only for trusted internal events.
func (r *repository) FindByID(ctx context.Context, id string) (*model.Interview, error) {
	var interview model.Interview
	if err := r.db.WithContext(ctx).Where("id = ? AND scenario_version = ?", id, 2).First(&interview).Error; err != nil {
		return nil, translateNotFound(err)
	}
	return &interview, nil
}

// translateNotFound keeps GORM out of the service layer.
func translateNotFound(err error) error {
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return ErrNotFound
	}
	return err
}

func (r *repository) ListByUser(ctx context.Context, userID uint, limit, offset int) ([]model.Interview, int64, error) {
	query := r.db.WithContext(ctx).Model(&model.Interview{}).Where("user_id = ? AND scenario_version = ?", userID, 2)
	var total int64
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}
	var items []model.Interview
	if err := query.Order("started_at DESC").Limit(limit).Offset(offset).Find(&items).Error; err != nil {
		return nil, 0, err
	}
	return items, total, nil
}

func (r *repository) Save(ctx context.Context, interview *model.Interview) error {
	return r.db.WithContext(ctx).Save(interview).Error
}
