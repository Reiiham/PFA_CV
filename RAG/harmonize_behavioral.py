import json

# Charger ton fichier annoté
with open("behavioral_questions_annotated.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Harmonisation
harmonized = []
for idx, item in enumerate(data, start=201):
    harmonized.append({
        "id": idx,
        "question": item.get("question"),
        "answer": None,
        "category": "Behavioral",
        "difficulty": item.get("difficulty"),
        "bloom_level": item.get("bloom_level"),
        "source": "behavioral"
    })

# Sauvegarde
with open("behavioral_questions_harmonized.json", "w", encoding="utf-8") as f:
    json.dump(harmonized, f, indent=4, ensure_ascii=False)

print("✅ behavioral_questions_harmonized.json généré !")
