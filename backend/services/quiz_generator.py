
import json
from typing import List, Dict, Any
from .groq_client import get_groq_client
from pinecone import Pinecone
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

# ---------------- CONFIG ----------------
PINECONE_API_KEY = os.getenv("PINECONE_API")
INDEX_HOST = os.getenv("INDEX_URL")
NAMESPACE = "quiz-namespace"

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=INDEX_HOST)

# ✅ Initialiser le modèle d'embedding (1024 dimensions)
# Ce modèle est téléchargé une fois et utilisé localement (gratuit)
print("[quiz_generator_rag] Loading embedding model...")
embedding_model = SentenceTransformer('BAAI/bge-large-en-v1.5')
print("[quiz_generator_rag] ✅ Embedding model loaded")

# ---------------- PROMPT TEMPLATE ----------------
QUIZ_PROMPT_TEMPLATE = """Generate quiz questions for these skills using the provided context from the knowledge base. Return JSON only.

Context:
{context}

Format:
{{
  "skill_quizzes": [
    {{
      "skill": "Python",
      "questions": [
        {{
          "type": "MCQ",
          "bloom_level": "Apply",
          "question": "What does print() do in Python?",
          "options": ["Displays text", "Calculates math", "Creates variables", "Imports modules"],
          "correct_option_index": 0
        }},
        {{
          "type": "CODING", 
          "bloom_level": "Apply",
          "question": "Write a function to add two numbers"
        }}
      ]
    }}
  ]
}}

Skills: {categorized}
"""

# ---------------- EMBEDDING FUNCTION ----------------
def get_embedding(text: str) -> List[float]:
    """
    Generate embedding using SentenceTransformer (local, free, 1024 dimensions)
    """
    try:
        # Générer l'embedding localement (pas d'API)
        embedding = embedding_model.encode(text).tolist()
        return embedding
    except Exception as e:
        print(f"[get_embedding] Error for text '{text[:50]}...': {e}")
        return None


# ---------------- RAG SEARCH ----------------
def retrieve_context(skills: List[str], top_k: int = 5) -> str:
    """
    Search Pinecone for relevant records using local embeddings
    """
    all_context = []
    
    for skill in skills:
        try:
            # ✅ Générer l'embedding localement (gratuit)
            query_vector = get_embedding(skill)
            
            if query_vector is None:
                print(f"[retrieve_context] Failed to get embedding for '{skill}'")
                continue
            
            # Vérifier la dimension
            if len(query_vector) != 1024:
                print(f"[retrieve_context] ⚠️ Warning: Vector dimension is {len(query_vector)}, expected 1024")
            
            # ✅ Query Pinecone avec le vecteur
            query_results = index.query(
                namespace=NAMESPACE,
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )
            
            matches = query_results.get('matches', [])
            print(f"[retrieve_context] Found {len(matches)} results for skill '{skill}'")
            
            for match in matches:
                context_piece = match.get('metadata', {}).get("text", "")
                score = match.get('score', 0)
                if context_piece and score > 0.3:  # Filtrer les résultats peu pertinents
                    all_context.append(f"- {context_piece}")
                    
        except Exception as e:
            print(f"[retrieve_context] Error querying for skill '{skill}': {e}")
            continue

    context = "\n".join(all_context) if all_context else "No specific context found in the knowledge base."
    print(f"[retrieve_context] Total context items: {len(all_context)}")
    print(f"[retrieve_context] Total context length: {len(context)} characters")
    return context


# ---------------- QUIZ GENERATION WITH RAG ----------------
def generate_quiz_for_skills(categorized_skills: Dict[str, List[str]], num_questions_per_skill: int = 2, config: Dict[str, Any] | None = None) -> dict:
    """
    Generate quiz questions based on skills using RAG (Retrieval-Augmented Generation)
    Uses local SentenceTransformer for embeddings (free, no API needed)
    """
    client = get_groq_client()

    # Limit skills per category to avoid token overflow
    limited_skills = {}
    for category, skills in categorized_skills.items():
        limited_skills[category] = skills[:2]

    print(f"[generate_quiz] Limited skills: {limited_skills}")

    # ✅ Retrieve context using RAG with local embeddings
    all_skills = [skill for skills in limited_skills.values() for skill in skills]
    context = retrieve_context(all_skills)

    prompt = QUIZ_PROMPT_TEMPLATE.format(
        context=context,
        categorized=json.dumps(limited_skills, ensure_ascii=False)
    )

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "Always output strict JSON only. Generate questions based on the provided context."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=4000,
            stream=False,
        )
        response_text = completion.choices[0].message.content.strip()
        print(f"[quiz_generator_rag] raw response length: {len(response_text)}")
        print(f"[quiz_generator_rag] raw response preview: {response_text[:500]}")
    except Exception as e:
        print(f"[quiz_generator_rag] Groq API error: {e}")
        response_text = '{"skill_quizzes": []}'

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"[quiz_generator_rag] JSON parse error: {e}")
        data = {"skill_quizzes": []}

    # Add time limits
    for skill_quiz in data.get("skill_quizzes", []):
        for question in skill_quiz.get("questions", []):
            if question.get("type") == "MCQ":
                question["time_limit_sec"] = 60
            elif question.get("type") == "CODING":
                question["time_limit_sec"] = 300
            else:
                question["time_limit_sec"] = 120

    return data