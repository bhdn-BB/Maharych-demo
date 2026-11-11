package interview

import (
	"context"
	"encoding/json"
	"fmt"

	"maharych-api/src/internal/broker"
)

// Finisher asks the AI side to finalize an interview. It only enqueues the request: the
// result comes back asynchronously as an "interview.finished" event (see HandleFinished).
type Finisher interface {
	RequestFinish(ctx context.Context, interviewID string) error
}

type eventPublisher interface {
	Publish(ctx context.Context, key string, body []byte) error
}

// BrokerFinisher publishes finalization requests to RabbitMQ with publisher confirms.
type BrokerFinisher struct{ publisher eventPublisher }

func NewBrokerFinisher(publisher eventPublisher) *BrokerFinisher {
	return &BrokerFinisher{publisher: publisher}
}

// RequestFinish is safe to repeat: the AI consumer finalizes idempotently.
func (f *BrokerFinisher) RequestFinish(ctx context.Context, interviewID string) error {
	body, err := json.Marshal(map[string]string{"interview_id": interviewID})
	if err != nil {
		return fmt.Errorf("encode finish request: %w", err)
	}
	return f.publisher.Publish(ctx, broker.FinishRequestedKey, body)
}
