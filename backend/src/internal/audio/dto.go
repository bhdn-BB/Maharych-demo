package audio

type wsResponse struct {
	QuestionID      string `json:"questionId,omitempty"`
	AnswerID        string `json:"answerId,omitempty"`
	EventID         string `json:"eventId,omitempty"`
	AudioMIMEType   string `json:"audioMimeType,omitempty"`
	Type            string `json:"type"`
	Transcription   string `json:"transcription,omitempty"`
	Text            string `json:"text,omitempty"`
	Stage           string `json:"stage,omitempty"`
	CurrentQuestion int32  `json:"currentQuestion,omitempty"`
	TotalQuestions  int32  `json:"totalQuestions,omitempty"`
	Error           string `json:"error,omitempty"`
}
