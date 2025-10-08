from pinecone import Pinecone
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

print("=" * 60)
print("TEST: SentenceTransformer → Pinecone")
print("=" * 60)

# Step 1: Load model
print("\n1️⃣ Loading model...")
try:
    model = SentenceTransformer('BAAI/bge-large-en-v1.5')
    print("   ✅ Model loaded")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# Step 2: Generate embedding
print("\n2️⃣ Generating embedding...")
try:
    embedding = model.encode("Python programming").tolist()
    print(f"   ✅ Embedding generated")
    print(f"   📏 Dimension: {len(embedding)}")
    print(f"   📊 First 5 values: {embedding[:5]}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# Step 3: Query Pinecone
print("\n3️⃣ Querying Pinecone...")
try:
    pc = Pinecone(api_key=os.getenv("PINECONE_API"))
    index = pc.Index(host=os.getenv("INDEX_URL"))
    
    results = index.query(
        namespace="quiz-namespace",
        vector=embedding,
        top_k=3,
        include_metadata=True
    )
    
    print(f"   ✅ Query successful!")
    print(f"   📊 Results found: {len(results.get('matches', []))}")
    
    for i, match in enumerate(results.get('matches', [])[:3]):
        print(f"\n   Result {i+1}:")
        print(f"      Score: {match.get('score', 0):.4f}")
        print(f"      Text: {match.get('metadata', {}).get('text', 'N/A')[:80]}...")
    
except Exception as e:
    print(f"   ❌ Failed: {e}")

print("\n" + "=" * 60)
print("🎉 Done!")
print("=" * 60)