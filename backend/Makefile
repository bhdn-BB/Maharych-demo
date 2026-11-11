.PHONY: build run swagger tidy test clean proto proto-deps

APP_NAME := maharych-api
BUILD_DIR := bin
PROTO_DIR := ../proto
PROTO_OUT := src/internal/genproto

build:
	go build -o $(BUILD_DIR)/$(APP_NAME) ./src/cmd/server

run:
	go run ./src/cmd/server

swagger:
	swag init -g src/cmd/server/main.go -o docs --parseDependency --parseInternal

tidy:
	go mod tidy

test:
	go test ./...

clean:
	rm -rf $(BUILD_DIR)

proto-deps:
	@which protoc > /dev/null || (echo "protoc not found, install protobuf compiler" && exit 1)
	@which protoc-gen-go > /dev/null || go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
	@which protoc-gen-go-grpc > /dev/null || go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

proto: proto-deps
	@mkdir -p $(PROTO_OUT)/aiservicepb
	protoc \
		--proto_path=$(PROTO_DIR) \
		--go_out=$(PROTO_OUT)/aiservicepb --go_opt=module=maharych-api/src/internal/genproto/aiservicepb \
		--go-grpc_out=$(PROTO_OUT)/aiservicepb --go-grpc_opt=module=maharych-api/src/internal/genproto/aiservicepb \
		$(PROTO_DIR)/ai_service/v1/ai_service.proto
