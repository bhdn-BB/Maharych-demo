package auth

import (
	"errors"
	"unicode"
	"unicode/utf8"
)

// ErrWeakPassword is returned when a new password violates the sign-up policy.
var ErrWeakPassword = errors.New("password must be 8-72 bytes long and contain an upper-case letter and a digit")

const (
	minPasswordRunes = 8
	// bcrypt rejects inputs longer than 72 bytes; refuse them before hashing.
	maxPasswordBytes = 72
)

// ValidatePassword applies the same rules as the registration form so that the
// API cannot be used to bypass them. It is checked on sign-up only: existing
// accounts keep signing in with whatever password they already have.
func ValidatePassword(password string) error {
	if utf8.RuneCountInString(password) < minPasswordRunes || len(password) > maxPasswordBytes {
		return ErrWeakPassword
	}
	var upper, digit bool
	for _, r := range password {
		upper = upper || unicode.IsUpper(r)
		digit = digit || unicode.IsDigit(r)
	}
	if !upper || !digit {
		return ErrWeakPassword
	}
	return nil
}
