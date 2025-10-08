import json
import os
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API")
INDEX_NAME = "quiz-knowledge-base"
INDEX_HOST = os.getenv("INDEX_URL")  # ex: "https://quiz-knowledge-base.svc.pinecone.io"
NAMESPACE = "quiz-namespace"

# --- INIT ---
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=INDEX_HOST)

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
        "_id": str(item["id"]),
        "text": chunk_text,
        "category": str(item.get("category", "")) or "unknown",
        "difficulty": str(item.get("difficulty", "")) or "unknown",
        "bloom_level": str(item.get("bloom_level", "")) or "unknown",
        "source": str(item.get("source", "")) or "unknown"
    })



print(f"⚙️ Preparing to upload {len(records)} records in batches...")

# --- UPSERT EN BATCHES ---
BATCH_SIZE = 96

def chunked(lst, size): 
    for i in range(0, len(lst), size): yield lst[i:i + size]

total_uploaded = 0
for batch in chunked(records, BATCH_SIZE):
    index.upsert_records(NAMESPACE, batch)
    total_uploaded += len(batch)
    print(f"✅ Uploaded batch of {len(batch)} records (Total: {total_uploaded})")


print(f"🎉 Finished uploading {total_uploaded} records into Pinecone (namespace='{NAMESPACE}')")

