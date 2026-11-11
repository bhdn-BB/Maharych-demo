// mock-ai is a gRPC server that implements AIService.StreamInterview,
// replicating the exact behavior of voice_ai_service for testing.
//
// It follows the same protocol:
//  1. First message must contain startup options → greeting + first topic.
//  2. Subsequent audio chunks are accumulated; every N chunks triggers
//     a mock transcription + evaluation + next question.
//  3. After 5 topics the interview transitions through evaluating → finished
//     with a feedback summary.
//
// Usage:
//
//	go run ./src/cmd/mock-ai            # listens on :50051
//	go run ./src/cmd/mock-ai -addr :9090 # custom port
package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"strings"
	"time"

	"maharych-api/src/internal/genproto/aiservicepb"

	"google.golang.org/grpc"
)

// Interview stages matching voice_ai_service InterviewStage enum.
const (
	stageGreeting    = "greeting"
	stageQuestioning = "questioning"
	stageEvaluating  = "evaluating"
	stageFinished    = "finished"
	totalTopics      = 5
	chunksPerAnswer  = 10 // audio chunks before we treat accumulated data as a complete answer
	delayTranscribe  = 800 * time.Millisecond  // pause before sending transcription
	delayThink       = 2 * time.Second         // pause simulating LLM "thinking"
	delayFeedback    = 3 * time.Second         // pause simulating feedback generation
)

// Mock interview questions per topic (difficulty: basic → advanced).
var mockTopics = [totalTopics]struct {
	question  string
	subTopics []string
}{
	{
		question:  "Tell us about your professional background and what brought you to this field.",
		subTopics: []string{"Key career milestones", "Motivation for this role", "Relevant achievements"},
	},
	{
		question:  "Describe a challenging project you worked on recently. What was your role and how did you handle it?",
		subTopics: []string{"Technical decisions made", "Team collaboration", "Outcomes and lessons learned"},
	},
	{
		question:  "How do you approach system design when starting a new feature or service?",
		subTopics: []string{"Requirements gathering", "Architecture patterns", "Trade-off analysis"},
	},
	{
		question:  "Explain how you handle debugging complex production issues under time pressure.",
		subTopics: []string{"Monitoring and observability", "Root cause analysis", "Incident communication"},
	},
	{
		question:  "If you could redesign a system you've previously worked on, what would you change and why?",
		subTopics: []string{"Scalability improvements", "Technology choices", "Process improvements"},
	},
}

// session holds per-stream interview state.
type session struct {
	candidateName string
	positionTitle string
	grade         string
	department    string
	techStack     []string

	stage      string
	topicIndex int // 0-based, incremented after each accepted answer
	chunkCount int // audio chunks received since last response
}

type mockAIServer struct {
	aiservicepb.UnimplementedAIServiceServer
}

