from collections import defaultdict
import json
from .groq_client import get_groq_client


BASIC_COURSES = {
    "Python": [
        {"title": "Python for Everybody", "provider": "Coursera", "url": "https://www.coursera.org/specializations/python"},
        {"title": "Automate the Boring Stuff with Python", "provider": "Udemy", "url": "https://www.udemy.com/course/automate/"},
        {"title": "Python Data Science Handbook", "provider": "O'Reilly", "url": "https://www.oreilly.com/library/view/python-data-science/9781491912126/"},
    ],
    "Java": [
        {"title": "Java Programming and Software Engineering Fundamentals", "provider": "Coursera", "url": "https://www.coursera.org/specializations/java-programming"},
        {"title": "Spring Framework Masterclass", "provider": "Udemy", "url": "https://www.udemy.com/course/spring-tutorial-for-beginners/"},
    ],
    "SQL": [
        {"title": "SQL for Data Science", "provider": "Coursera", "url": "https://www.coursera.org/learn/sql-for-data-science"},
        {"title": "Complete SQL Bootcamp", "provider": "Udemy", "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"},
    ],
    "Communication": [
        {"title": "Communication Skills for Engineers", "provider": "Coursera", "url": "https://www.coursera.org/learn/communication-skills-engineers"},
        {"title": "Business Communication", "provider": "edX", "url": "https://www.edx.org/course/business-communication"},
    ],
    "Teamwork": [
        {"title": "Teamwork Skills: Communicating Effectively in Groups", "provider": "Coursera", "url": "https://www.coursera.org/learn/teamwork-skills"},
        {"title": "Collaborative Leadership", "provider": "LinkedIn Learning", "url": "https://www.linkedin.com/learning/collaborative-leadership"},
    ],
    "Problem Solving": [
        {"title": "Critical Thinking & Problem-Solving", "provider": "edX", "url": "https://www.edx.org/course/critical-thinking-problem-solving"},
        {"title": "Problem Solving Techniques", "provider": "Coursera", "url": "https://www.coursera.org/learn/problem-solving-techniques"},
    ],
    "Critical Thinking": [
        {"title": "Critical Thinking at Work", "provider": "LinkedIn Learning", "url": "https://www.linkedin.com/learning/critical-thinking-at-work"},
        {"title": "Logical and Critical Thinking", "provider": "FutureLearn", "url": "https://www.futurelearn.com/courses/logical-and-critical-thinking"},
    ],
    "Leadership": [
        {"title": "Leadership Principles", "provider": "Coursera", "url": "https://www.coursera.org/learn/leadership-principles"},
        {"title": "Strategic Leadership", "provider": "edX", "url": "https://www.edx.org/course/strategic-leadership"},
    ],
    "Project Management": [
        {"title": "Project Management Principles", "provider": "Coursera", "url": "https://www.coursera.org/learn/project-management-principles"},
        {"title": "Agile Project Management", "provider": "Udemy", "url": "https://www.udemy.com/course/agile-project-management/"},
    ],
}


LEVEL_TO_PRIORITY = {
    "beginner": 3,
    "intermediate": 2,
    "advanced": 1,
}


# ============ GROQ AI RECOMMENDATIONS ============

RECOMMENDATION_PROMPT = """Based on the user's skill assessment, generate personalized learning recommendations.

User Profile:
- Skill: {skill}
- Current Level: {level}
- Quiz Performance: {performance}
- Weakness: {weakness}

Generate 3-5 highly relevant learning resources (courses, tutorials, books, or documentation) that would help improve this specific skill. Focus on addressing the identified weaknesses.

Return ONLY valid JSON in this exact format:
{{
  "resources": [
    {{
      "title": "Resource Title",
      "provider": "Platform/Publisher Name",
      "type": "course|tutorial|book|documentation",
      "url": "https://example.com/resource",
      "why": "Brief explanation of why this resource is recommended (1-2 sentences)",
      "difficulty": "beginner|intermediate|advanced"
    }}
  ]
}}

Important:
- Recommend real, existing resources only
- Mix different types (courses, books, tutorials, docs)
- Prioritize FREE or affordable resources
- Be specific about what makes each resource valuable
- Match difficulty to user's current level and growth path
"""


