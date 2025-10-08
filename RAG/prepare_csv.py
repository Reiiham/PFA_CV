import os
import sys
import json
import pandas as pd
import logging
from groq_client import get_groq_client

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Config logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def annotate_questions_with_metadata(questions, client):
    results = []
    total = len(questions)
    logging.info(f"Début de l'annotation technique pour {total} questions...")

    for idx, row in enumerate(questions, start=1):
        question_text = row["Question"]
        difficulty = row.get("Difficulty", "medium").lower()
        category = row.get("Category", "General Programming")

        logging.info(f"[{idx}/{total}] Traitement : {question_text[:50]}...")

        try:
            # Prompt pour obtenir le bloom_level
            prompt = f"""
            You are an assistant that tags technical interview questions.
            For the following question, return a JSON with fields:
            - bloom_level: one of [Remember, Understand, Apply, Analyze, Evaluate, Create]

            Question: "{question_text}"
            """

            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200,
                response_format={"type": "json_object"}
            )

            raw_output = response.choices[0].message.content if hasattr(response.choices[0].message, "content") else response.choices[0].message["content"]
            parsed = json.loads(raw_output)

            results.append({
                "id": idx,
                "question": question_text,
                "answer": row.get("Answer", ""),
                "category": category,
                "difficulty": difficulty,
                "bloom_level": parsed.get("bloom_level", "Understand"),
                "source": "technical"
            })

            logging.info(f"✅ Question {idx} annotée : {parsed.get('bloom_level', 'Understand')}")

        except Exception as e:
            logging.error(f"❌ Erreur question {idx}: {e}")
            results.append({
                "id": idx,
                "question": question_text,
                "answer": row.get("Answer", ""),
                "category": category,
                "difficulty": difficulty,
                "bloom_level": None,
                "source": "technical",
                "error": str(e)
            })

    logging.info("✅ Annotation technique terminée")
    return results


if __name__ == "__main__":
    client = get_groq_client()
    df = pd.read_csv("Software Questions.csv", encoding="latin1")

    annotated = annotate_questions_with_metadata(df.to_dict(orient="records"), client)

    with open("technical_questions_annotated.json", "w", encoding="utf-8") as f:
        json.dump(annotated, f, indent=4, ensure_ascii=False)
