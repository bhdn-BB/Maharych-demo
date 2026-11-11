package profile

import "maharych-api/src/internal/model"

func toResponse(p *model.Profile) Response {
	return Response{
		Name:              p.Name,
		Surname:           p.Surname,
		PhoneNumber:       p.PhoneNumber,
		LinkedInURL:       p.LinkedInURL,
		GitHubURL:         p.GitHubURL,
		YearsOfExperience: p.YearsOfExperience,
		TechStack:         p.TechStack,
		Resume:            p.Resume,
	}
}
