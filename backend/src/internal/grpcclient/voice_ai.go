package grpcclient

import (
	"fmt"

	"maharych-api/src/internal/genproto/aiservicepb"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func Connect(addr string) (aiservicepb.AIServiceClient, func(), error) {
	conn, err := grpc.NewClient(addr, grpc.WithTransportCredentials(insecure.NewCredentials()), grpc.WithDefaultCallOptions(grpc.MaxCallRecvMsgSize(10<<20), grpc.MaxCallSendMsgSize(10<<20)))
	if err != nil {
		return nil, nil, fmt.Errorf("failed to connect to AI service: %w", err)
	}

	client := aiservicepb.NewAIServiceClient(conn)
	closer := func() { conn.Close() }
	return client, closer, nil
}
