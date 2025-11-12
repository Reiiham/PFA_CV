# services/recommender.py
from collections import defaultdict
import json
import re
from .groq_client import get_groq_client

# recommander.py

# LEVEL_TO_PRIORITY = {"beginner": 3, "intermediate": 2, "advanced": 1}

# RECOMMENDATION_PROMPT = (
#     "You are a career development assistant AI.\n"
#     "Suggest 3 short, concrete learning resources for the given skill.\n"
#     "Return ONLY valid JSON, in this format:\n"
#     "{\n"
#     "  \"recommendations\": [\n"
#     "    {\n"
#     "      \"title\": \"Course or resource name\",\n"
#     "      \"description\": \"Brief explanation (1 sentence)\",\n"
#     "      \"platform\": \"Coursera / Udemy / YouTube / etc.\",\n"
#     "      \"difficulty\": \"beginner / intermediate / advanced\"\n"
#     "    }\n"
#     "  ]\n"
#     "}\n\n"
#     "Skill: {skill}\n"
#     "Performance: {performance}\n"
#     "Weakness: {weakness}\n"
# )

# # --- helpers for robust JSON parsing (improved) ---
# def _safe_load_json(s: str) -> dict:
#     """
#     Try to parse JSON robustly:
#       1) direct json.loads
#       2) extract first {...} object block and try to json.loads after conservative cleanup
#       3) extract a top-level "recommendations": [...] fragment and wrap into {"recommendations": ...}
#     Returns parsed dict or {} if nothing usable.
#     """
#     if not s:
#         return {}
#     s = s.strip()
#     # 1) direct
#     try:
#         return json.loads(s)
#     except json.JSONDecodeError:
#         pass

#     # 2) find first {...} block
#     start = s.find("{")
#     end = s.rfind("}")
#     if start != -1 and end != -1 and end > start:
#         candidate = s[start:end+1]
#         cand2 = re.sub(r",\s*}", "}", candidate)
#         cand2 = re.sub(r",\s*\]", "]", cand2)
#         try:
#             return json.loads(cand2)
#         except json.JSONDecodeError:
#             pass

#     # 3) try to find a "recommendations": [ ... ] fragment and wrap it
#     # use a non-greedy match for the array content, DOTALL so newlines allowed
#     arr_match = re.search(r'"recommendations"\s*:\s*(\[\s*(?:\{.*?\}\s*,?\s*)+\])', s, flags=re.DOTALL)
#     if arr_match:
#         arr_text = arr_match.group(1)
#         wrapped = "{" + f'"recommendations": {arr_text}' + "}"
#         # cleanup trailing commas conservatively
#         wrapped = re.sub(r",\s*}", "}", wrapped)
#         wrapped = re.sub(r",\s*\]", "]", wrapped)
#         try:
#             return json.loads(wrapped)
#         except json.JSONDecodeError:
#             # attempt a looser heuristic: try to extract between the first [ and the matching ]
#             try:
#                 first_br = s.index("[", arr_match.start(1))
#                 # find matching closing bracket by scanning
#                 depth = 0
#                 for i in range(first_br, len(s)):
#                     if s[i] == "[":
#                         depth += 1
#                     elif s[i] == "]":
#                         depth -= 1
#                         if depth == 0:
#                             last_br = i
#                             break
#                 arr2 = s[first_br:last_br+1]
#                 wrapped2 = "{" + f'"recommendations": {arr2}' + "}"
#                 wrapped2 = re.sub(r",\s*}", "}", wrapped2)
#                 wrapped2 = re.sub(r",\s*\]", "]", wrapped2)
#                 return json.loads(wrapped2)
#             except Exception:
#                 pass

#     # nothing parsed
#     return {}

# def get_groq():
#     if not hasattr(get_groq, "client"):
#         print("[recommender] Initializing Groq client...")
#         get_groq.client = get_groq_client()
#         print("[recommender] ✅ Groq client ready")
#     return get_groq.client

# def generate_ai_recommendations(skill: str, performance: str, weakness: str, max_retries: int = 1) -> list:
#     """
#     Ask the LLM to produce recommendations for a skill.
#     Returns a list of recommendation dicts (may be empty).
#     """
#     client = get_groq()

#     # ⚙️ safe replacement instead of .format()
#     prompt = (
#         RECOMMENDATION_PROMPT
#         .replace("{skill}", skill)
#         .replace("{performance}", performance)
#         .replace("{weakness}", weakness)
#     )

