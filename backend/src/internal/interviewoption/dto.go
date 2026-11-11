package interviewoption

import "maharych-api/src/internal/model"

type OptionsResponse struct {
	Levels    []model.InterviewOption `json:"levels"`
	Positions []model.InterviewOption `json:"positions"`
	Focuses   []model.InterviewOption `json:"focuses"`
}
