package audio

import (
	"crypto/rand"
	"encoding/base64"
	"sync"
	"time"
)

// ticketTTL is how long a freshly issued WebSocket ticket can be redeemed.
const ticketTTL = 30 * time.Second

type ticketEntry struct {
	userID      uint
	interviewID string
	expires     time.Time
}

// TicketStore issues short-lived, single-use tickets that authorize one WebSocket
// handshake, so the long-lived API JWT never appears in a URL, proxy log or history.
type TicketStore struct {
	mu      sync.Mutex
	tickets map[string]ticketEntry
	now     func() time.Time
}

func NewTicketStore() *TicketStore {
	return &TicketStore{tickets: make(map[string]ticketEntry), now: time.Now}
}

// Issue returns an unguessable ticket bound to one user and one interview.
func (s *TicketStore) Issue(userID uint, interviewID string) (string, error) {
	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		return "", err
	}
	ticket := base64.RawURLEncoding.EncodeToString(raw)
	s.mu.Lock()
	defer s.mu.Unlock()
	now := s.now()
	for key, entry := range s.tickets { // opportunistic cleanup keeps the map bounded
		if now.After(entry.expires) {
			delete(s.tickets, key)
		}
	}
	s.tickets[ticket] = ticketEntry{userID: userID, interviewID: interviewID, expires: now.Add(ticketTTL)}
	return ticket, nil
}

// Redeem consumes the ticket; it succeeds at most once and only for the bound interview.
func (s *TicketStore) Redeem(ticket, interviewID string) (uint, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	entry, ok := s.tickets[ticket]
	if !ok {
		return 0, false
	}
	delete(s.tickets, ticket)
	if s.now().After(entry.expires) || entry.interviewID != interviewID {
		return 0, false
	}
	return entry.userID, true
}
