package admin

import (
	"context"
	"time"

	"maharych-api/src/internal/model"

	"gorm.io/gorm"
)

// QuestionBankRow maps the Python-owned interview_question_bank table.
// The schema is managed by Alembic in voice_ai_service; Go only reads and edits rows.
type QuestionBankRow struct {
	ID         uint   `gorm:"primaryKey" json:"id"`
	Key        string `json:"key"`
	Version    int    `json:"version"`
	Language   string `json:"language"`
	Focus      string `json:"focus"`
	TopicIndex int    `json:"topicIndex"`
	Role       string `json:"role"`
	Level      string `json:"level"`
	Question   string `json:"question"`
	Criteria   string `json:"criteria"`
	SourceURL  string `json:"sourceUrl"`
	Provenance string `json:"provenance"`
	Active     bool   `json:"active"`
}

func (QuestionBankRow) TableName() string { return "interview_question_bank" }

// OutboxRow maps the Python-owned feedback_outbox table.
type OutboxRow struct {
	InterviewID string     `gorm:"primaryKey" json:"interviewId"`
	Published   bool       `json:"published"`
	Attempts    int        `json:"attempts"`
	CreatedAt   time.Time  `json:"createdAt"`
	PublishedAt *time.Time `json:"publishedAt"`
	LastError   *string    `json:"lastError"`
}

func (OutboxRow) TableName() string { return "feedback_outbox" }

type QuestionFilter struct {
	Language string
	Focus    string
	Active   *bool
}

type Repository struct {
	db *gorm.DB
}

func NewRepository(db *gorm.DB) *Repository { return &Repository{db: db} }

// Interview options.

func (r *Repository) ListOptions(ctx context.Context) ([]model.InterviewOption, error) {
	var out []model.InterviewOption
	err := r.db.WithContext(ctx).Order("category, sort_order").Find(&out).Error
	return out, err
}

func (r *Repository) CreateOption(ctx context.Context, o *model.InterviewOption) error {
	return r.db.WithContext(ctx).Create(o).Error
}

func (r *Repository) GetOption(ctx context.Context, id uint) (*model.InterviewOption, error) {
	var o model.InterviewOption
	if err := r.db.WithContext(ctx).First(&o, id).Error; err != nil {
		return nil, err
	}
	return &o, nil
}

func (r *Repository) SaveOption(ctx context.Context, o *model.InterviewOption) error {
	return r.db.WithContext(ctx).Save(o).Error
}

func (r *Repository) DeleteOption(ctx context.Context, id uint) (bool, error) {
	res := r.db.WithContext(ctx).Delete(&model.InterviewOption{}, id)
	return res.RowsAffected > 0, res.Error
}

// Question bank.

func (r *Repository) ListQuestions(ctx context.Context, f QuestionFilter) ([]QuestionBankRow, error) {
	q := r.db.WithContext(ctx).Model(&QuestionBankRow{})
	if f.Language != "" {
		q = q.Where("language = ?", f.Language)
	}
	if f.Focus != "" {
		q = q.Where("focus = ?", f.Focus)
	}
	if f.Active != nil {
		q = q.Where("active = ?", *f.Active)
	}
	var out []QuestionBankRow
	err := q.Order("focus, language, topic_index, key, version DESC").Limit(500).Find(&out).Error
	return out, err
}

func (r *Repository) GetQuestion(ctx context.Context, id uint) (*QuestionBankRow, error) {
	var row QuestionBankRow
	if err := r.db.WithContext(ctx).First(&row, id).Error; err != nil {
		return nil, err
	}
	return &row, nil
}

func (r *Repository) SaveQuestion(ctx context.Context, row *QuestionBankRow) error {
	return r.db.WithContext(ctx).Save(row).Error
}

// NewQuestionVersion copies a row into version max+1 (same key/language) with new text.
func (r *Repository) NewQuestionVersion(ctx context.Context, src *QuestionBankRow, question, criteria string) (*QuestionBankRow, error) {
	var created QuestionBankRow
	err := r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var maxVersion int
		if err := tx.Model(&QuestionBankRow{}).
			Where("key = ? AND language = ?", src.Key, src.Language).
			Select("COALESCE(MAX(version), 0)").Scan(&maxVersion).Error; err != nil {
			return err
		}
		created = *src
		created.ID = 0
		created.Version = maxVersion + 1
		created.Question = question
		created.Criteria = criteria
		created.Provenance = "admin"
		created.Active = true
		return tx.Create(&created).Error
	})
	if err != nil {
		return nil, err
	}
	return &created, nil
}

// Feedback outbox.

func (r *Repository) ListOutbox(ctx context.Context, onlyPending bool) ([]OutboxRow, error) {
	q := r.db.WithContext(ctx).Model(&OutboxRow{})
	if onlyPending {
		q = q.Where("published = ?", false)
	}
	var out []OutboxRow
	err := q.Order("created_at DESC").Limit(200).Find(&out).Error
	return out, err
}

// RetryOutbox makes an entry eligible for republishing by the outbox relay.
func (r *Repository) RetryOutbox(ctx context.Context, interviewID string) (bool, error) {
	res := r.db.WithContext(ctx).Model(&OutboxRow{}).
		Where("interview_id = ?", interviewID).
		Updates(map[string]any{"published": false, "attempts": 0, "published_at": nil, "last_error": nil})
	return res.RowsAffected > 0, res.Error
}
