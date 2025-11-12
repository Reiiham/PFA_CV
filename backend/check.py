import os, json, traceback
from sentence_transformers import SentenceTransformer
from services.quiz_generator import get_embedding  # or import embedding_model

# 1) check env
print("PINECONE_API:", os.getenv("PINECONE_API"))
print("INDEX_URL:", os.getenv("INDEX_URL"))

# 2) test embedding model
try:
    m = SentenceTransformer('BAAI/bge-large-en-v1.5')
    vec = m.encode("python").tolist()
    print("embedding length:", len(vec))
except Exception:
    traceback.print_exc()

# 3) test local embedding helper (if present)
try:
    print("get_embedding('python') -> length:", len(get_embedding("python")))
except Exception:
    traceback.print_exc()

# 4) test Pinecone query (very small)
try:
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API"))
    print("pinecone client ok:", pc is not None)
    index = pc.Index(host=os.getenv("INDEX_URL"))
    print("index object:", type(index))
    q = index.query(namespace="quiz-namespace", vector=[0.0]*1024, top_k=1, include_metadata=True)
    print("query result keys:", q.keys() if isinstance(q, dict) else dir(q))
except Exception:
    traceback.print_exc()

# 5) test Groq client quickly
try:
    from services.groq_client import get_groq_client
    client = get_groq_client()
    r = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"system","content":"Return JSON only."},{"role":"user","content":"{ \"skill_quizzes\": [] }"}], max_tokens=10)
    print("groq ok, got:", r.choices[0].message.content[:200])
except Exception:
    traceback.print_exc()
