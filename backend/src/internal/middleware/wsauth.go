package middleware

import (
	"strconv"

	"github.com/golang-jwt/jwt/v5"
)

// ParseAuthUser converts an API token into the identity used by both transports.
func ParseAuthUser(tokenString, secret string) (AuthUser, error) {
	claims, err := ParseJWTClaims(tokenString, secret)
	if err != nil {
		return AuthUser{}, err
	}
	sub, _ := claims["sub"].(string)
	uid, err := strconv.ParseUint(sub, 10, 64)
	if err != nil {
		return AuthUser{}, err
	}
	email, _ := claims["email"].(string)
	role, _ := claims["role"].(string)
	return AuthUser{ID: uint(uid), Email: email, Role: role}, nil
}

func ParseJWTClaims(tokenString, secret string) (jwt.MapClaims, error) {
	token, err := jwt.Parse(tokenString, func(t *jwt.Token) (any, error) {
		return []byte(secret), nil
	}, jwt.WithValidMethods([]string{jwt.SigningMethodHS256.Alg()}), jwt.WithExpirationRequired())
	if err != nil || !token.Valid {
		return nil, jwt.ErrSignatureInvalid
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return nil, jwt.ErrSignatureInvalid
	}

	return claims, nil
}