func (s *mockAIServer) StreamInterview(stream grpc.BidiStreamingServer[aiservicepb.AudioStreamRequest, aiservicepb.AudioStreamResponse]) error {
	log.Println("=== new StreamInterview session ===")

	sess := &session{stage: stageGreeting}

	for {
		req, err := stream.Recv()
		if err == io.EOF {
			log.Printf("stream closed by client (topic %d/%d)", sess.topicIndex, totalTopics)
			return nil
		}
		if err != nil {
			log.Printf("recv error: %v", err)
			return err
		}

		// ── First message: initialise session ───────────────────────────
		if req.Options != nil && sess.stage == stageGreeting {
			opts := req.Options

			sess.candidateName = fmt.Sprintf("%s %s", opts.GetCandidate().GetName(), opts.GetCandidate().GetSurname())
			sess.positionTitle = opts.GetPosition().GetTitle()
			sess.grade = gradeString(opts.GetPosition().GetGrade())
			sess.department = opts.GetPosition().GetDepartment()
			sess.techStack = opts.GetPosition().GetRequiredSkills()

			log.Printf("interview started: candidate=%s position=%s grade=%s",
				sess.candidateName, sess.positionTitle, sess.grade)

			sess.stage = stageQuestioning
			sess.topicIndex = 0

			// Stage update (matches interview_servicer.py line 76-81)
			if err := stream.Send(&aiservicepb.AudioStreamResponse{
				Type:            aiservicepb.AudioStreamResponse_STAGE_UPDATE,
				Stage:           stageQuestioning,
				CurrentQuestion: int32(sess.topicIndex),
				TotalQuestions:  totalTopics,
			}); err != nil {
				return err
			}

			// Greeting + first topic (matches interview_servicer.py line 84-87)
			if err := stream.Send(&aiservicepb.AudioStreamResponse{
				Type:   aiservicepb.AudioStreamResponse_AI_TEXT,
				AiText: buildGreeting(sess),
			}); err != nil {
				return err
			}

			log.Printf("  -> sent greeting + topic 1/%d", totalTopics)
			continue
		}

		// ── No options received yet ─────────────────────────────────────
		if sess.stage == stageGreeting {
			_ = stream.Send(&aiservicepb.AudioStreamResponse{
				Type:  aiservicepb.AudioStreamResponse_ERROR,
				Error: "First message must contain startup options",
			})
			return nil
		}

		// ── Audio chunk processing ──────────────────────────────────────
		if len(req.AudioData) == 0 {
			continue
		}

		sess.chunkCount++
		if sess.chunkCount < chunksPerAnswer {
			continue
		}
		sess.chunkCount = 0

		topicNum := sess.topicIndex + 1

		// Simulate STT processing delay
		time.Sleep(delayTranscribe)

		// Transcription
		if err := stream.Send(&aiservicepb.AudioStreamResponse{
			Type:          aiservicepb.AudioStreamResponse_TRANSCRIPTION,
			Transcription: fmt.Sprintf("[Candidate answer for topic %d — transcribed from audio]", topicNum),
		}); err != nil {
			return err
		}

		// Advance to next topic (mock always scores > 70%)
		sess.topicIndex++

		if sess.topicIndex >= totalTopics {
			// ── All topics completed → feedback flow ────────────────────
			if err := sendFinishSequence(stream, sess); err != nil {
				return err
			}
			log.Printf("  -> interview round finished, sent feedback — resetting to topic 1")

			// Reset: loop back to topic 1 so the mock never gets stuck
			sess.topicIndex = 0
			sess.stage = stageQuestioning
			continue
		}

		// Simulate LLM thinking delay
		time.Sleep(delayThink)

		// ── Next topic ──────────────────────────────────────────────────
		if err := stream.Send(&aiservicepb.AudioStreamResponse{
			Type:            aiservicepb.AudioStreamResponse_STAGE_UPDATE,
			Stage:           stageQuestioning,
			CurrentQuestion: int32(sess.topicIndex),
			TotalQuestions:  totalTopics,
		}); err != nil {
			return err
		}

		if err := stream.Send(&aiservicepb.AudioStreamResponse{
			Type:   aiservicepb.AudioStreamResponse_AI_TEXT,
			AiText: "Great answer! Let's move to the next topic. 🚀\n\n" + buildTopicMessage(sess.topicIndex),
		}); err != nil {
			return err
		}

		log.Printf("  -> topic %d/%d answered, sent topic %d", topicNum, totalTopics, sess.topicIndex+1)
	}
}

