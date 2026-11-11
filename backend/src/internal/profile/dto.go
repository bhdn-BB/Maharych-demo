package profile

type PutRequest struct {
	Name              string   `json:"name"`
	Surname           string   `json:"surname"`
	PhoneNumber       string   `json:"phoneNumber"`
	LinkedInURL       string   `json:"linkedinUrl"`
	GitHubURL         string   `json:"githubUrl"`
	YearsOfExperience *int     `json:"yearsOfExperience"`
	TechStack         []string `json:"techStack"`
	Resume            string   `json:"resume"`
}

type Response struct {
	Name              string   `json:"name"`
	Surname           string   `json:"surname"`
	PhoneNumber       string   `json:"phoneNumber"`
	LinkedInURL       string   `json:"linkedinUrl"`
	GitHubURL         string   `json:"githubUrl"`
	YearsOfExperience int      `json:"yearsOfExperience"`
	TechStack         []string `json:"techStack"`
	Resume            string   `json:"resume"`
}
