package audio

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"maharych-api/src/internal/genproto/aiservicepb"

	"github.com/gorilla/websocket"
	"google.golang.org/grpc"
)

type fakeStream struct {
	grpc.ClientStream
	mu     sync.Mutex
	sent   []*aiservicepb.AudioStreamRequest
	recv   chan *aiservicepb.AudioStreamResponse
	closed chan struct{}
	once   sync.Once
}

func newFakeStream() *fakeStream {
	return &fakeStream{recv: make(chan *aiservicepb.AudioStreamResponse, 8), closed: make(chan struct{})}
}

func (f *fakeStream) Send(r *aiservicepb.AudioStreamRequest) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.sent = append(f.sent, r)
	return nil
}
func (f *fakeStream) Recv() (*aiservicepb.AudioStreamResponse, error) {
	select {
	case r := <-f.recv:
		return r, nil
	case <-f.closed:
		return nil, errors.New("stream cancelled")
	}
}
func (f *fakeStream) CloseSend() error { return nil }
func (f *fakeStream) cancel()          { f.once.Do(func() { close(f.closed) }) }
func (f *fakeStream) sentCopy() []*aiservicepb.AudioStreamRequest {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]*aiservicepb.AudioStreamRequest(nil), f.sent...)
}

// startBridge serves one bridged connection and returns the client end plus a channel closed when Run exits.
func startBridge(t *testing.T, stream *fakeStream) (*websocket.Conn, <-chan struct{}) {
	t.Helper()
	finished := make(chan struct{})
	upgrader := websocket.Upgrader{}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ws, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer ws.Close()
		NewBridge(ws, stream).Run(stream.cancel)
		close(finished)
	}))
	t.Cleanup(srv.Close)
	client, _, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(srv.URL, "http"), nil)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { client.Close() })
	return client, finished
}

func waitFor(t *testing.T, ch <-chan struct{}, what string) {
	t.Helper()
	select {
	case <-ch:
	case <-time.After(3 * time.Second):
		t.Fatalf("timed out waiting for %s", what)
	}
}

func TestBridgeClosesWithProtocolErrorOnUnknownMessage(t *testing.T) {
	stream := newFakeStream()
	client, finished := startBridge(t, stream)
	if err := client.WriteMessage(websocket.TextMessage, []byte(`{"type":"nope"}`)); err != nil {
		t.Fatal(err)
	}
	_, _, err := client.ReadMessage()
	var closeErr *websocket.CloseError
	if !errors.As(err, &closeErr) || closeErr.Code != websocket.CloseProtocolError {
		t.Fatalf("want protocol-error close frame, got %v", err)
	}
	waitFor(t, finished, "bridge shutdown")
}

func TestBridgeDoesNotReuseAnswerIDForLaterBlobs(t *testing.T) {
	stream := newFakeStream()
	client, _ := startBridge(t, stream)
	_ = client.WriteMessage(websocket.TextMessage, []byte(`{"type":"answer","answerId":"a1","questionId":"q1"}`))
	_ = client.WriteMessage(websocket.BinaryMessage, []byte("first"))
	_ = client.WriteMessage(websocket.BinaryMessage, []byte("second"))
	deadline := time.Now().Add(3 * time.Second)
	for len(stream.sentCopy()) < 2 && time.Now().Before(deadline) {
		time.Sleep(10 * time.Millisecond)
	}
	sent := stream.sentCopy()
	if len(sent) != 2 || sent[0].AnswerId != "a1" || sent[1].AnswerId != "" {
		t.Fatalf("stale answer id leaked: %+v", sent)
	}
}

func TestBridgeDropsSilentPeerAndReleasesStream(t *testing.T) {
	old := pongWait
	pongWait = 200 * time.Millisecond
	t.Cleanup(func() { pongWait = old })

	stream := newFakeStream()
	_, finished := startBridge(t, stream) // the client never reads, so it never answers pings or sends frames
	waitFor(t, finished, "read deadline to end the session")
	select {
	case <-stream.closed:
	default:
		t.Fatal("gRPC stream was not cancelled")
	}
}

func TestBridgeForwardsAIEventsToClient(t *testing.T) {
	stream := newFakeStream()
	client, _ := startBridge(t, stream)
	stream.recv <- &aiservicepb.AudioStreamResponse{Type: aiservicepb.AudioStreamResponse_AI_TEXT, AiText: "hello"}
	_ = client.SetReadDeadline(time.Now().Add(3 * time.Second))
	_, data, err := client.ReadMessage()
	if err != nil || !strings.Contains(string(data), "hello") {
		t.Fatalf("got %q err=%v", data, err)
	}
	_ = context.Background
}
