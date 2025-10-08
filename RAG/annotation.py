import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from backend.services.groq_client import get_groq_client
import logging
import json
from typing import List

# Config logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def annotate_questions_with_metadata(questions: List[str], client) -> List[dict]:
    """
    Envoie chaque question à Groq et ajoute bloom_level + difficulty.
    :param questions: Liste de questions
    :param client: ton groq_client déjà configuré
    :return: Liste de dicts annotés
    """
    results = []

    total = len(questions)
    logging.info(f"Début de l'annotation de {total} questions...")

    for idx, question in enumerate(questions, start=1):
        try:
            logging.info(f"[{idx}/{total}] Traitement de la question : {question[:50]}...")

            prompt = f"""
            You are an assistant that tags questions.
            For the following question, return a JSON with fields:
            - bloom_level: one of [Remember, Understand, Apply, Analyze, Evaluate, Create]
            - difficulty: one of [easy, medium, hard]
            
            Question: "{question}"
            """

            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1042,
                response_format={"type": "json_object"}
            )

            raw_output = response.choices[0].message.content  

            # Parser le JSON renvoyé
            parsed = json.loads(raw_output)
            parsed["question"] = question
            results.append(parsed)

            logging.info(f"✅ Question {idx} annotée : {parsed}")

        except Exception as e:
            logging.error(f"❌ Erreur sur la question {idx}: {e}")
            results.append({
                "question": question,
                "bloom_level": None,
                "difficulty": None,
                "error": str(e)
            })

    logging.info("✅ Annotation terminée")
    return results