#     attempt = 0
#     while attempt <= max_retries:
#         attempt += 1
#         try:
#             completion = client.chat.completions.create(
#                 model="openai/gpt-oss-20b",
#                 messages=[
#                     {"role": "system", "content": "Always return valid JSON only."},
#                     {"role": "user", "content": prompt},
#                 ],
#                 temperature=0.3,
#                 max_tokens=1200,
#                 stream=False,
#             )
#             response = completion.choices[0].message.content.strip()
#             print(f"[recommender] Raw LLM response (skill={skill}, attempt={attempt}):")
#             print(response[:1500])

#             data = _safe_load_json(response)
#             if not data:
#                 print(f"[recommender] _safe_load_json could not parse response for skill={skill} on attempt {attempt}")
#                 continue

#             recs = data.get("recommendations") or data.get("resources") or data.get("items") or []
#             if isinstance(recs, dict):
#                 for v in recs.values():
#                     if isinstance(v, list):
#                         recs = v
#                         break

#             if not isinstance(recs, list):
#                 recs = []

#             normalized = []
#             for r in recs:
#                 if not isinstance(r, dict):
#                     continue
#                 title = r.get("title") or r.get("name") or r.get("course") or "Untitled"
#                 description = r.get("description") or r.get("desc") or ""
#                 platform = r.get("platform") or r.get("source") or "Unknown"
#                 difficulty = r.get("difficulty") or r.get("level") or "intermediate"
#                 normalized.append({
#                     "title": title,
#                     "description": description,
#                     "platform": platform,
#                     "difficulty": difficulty
#                 })
#                 if len(normalized) >= 3:
#                     break

#             if normalized:
#                 return normalized
#             else:
#                 print(f"[recommender] No usable recs parsed for skill={skill} on attempt {attempt}")
#                 continue

#         except Exception as e:
#             print(f"[recommender] ⚠️ AI recommendation error (skill={skill}, attempt={attempt}): {e}")
#             continue

#     return []


# def recommend_courses(skills_data, grading, use_ai=True):
#     """Generate skill-based learning recommendations."""
#     try:
#         recommendations = []

#         overall_score = grading.get("overall_score", None) if isinstance(grading, dict) else None

#         for category, skills in skills_data.items():
#             for skill_obj in skills:
#                 if isinstance(skill_obj, dict):
#                     skill = skill_obj.get("name")
#                     level = (skill_obj.get("level") or "").lower()
#                 else:
#                     skill = skill_obj
#                     level = ""

#                 # priority logic could use LEVEL_TO_PRIORITY + grading (simple mapping here)
#                 if overall_score is None:
#                     priority = "medium"
#                 else:
#                     priority = "low" if overall_score > 80 else "medium" if overall_score > 60 else "high"

#                 # 🔥 Generate AI recs only if use_ai=True
#                 ai_recs = []
#                 if use_ai:
#                     ai_recs = generate_ai_recommendations(skill, f"priority={priority}", "weak area", max_retries=1)

#                 resources = ai_recs if ai_recs else [
#                     {"title": "No AI recommendations", "description": "AI not available or returned no results.", "platform": "N/A", "difficulty": "N/A"}
#                 ]

#                 recommendations.append({
#                     "skill": skill,
#                     "level": level,
#                     "priority": priority,
#                     "resources": resources
#                 })

#         print("[recommender] ✅ Recommendations assembled")
#         return recommendations

#     except Exception as e:
#         print(f"[recommender] ⚠️ Fallback mode triggered due to: {e}")
#         # 🩹 fallback recommendations
#         fallback = [
#             {
#                 "skill": "General Improvement",
#                 "resources": [
#                     {
#                         "title": "Learn with Coursera",
#                         "description": "Explore top online courses.",
#                         "platform": "Coursera",
#                         "difficulty": "beginner"
#                     }
#                 ]
#             }
#         ]
#         return fallback

# services/recommender.py
import json
import re
from .groq_client import get_groq_client

LEVEL_TO_PRIORITY = {"beginner": 3, "intermediate": 2, "advanced": 1}

RECOMMENDATION_PROMPT = (
    "You are a career development assistant AI.\n"
    "Suggest up to 3 short, concrete learning resources for the given skill.\n"
    "Return ONLY valid JSON, in this format:\n"
    "{\n"
    "  \"recommendations\": [\n"
    "    {\n"
    "      \"title\": \"Course or resource name\",\n"
    "      \"description\": \"Brief explanation (1 sentence)\",\n"
    "      \"platform\": \"Coursera / Udemy / YouTube / etc.\",\n"
    "      \"difficulty\": \"beginner / intermediate / advanced\"\n"
    "    }\n"
    "  ]\n"
    "}\n\n"
    "Skill: {skill}\n"
    "Performance: {performance}\n"
    "Weakness: {weakness}\n"
)

