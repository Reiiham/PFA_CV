import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.services.recommender import recommend_courses
import json
# Mock data
skills = {
    "technical_skills": [
        {"name": "Python", "level": "intermediate"},
        {"name": "Java", "level": "beginner"}
    ],
    "soft_skills": [
        {"name": "Leadership", "level": "advanced"}
    ]
}

grading = {
    "corrections": [
        {
            "skill": "Python",
            "question": "What is list comprehension?",
            "score": 2,
            "feedback": "Needs improvement"
        },
        {
            "skill": "Java",
            "question": "Explain polymorphism",
            "score": 0,
            "feedback": "Incorrect answer"
        }
    ],
    "overall_score": 35.0,
    "cognitive_score": 40.0
}

# Test with AI
print("=" * 60)
print("Testing with AI recommendations")
print("=" * 60)
result = recommend_courses(skills, grading, use_ai=True)
print(json.dumps(result, indent=2))

# Test without AI (fallback to static only)
print("\n" + "=" * 60)
print("Testing without AI (static only)")
print("=" * 60)
result = recommend_courses(skills, grading, use_ai=False)
print(json.dumps(result, indent=2))