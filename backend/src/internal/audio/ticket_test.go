package audio

import (
	"testing"
	"time"
)

func TestTicketIsSingleUse(t *testing.T) {
	store := NewTicketStore()
	ticket, err := store.Issue(7, "iv-1")
	if err != nil {
		t.Fatal(err)
	}
	if uid, ok := store.Redeem(ticket, "iv-1"); !ok || uid != 7 {
		t.Fatalf("first redeem = %d, %v", uid, ok)
	}
	if _, ok := store.Redeem(ticket, "iv-1"); ok {
		t.Fatal("ticket must not be reusable")
	}
}

func TestTicketRejectsOtherInterviewAndConsumesIt(t *testing.T) {
	store := NewTicketStore()
	ticket, _ := store.Issue(7, "iv-1")
	if _, ok := store.Redeem(ticket, "iv-2"); ok {
		t.Fatal("ticket is bound to its interview")
	}
	if _, ok := store.Redeem(ticket, "iv-1"); ok {
		t.Fatal("a failed redeem must still burn the ticket")
	}
}

func TestTicketExpires(t *testing.T) {
	store := NewTicketStore()
	now := time.Now()
	store.now = func() time.Time { return now }
	ticket, _ := store.Issue(7, "iv-1")
	store.now = func() time.Time { return now.Add(ticketTTL + time.Second) }
	if _, ok := store.Redeem(ticket, "iv-1"); ok {
		t.Fatal("expired ticket must be rejected")
	}
	if _, ok := store.Redeem("unknown", "iv-1"); ok {
		t.Fatal("unknown ticket must be rejected")
	}
}
