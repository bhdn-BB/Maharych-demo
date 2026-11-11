package audio

import (
	"context"
	"encoding/json"
	"log"
	"sync"
	"time"

	"maharych-api/src/internal/genproto/aiservicepb"

	"github.com/gorilla/websocket"
	"google.golang.org/grpc"
)

// Timing is package-level so tests can shrink it.
var (
	// pongWait is how long the peer may stay silent (no frame and no pong) before the session is dropped.
	pongWait = 60 * time.Second
	// pingInterval must stay below pongWait so a healthy idle client keeps the deadline alive.
	pingInterval = 25 * time.Second
	// writeWait bounds a single WebSocket write so a stalled client cannot block the relay.
	writeWait = 10 * time.Second
	// maxSessionDuration caps one connection, which also releases a hung AI stream.
	maxSessionDuration = 45 * time.Minute
)

type Bridge struct {
	onTerminal func(string) error
	ws         *websocket.Conn
	stream     grpc.BidiStreamingClient[aiservicepb.AudioStreamRequest, aiservicepb.AudioStreamResponse]
	writeMu    sync.Mutex // gorilla/websocket allows one concurrent writer
}

func NewBridge(
	ws *websocket.Conn,
	stream grpc.BidiStreamingClient[aiservicepb.AudioStreamRequest, aiservicepb.AudioStreamResponse],
) *Bridge {
	return &Bridge{ws: ws, stream: stream}
}

// write sends one frame under the writer lock with a bounded deadline.
func (b *Bridge) write(messageType int, data []byte) error {
	b.writeMu.Lock()
	defer b.writeMu.Unlock()
	_ = b.ws.SetWriteDeadline(time.Now().Add(writeWait))
	return b.ws.WriteMessage(messageType, data)
}

// closeWith tells the client why the session ended instead of dropping the TCP connection silently.
func (b *Bridge) closeWith(code int, reason string) {
	_ = b.write(websocket.CloseMessage, websocket.FormatCloseMessage(code, reason))
}

func (b *Bridge) Run(cancelStream context.CancelFunc) {
	_ = b.ws.SetReadDeadline(time.Now().Add(pongWait))
	b.ws.SetPongHandler(func(string) error {
		return b.ws.SetReadDeadline(time.Now().Add(pongWait))
	})

	quit := make(chan struct{})
	defer close(quit)
	go b.keepAlive(quit)
	limit := time.AfterFunc(maxSessionDuration, func() {
		b.closeWith(websocket.CloseNormalClosure, "session time limit reached")
		_ = b.ws.Close()
	})
	defer limit.Stop()

	done := make(chan struct{}, 2)
	go func() {
		b.relayWSToGRPC()
		done <- struct{}{}
	}()
	go func() {
		b.relayGRPCToWS()
		done <- struct{}{}
	}()

	<-done
	_ = b.stream.CloseSend() // half-close before cancelling so the AI side sees a clean end
	cancelStream()
	_ = b.ws.Close()
	<-done
}

// keepAlive pings the client so half-open connections hit the read deadline and release the stream.
func (b *Bridge) keepAlive(quit <-chan struct{}) {
	ticker := time.NewTicker(pingInterval)
	defer ticker.Stop()
	for {
		select {
		case <-quit:
			return
		case <-ticker.C:
			if err := b.write(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

func (b *Bridge) relayWSToGRPC() {
	var pending struct {
		Type       string `json:"type"`
		AnswerID   string `json:"answerId"`
		QuestionID string `json:"questionId"`
	}
	for {
		msgType, data, err := b.ws.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
				log.Printf("ws read error: %v", err)
			}
			return
		}
		_ = b.ws.SetReadDeadline(time.Now().Add(pongWait)) // any client frame proves liveness

		if msgType == websocket.TextMessage {
			if len(data) > 4096 || json.Unmarshal(data, &pending) != nil {
				b.closeWith(websocket.CloseProtocolError, "malformed message")
				return
			}
			if pending.Type == "finish" || pending.Type == "replay_audio" || pending.Type == "start_recording" || pending.Type == "skip_recording" {
				if err := b.stream.Send(&aiservicepb.AudioStreamRequest{Command: pending.Type, QuestionId: pending.QuestionID, AnswerId: pending.AnswerID}); err != nil {
					return
				}
			} else if pending.Type != "answer" {
				b.closeWith(websocket.CloseProtocolError, "unknown message type")
				return
			}
			continue
		}
		if msgType != websocket.BinaryMessage {
			continue
		}

		req := &aiservicepb.AudioStreamRequest{
			AnswerId:    pending.AnswerID,
			QuestionId:  pending.QuestionID,
			AudioData:   data,
			TimestampMs: time.Now().UnixMilli(),
		}
		// One "answer" header authorizes exactly one blob; do not let stale IDs leak into the next frame.
		pending.Type, pending.AnswerID, pending.QuestionID = "", "", ""

		if err := b.stream.Send(req); err != nil {
			log.Printf("grpc send error: %v", err)
			return
		}
	}
}

func (b *Bridge) relayGRPCToWS() {
	for {
		resp, err := b.stream.Recv()
		if err != nil {
			return
		}

		if resp.Type == aiservicepb.AudioStreamResponse_INTERVIEW_FINISHED && b.onTerminal != nil {
			if err := b.onTerminal(resp.Stage); err != nil {
				log.Printf("save final interview status: %v", err)
				b.closeWith(websocket.CloseInternalServerErr, "could not save interview result")
				return
			}
		}

		msg := wsResponse{
			QuestionID: resp.QuestionId, AnswerID: resp.AnswerId, EventID: resp.EventId, AudioMIMEType: resp.AudioMimeType,
			Type:            resp.Type.String(),
			Transcription:   resp.Transcription,
			Text:            resp.AiText,
			Stage:           resp.Stage,
			CurrentQuestion: resp.CurrentQuestion,
			TotalQuestions:  resp.TotalQuestions,
			Error:           resp.Error,
		}

		jsonData, err := json.Marshal(msg)
		if err != nil {
			log.Printf("json marshal error: %v", err)
			continue
		}

		if err := b.write(websocket.TextMessage, jsonData); err != nil {
			log.Printf("ws write text error: %v", err)
			return
		}
		if resp.Type == aiservicepb.AudioStreamResponse_AI_AUDIO {
			if err := b.write(websocket.BinaryMessage, resp.AiAudioData); err != nil {
				return
			}
		}
	}
}