def generate_ai_recommendations(skill: str, level: str, performance: str, weakness: str) -> list:
    """
    Use Groq AI to generate personalized course/resource recommendations
    """
    client = get_groq_client()
    
    prompt = RECOMMENDATION_PROMPT.format(
        skill=skill,
        level=level,
        performance=performance,
        weakness=weakness or "General improvement needed"
    )
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are an expert learning advisor. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500,
            stream=False,
        )
        
        response_text = completion.choices[0].message.content.strip()
        print(f"[recommender] AI response for {skill}: {response_text[:200]}...")
        
        # Parse JSON response
        data = json.loads(response_text)
        resources = data.get("resources", [])
        
        # Add source indicator
        for resource in resources:
            resource["source"] = "AI-Generated"
        
        return resources[:5]  # Limit to 5 resources
        
    except json.JSONDecodeError as e:
        print(f"[recommender] JSON parse error for {skill}: {e}")
        return []
    except Exception as e:
        print(f"[recommender] AI generation error for {skill}: {e}")
        return []


def _why_for_resource(skill: str, resource: dict, weakness_hint: str | None) -> str:
    """Generate explanation for why a resource is recommended"""
    hints = []
    if weakness_hint:
        hints.append(weakness_hint)
    if resource.get("provider"):
        hints.append(f"structured guidance from {resource['provider']}")
    if "Python" in skill and "Automate" in resource.get("title", ""):
        hints.append("focus on hands-on projects to consolidate fundamentals")
    reason = ", ".join(hints) if hints else "addresses knowledge gaps with targeted content"
    return f"Recommended for {skill}: {reason}."


def recommend_courses(skills: dict, grading: dict, use_ai: bool = True) -> dict:
    """
    Generate personalized learning recommendations based on skills and quiz performance
    
    Args:
        skills: User's extracted skills with levels
        grading: Quiz grading results with corrections
        use_ai: Whether to use AI-generated recommendations (default: True)
    """
    print(f"[recommender] Input skills: {skills}")
    print(f"[recommender] Input grading: {grading}")
    print(f"[recommender] AI recommendations: {'ENABLED' if use_ai else 'DISABLED'}")
    
    low_skills = defaultdict(float)
    details = {}
    skill_levels = {}

    # Process quiz results to identify weak areas
    for c in grading.get("corrections", []):
        skill = c.get("skill")
        score = c.get("score", 0)
        if not skill:
            continue
        low_skills[skill] += (5 - score)
        if score <= 2:
            details[skill] = f"weak performance on '{c.get('question','')[:60]}'"

    # Process extracted skills to add priority based on level
    extracted = []
    for key in ["technical_skills", "soft_skills", "cognitive_skills"]:
        extracted.extend(skills.get(key, []))

    for s in extracted:
        name = s.get("name")
        lvl = s.get("level", "intermediate").lower()
        skill_levels[name] = lvl
        # Add priority based on skill level (beginner gets higher priority)
        low_skills[name] += LEVEL_TO_PRIORITY.get(lvl, 2)

    print(f"[recommender] Low skills identified: {dict(low_skills)}")

    recommendations = []
    # Sort by priority and take top 5
    sorted_skills = sorted(low_skills.items(), key=lambda x: x[1], reverse=True)[:5]
    
    for skill_name, priority in sorted_skills:
        # Get static courses
        static_courses = BASIC_COURSES.get(skill_name, [])
        
        # Get AI-generated recommendations if enabled
        ai_resources = []
        if use_ai:
            level = skill_levels.get(skill_name, "intermediate")
            performance = f"Priority score: {priority:.1f}"
            weakness = details.get(skill_name, "")
            
            ai_resources = generate_ai_recommendations(
                skill=skill_name,
                level=level,
                performance=performance,
                weakness=weakness
            )
        
        # Combine resources
        all_resources = []
        
        # Add static courses first (with source indicator)
        for c in static_courses[:2]:  # Take top 2 static
            all_resources.append({
                **c,
                "source": "Curated",
                "type": "course",
                "difficulty": skill_levels.get(skill_name, "intermediate"),
                "why": _why_for_resource(skill_name, c, details.get(skill_name))
            })
        
        # Add AI recommendations
        all_resources.extend(ai_resources)
        
        # If we have no resources at all
        if not all_resources:
            print(f"[recommender] No resources found for skill: {skill_name}")
            # Generate AI recommendations as fallback
            if use_ai:
                ai_resources = generate_ai_recommendations(
                    skill=skill_name,
                    level="intermediate",
                    performance=f"Priority: {priority}",
                    weakness="General skill development needed"
                )
                all_resources.extend(ai_resources)
        
        if all_resources:
            recommendations.append({
                "skill": skill_name,
                "priority": priority,
                "current_level": skill_levels.get(skill_name, "unknown"),
                "resources": all_resources[:5]  # Limit to 5 total resources
            })

    print(f"[recommender] Generated {len(recommendations)} recommendations with {sum(len(r['resources']) for r in recommendations)} total resources")

    return {
        "recommendations": recommendations,
        "overall_score": grading.get("overall_score", 0),
        "cognitive_score": grading.get("cognitive_score", 0),
    }