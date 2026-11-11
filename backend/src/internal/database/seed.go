package database

import (
	"log"

	"maharych-api/src/internal/model"

	"gorm.io/gorm"
)

func ptr(s string) *string { return &s }

func Seed(db *gorm.DB) {
	var count int64
	db.Model(&model.InterviewOption{}).Count(&count)
	if count == 0 {
		log.Println("Seeding interview options...")
		options := []model.InterviewOption{
			// Levels
			{Category: "level", Key: "junior", Label: "Junior", Description: ptr("0–2 years experience"), Icon: "Rocket", SortOrder: 0},
			{Category: "level", Key: "middle", Label: "Middle", Description: ptr("2–5 years experience"), Icon: "Code", SortOrder: 1},
			{Category: "level", Key: "senior", Label: "Senior", Description: ptr("5–8 years experience"), Icon: "Brain", SortOrder: 2},
			{Category: "level", Key: "lead", Label: "Lead", Description: ptr("8+ years experience"), Icon: "Cpu", SortOrder: 3},

			// Positions
			{Category: "position", Key: "frontend", Label: "Frontend", Icon: "Monitor", SortOrder: 0},
			{Category: "position", Key: "backend", Label: "Backend", Icon: "Server", SortOrder: 1},
			{Category: "position", Key: "fullstack", Label: "Fullstack", Icon: "Laptop", SortOrder: 2},
			{Category: "position", Key: "devops", Label: "DevOps", Icon: "Globe", SortOrder: 3},
			{Category: "position", Key: "mobile", Label: "Mobile", Icon: "Smartphone", SortOrder: 4},
			{Category: "position", Key: "data", Label: "Data Science", Icon: "Database", SortOrder: 5},

			// Focuses
			{Category: "focus", Key: "algorithms", Label: "Algorithms", Description: ptr("Oral algorithms and time/space complexity"), Icon: "Terminal", SortOrder: 0},
			{Category: "focus", Key: "system-design", Label: "System Design", Description: ptr("CV-based service design, budget and tradeoffs"), Icon: "Target", SortOrder: 1},
		}
		if err := db.Create(&options).Error; err != nil {
			log.Printf("could not seed interview options: %v", err)
		}
	}
	behavioral := model.InterviewOption{Category: "focus", Key: "behavioral", Label: "Behavioral", Description: ptr("Motivation, teamwork and real work experiences"), Icon: "MessageSquare", SortOrder: 2}
	if err := db.Where("category = ? AND key = ?", behavioral.Category, behavioral.Key).FirstOrCreate(&behavioral).Error; err != nil {
		log.Printf("could not seed behavioral interview option: %v", err)
	}
}
