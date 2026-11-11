package model

import (
	"strings"
	"testing"
)

func TestSetPasswordStoresSaltedBcryptHash(t *testing.T) {
	var a, b User
	if err := a.SetPassword("Secret-Password1"); err != nil {
		t.Fatal(err)
	}
	if err := b.SetPassword("Secret-Password1"); err != nil {
		t.Fatal(err)
	}
	if a.Password == "Secret-Password1" || !strings.HasPrefix(a.Password, "$2") {
		t.Fatalf("password must be stored as a bcrypt hash, got %q", a.Password)
	}
	if a.Password == b.Password {
		t.Fatal("equal passwords must produce different hashes (per-hash salt)")
	}
}

func TestCheckPassword(t *testing.T) {
	var u User
	if err := u.SetPassword("Secret-Password1"); err != nil {
		t.Fatal(err)
	}
	for candidate, want := range map[string]bool{
		"Secret-Password1":  true,
		"secret-password1":  false, // case-sensitive
		"Secret-Password1 ": false, // no trimming
		"":                  false,
	} {
		if got := u.CheckPassword(candidate); got != want {
			t.Errorf("CheckPassword(%q) = %v, want %v", candidate, got, want)
		}
	}
}

func TestGoogleOnlyAccountCannotSignInWithPassword(t *testing.T) {
	sub := "google-subject"
	u := User{Email: "g@example.com", GoogleSub: &sub}
	if u.CheckPassword("") || u.CheckPassword("anything") {
		t.Fatal("an account without a password hash must reject every password")
	}
}

func TestSetPasswordRejectsInputBeyondBcryptLimit(t *testing.T) {
	var u User
	if err := u.SetPassword("A1" + strings.Repeat("x", 71)); err == nil {
		t.Fatal("bcrypt input over 72 bytes must fail; callers validate before hashing")
	}
}
