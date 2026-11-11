// Package broker is the Go side of the RabbitMQ topology shared with voice_ai_service.
package broker

import (
	"context"
	"errors"
	"fmt"
	"log"
	"sync"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
)

// Topology shared with voice_ai_service/.../services/interview_events.py (keep in sync).
const (
	EventsExchange     = "maharych.events"
	FinishRequestedKey = "interview.finish.requested"
	FinishedKey        = "interview.finished"
)

const publishTimeout = 10 * time.Second

// ErrUnroutable means the broker accepted the message but no queue was bound for its key.
var ErrUnroutable = errors.New("broker: message was not routed to any queue")

// Client owns one lazily (re)established AMQP connection.
type Client struct {
	url  string
	mu   sync.Mutex
	conn *amqp.Connection
}

func New(url string) *Client { return &Client{url: url} }

func (c *Client) connection() (*amqp.Connection, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.conn != nil && !c.conn.IsClosed() {
		return c.conn, nil
	}
	conn, err := amqp.DialConfig(c.url, amqp.Config{Dial: amqp.DefaultDial(10 * time.Second), Heartbeat: 10 * time.Second})
	if err != nil {
		return nil, fmt.Errorf("connect to broker: %w", err)
	}
	c.conn = conn
	return conn, nil
}

func declareExchange(ch *amqp.Channel) error {
	return ch.ExchangeDeclare(EventsExchange, "direct", true, false, false, false, nil)
}

// Close releases the connection.
func (c *Client) Close() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.conn != nil {
		_ = c.conn.Close()
	}
}

// Publish sends a persistent message and returns only after the broker confirmed it was
// accepted and routed to at least one queue.
func (c *Client) Publish(ctx context.Context, key string, body []byte) error {
	conn, err := c.connection()
	if err != nil {
		return err
	}
	ch, err := conn.Channel()
	if err != nil {
		return fmt.Errorf("open channel: %w", err)
	}
	defer ch.Close()
	if err := declareExchange(ch); err != nil {
		return fmt.Errorf("declare exchange: %w", err)
	}
	if err := ch.Confirm(false); err != nil {
		return fmt.Errorf("enable confirms: %w", err)
	}
	returned := ch.NotifyReturn(make(chan amqp.Return, 1))
	confirms := ch.NotifyPublish(make(chan amqp.Confirmation, 1))

	ctx, cancel := context.WithTimeout(ctx, publishTimeout)
	defer cancel()
	if err := ch.PublishWithContext(ctx, EventsExchange, key, true, false, amqp.Publishing{
		ContentType: "application/json", DeliveryMode: amqp.Persistent, Body: body,
	}); err != nil {
		return fmt.Errorf("publish: %w", err)
	}
	select {
	case <-returned: // mandatory message with no bound queue
		return ErrUnroutable
	case confirmation := <-confirms:
		select {
		case <-returned: // basic.return is delivered before the confirm
			return ErrUnroutable
		default:
		}
		if !confirmation.Ack {
			return errors.New("broker rejected the message")
		}
		return nil
	case <-ctx.Done():
		return fmt.Errorf("await broker confirmation: %w", ctx.Err())
	}
}

// Consume binds a durable queue to key and calls handle for every message until ctx ends,
// reconnecting with backoff. A handler error requeues the message after a short pause;
// ErrDiscard drops a message that can never succeed.
func (c *Client) Consume(ctx context.Context, queue, key string, handle func(context.Context, []byte) error) {
	backoff := time.Second
	for ctx.Err() == nil {
		err := c.consumeOnce(ctx, queue, key, handle)
		if ctx.Err() != nil {
			return
		}
		log.Printf("broker consumer %s stopped: %v; retrying in %s", queue, err, backoff)
		select {
		case <-ctx.Done():
			return
		case <-time.After(backoff):
		}
		if backoff < 30*time.Second {
			backoff *= 2
		}
	}
}

// ErrDiscard marks a message as permanently unprocessable (e.g. malformed JSON).
var ErrDiscard = errors.New("broker: discard message")

func (c *Client) consumeOnce(ctx context.Context, queue, key string, handle func(context.Context, []byte) error) error {
	conn, err := c.connection()
	if err != nil {
		return err
	}
	ch, err := conn.Channel()
	if err != nil {
		return err
	}
	defer ch.Close()
	if err := declareExchange(ch); err != nil {
		return err
	}
	if _, err := ch.QueueDeclare(queue, true, false, false, false, nil); err != nil {
		return err
	}
	if err := ch.QueueBind(queue, key, EventsExchange, false, nil); err != nil {
		return err
	}
	if err := ch.Qos(1, 0, false); err != nil {
		return err
	}
	deliveries, err := ch.Consume(queue, "", false, false, false, false, nil)
	if err != nil {
		return err
	}
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case d, ok := <-deliveries:
			if !ok {
				return errors.New("delivery channel closed")
			}
			switch err := handle(ctx, d.Body); {
			case err == nil:
				_ = d.Ack(false)
			case errors.Is(err, ErrDiscard):
				log.Printf("broker: discarding message on %s: %v", queue, err)
				_ = d.Reject(false)
			default:
				log.Printf("broker: handler failed on %s, requeueing: %v", queue, err)
				select {
				case <-ctx.Done():
				case <-time.After(2 * time.Second):
				}
				_ = d.Nack(false, true)
			}
		}
	}
}
