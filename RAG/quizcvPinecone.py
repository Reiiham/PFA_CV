import json
import os
from pinecone import Pinecone
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# --- CONFIG ---
load_dotenv()
#Using local embedding model (bge-large-en-v1.5, 1024 dims)
PINECONE_API_KEY = os.getenv("PINECONE_API")
INDEX_HOST = os.getenv("INDEX_URL")   
NAMESPACE = "quiz-namespace"

# --- INIT ---
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=INDEX_HOST)

# ✅ Load local embedding model (bge-large-en-v1.5, 1024 dims)
print("[indexer] Loading local embedding model...")
embedding_model = SentenceTransformer("BAAI/bge-large-en-v1.5")
print("[indexer] ✅ Model loaded successfully")

# --- LOAD FILES ---
with open("technical_questions_annotated.json", "r", encoding="utf-8") as f:
    technical = json.load(f)

with open("behavioral_questions_harmonized.json", "r", encoding="utf-8") as f:
    behavioral = json.load(f)

all_data = technical + behavioral
print(f"📥 Loaded {len(all_data)} total questions")

# --- PREPARE RECORDS ---
records = []
for item in all_data:
    chunk_text = item["question"]
    if item.get("answer"):
        chunk_text += " " + item["answer"]

    records.append({
        "id": str(item["id"]),
        "text": chunk_text,
        "category": str(item.get("category", "")) or "unknown",
        "difficulty": str(item.get("difficulty", "")) or "unknown",
        "bloom_level": str(item.get("bloom_level", "")) or "unknown",
        "source": str(item.get("source", "")) or "unknown"
    })

print(f"⚙️ Preparing {len(records)} records for embedding and upload...")

# --- UPSERT IN BATCHES ---
BATCH_SIZE = 64  # Ajuste si tu veux

def chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

total_uploaded = 0

for batch in chunked(records, BATCH_SIZE):
    # ✅ Générer embeddings localement
    texts = [r["text"] for r in batch]
    embeddings = embedding_model.encode(texts).tolist()

    vectors = []
    for i, record in enumerate(batch):
        vectors.append({
            "id": record["id"],
            "values": embeddings[i],
            "metadata": {
                "text": record["text"],
                "category": record["category"],
                "difficulty": record["difficulty"],
                "bloom_level": record["bloom_level"],
                "source": record["source"]
            }
        })

    # ✅ Envoyer à Pinecone
    index.upsert(vectors=vectors, namespace=NAMESPACE)
    total_uploaded += len(batch)
    print(f"✅ Uploaded batch of {len(batch)} records (Total: {total_uploaded})")

print(f"🎉 Finished uploading {total_uploaded} records into Pinecone (namespace='{NAMESPACE}')")
