package model

import (
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

const (
	RoleUser  = "user"
	RoleAdmin = "admin"
)

type User struct {
	gorm.Model
	Role         string  `gorm:"not null;default:'user';size:20" json:"-"`
	Email        string  `gorm:"uniqueIndex;not null;size:255" json:"email"`
	Password     string  `gorm:"size:255" json:"-"`
	AuthProvider string  `gorm:"not null;default:'credentials';size:50" json:"-"`
	GoogleSub    *string `gorm:"uniqueIndex;size:255" json:"-"`
}

func (u *User) SetPassword(plain string) error {
	hash, err := bcrypt.GenerateFromPassword([]byte(plain), bcrypt.DefaultCost)
	if err != nil {
		return err
	}
	u.Password = string(hash)
	return nil
}

func (u *User) CheckPassword(plain string) bool {
	if u.Password == "" {
		return false
	}
	return bcrypt.CompareHashAndPassword([]byte(u.Password), []byte(plain)) == nil
}