def _safe_load_json(s: str) -> dict:
    if not s:
        return {}
    s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = s[start:end+1]
        cand2 = re.sub(r",\s*}", "}", candidate)
        cand2 = re.sub(r",\s*\]", "]", cand2)
        try:
            return json.loads(cand2)
        except json.JSONDecodeError:
            pass
    # try to capture "recommendations": [ ... ] fragment
    arr_match = re.search(r'"recommendations"\s*:\s*(\[[\s\S]*\])', s)
    if arr_match:
        try:
            wrapped = "{" + f'"recommendations": {arr_match.group(1)}' + "}"
            wrapped = re.sub(r",\s*}", "}", wrapped)
            wrapped = re.sub(r",\s*\]", "]", wrapped)
            return json.loads(wrapped)
        except Exception:
            pass
    return {}

def get_groq():
    if not hasattr(get_groq, "client"):
        print("[recommender] Initializing Groq client...")
        get_groq.client = get_groq_client()
        print("[recommender] ✅ Groq client ready")
    return get_groq.client

def generate_ai_recommendations(skill: str, performance: str, weakness: str, max_retries: int = 1) -> list:
    client = get_groq()
    prompt = RECOMMENDATION_PROMPT.replace("{skill}", skill).replace("{performance}", performance).replace("{weakness}", weakness)
    attempt = 0
    while attempt <= max_retries:
        attempt += 1
        try:
            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "Always return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1200,
                stream=False,
            )
            response = completion.choices[0].message.content.strip()
            print(f"[recommender] Raw LLM response (skill={skill}, attempt={attempt}):")
            print(response[:1500])
            data = _safe_load_json(response)
            if not data:
                print(f"[recommender] _safe_load_json could not parse response for skill={skill} on attempt {attempt}")
                continue
            recs = data.get("recommendations") or []
            if not isinstance(recs, list):
                recs = []
            normalized = []
            for r in recs:
                if not isinstance(r, dict):
                    continue
                normalized.append({
                    "title": r.get("title") or r.get("name") or "Untitled",
                    "description": r.get("description") or r.get("desc") or "",
                    "platform": r.get("platform") or r.get("source") or "Unknown",
                    "difficulty": r.get("difficulty") or r.get("level") or "intermediate"
                })
                if len(normalized) >= 3:
                    break
            if normalized:
                return normalized
            else:
                continue
        except Exception as e:
            print(f"[recommender] ⚠️ AI recommendation error (skill={skill}, attempt={attempt}): {e}")
            continue
    return []

def recommend_courses(skills_data, grading, use_ai=True, max_total=7):
    """
    skills_data: same as before (dict of categories -> list of skills)
    grading: dict with overall_score => used to compute priority
    Returns a list of up to max_total recommendation objects:
      {skill, priority, title, description, platform, difficulty}
    """
    try:
        overall_score = grading.get("overall_score") if isinstance(grading, dict) else None
        flat_recs = []  # will hold dicts with skill + priority + resource

        for category, skills in skills_data.items():
            for skill_obj in skills:
                if isinstance(skill_obj, dict):
                    skill = skill_obj.get("name")
                    level = (skill_obj.get("level") or "").lower()
                else:
                    skill = skill_obj
                    level = ""
                if overall_score is None:
                    priority_label = "medium"
                else:
                    priority_label = "low" if overall_score > 80 else "medium" if overall_score > 60 else "high"
                priority_score = {"high": 3, "medium": 2, "low": 1}.get(priority_label, 2)

                ai_recs = []
                if use_ai and skill:
                    ai_recs = generate_ai_recommendations(skill, f"priority={priority_label}", "weak area", max_retries=1)
                resources = ai_recs if ai_recs else [{"title":"No AI recommendations","description":"AI not available","platform":"N/A","difficulty":"N/A"}]

                # flatten: keep up to 3 resources per skill but tag each with skill and priority_score
                for res in resources[:3]:
                    flat_recs.append({
                        "skill": skill,
                        "level": level,
                        "priority_label": priority_label,
                        "priority_score": priority_score,
                        "title": res.get("title"),
                        "description": res.get("description"),
                        "platform": res.get("platform"),
                        "difficulty": res.get("difficulty")
                    })

        # sort flattened recs by priority_score desc (higher priority first), then keep first max_total unique entries
        flat_recs.sort(key=lambda r: (-r["priority_score"], r["skill"] or ""))
        # optionally dedupe by title
        seen_titles = set()
        final = []
        for r in flat_recs:
            t = (r["title"] or "").strip()
            if t in seen_titles:
                continue
            final.append(r)
            seen_titles.add(t)
            if len(final) >= max_total:
                break

        print(f"[recommender] ✅ Recommendations assembled (total={len(final)})")
        return final

    except Exception as e:
        print(f"[recommender] ⚠️ Fallback mode triggered due to: {e}")
        return []

