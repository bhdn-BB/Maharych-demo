package interview

import "maharych-api/src/internal/model"

func ToResponse(i *model.Interview) Response {
	return Response{
		VoiceID:         i.VoiceID,
		ID:              i.ID,
		Language:        i.Language,
		ScenarioVersion: i.ScenarioVersion,
		UserID:          i.UserID,
		Level:           i.Level,
		Position:        i.Position,
		Focus:           i.Focus,
		TaskID:          i.TaskID,
		TaskTitle:       i.TaskTitle,
		TaskDescription: i.TaskDescription,
		Status:          i.Status,
		StartedAt:       i.StartedAt,
		EndedAt:         i.EndedAt,
	}
}