// sendFinishSequence sends the evaluating → finished → closing → feedback
// message sequence, matching the voice_ai_service flow.
func sendFinishSequence(stream grpc.BidiStreamingServer[aiservicepb.AudioStreamRequest, aiservicepb.AudioStreamResponse], sess *session) error {
	// Stage: evaluating (matches evaluator.py _FINISH_MSG)
	if err := stream.Send(&aiservicepb.AudioStreamResponse{
		Type:            aiservicepb.AudioStreamResponse_STAGE_UPDATE,
		Stage:           stageEvaluating,
		CurrentQuestion: int32(sess.topicIndex),
		TotalQuestions:  totalTopics,
	}); err != nil {
		return err
	}

	// Simulate LLM thinking
	time.Sleep(delayThink)

	if err := stream.Send(&aiservicepb.AudioStreamResponse{
		Type:   aiservicepb.AudioStreamResponse_AI_TEXT,
		AiText: "You've completed all topics! Generating your feedback now... 🎉",
	}); err != nil {
		return err
	}

	// Simulate feedback generation (longer — LLM evaluates all topics)
	time.Sleep(delayFeedback)

	sess.stage = stageFinished

	// Stage: finished
	if err := stream.Send(&aiservicepb.AudioStreamResponse{
		Type:            aiservicepb.AudioStreamResponse_STAGE_UPDATE,
		Stage:           stageFinished,
		CurrentQuestion: int32(sess.topicIndex),
		TotalQuestions:  totalTopics,
	}); err != nil {
		return err
	}

	// Closing message
	time.Sleep(delayThink)
	firstName := strings.SplitN(sess.candidateName, " ", 2)[0]
	if err := stream.Send(&aiservicepb.AudioStreamResponse{
		Type: aiservicepb.AudioStreamResponse_AI_TEXT,
		AiText: fmt.Sprintf(
			"Thank you, %s! 🎉 We've completed the interview. "+
				"Our team will review your results and get back to you shortly. Good luck! 🚀",
			firstName,
		),
	}); err != nil {
		return err
	}

	// Feedback summary (matches interview_servicer.py line 159-165)
	if err := stream.Send(&aiservicepb.AudioStreamResponse{
		Type: aiservicepb.AudioStreamResponse_AI_TEXT,
		AiText: fmt.Sprintf("[FEEDBACK] %s demonstrated solid knowledge across all %d topics "+
			"for the %s %s role. Communication was clear and answers were well-structured. "+
			"Overall score: 7.5/10. Recommendation: consider for next round.",
			firstName, totalTopics, sess.grade, sess.positionTitle,
		),
	}); err != nil {
		return err
	}

	return nil
}

func buildGreeting(sess *session) string {
	firstName := strings.SplitN(sess.candidateName, " ", 2)[0]
	techStr := "your skills"
	if len(sess.techStack) > 0 {
		techStr = strings.Join(sess.techStack, ", ")
	}

	return fmt.Sprintf(
		"Hello, %s! Welcome to the interview for the %s %s position in %s. "+
			"I'll be your AI interviewer today. We'll go through %d topics to assess "+
			"your knowledge and experience with %s. "+
			"Take your time with each answer — there are no trick questions.\n\n"+
			"Let's begin!\n\n%s",
		firstName, sess.grade, sess.positionTitle, sess.department,
		totalTopics, techStr,
		buildTopicMessage(0),
	)
}

func buildTopicMessage(idx int) string {
	t := mockTopics[idx]
	topicNum := idx + 1

	var sb strings.Builder
	fmt.Fprintf(&sb, "**Topic %d of %d**\n\n", topicNum, totalTopics)
	sb.WriteString(t.question)
	sb.WriteString("\n\n*Feel free to also cover:*\n")
	for _, s := range t.subTopics {
		fmt.Fprintf(&sb, "  • %s\n", s)
	}
	return sb.String()
}

func gradeString(g aiservicepb.Grade) string {
	switch g {
	case aiservicepb.Grade_GRADE_INTERN:
		return "intern"
	case aiservicepb.Grade_GRADE_JUNIOR:
		return "junior"
	case aiservicepb.Grade_GRADE_MIDDLE:
		return "middle"
	case aiservicepb.Grade_GRADE_SENIOR:
		return "senior"
	case aiservicepb.Grade_GRADE_LEAD:
		return "lead"
	default:
		return "middle"
	}
}

func main() {
	addr := flag.String("addr", ":50051", "gRPC listen address")
	flag.Parse()

	lis, err := net.Listen("tcp", *addr)
	if err != nil {
		log.Fatalf("failed to listen on %s: %v", *addr, err)
	}

	srv := grpc.NewServer(
		grpc.MaxRecvMsgSize(10*1024*1024),
		grpc.MaxSendMsgSize(10*1024*1024),
	)
	aiservicepb.RegisterAIServiceServer(srv, &mockAIServer{})

	log.Printf("mock AI gRPC server listening on %s", *addr)
	log.Println("waiting for StreamInterview connections...")

	if err := srv.Serve(lis); err != nil {
		log.Fatalf("grpc serve error: %v", err)
	}
}
