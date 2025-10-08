from pinecone import Pinecone
import os
from dotenv import load_dotenv
"""
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API")
INDEX_HOST = os.getenv("INDEX_URL")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=INDEX_HOST)

print("Index configuration:")
print(index.describe_index_stats())

"""
import replicate
import os
from dotenv import load_dotenv

load_dotenv()

# Modèles d'embedding potentiels sur Replicate
models_to_test = [
    # BGE Large (1024 dimensions)
    "nateraw/bge-large-en-v1.5:9cf9f015a9cb9c61d1a2610659cdac4a4ca222f2d3707a68517b18c198a9add1",
    
    # Instructor Large (768 dimensions mais populaire)
    "replicate/instructor-large:be96b447242555b757327252669f570e4a6f2185b3fe1e385c20876d4ba1d1b0",
    
    # All-mpnet-base-v2 (768 dimensions)
    "replicate/all-mpnet-base-v2:b6b7585c9640cd7a9572c6e129c9549d79c9c31f0d3fdce7baac7c67ca38f305",
    
    # E5 Large (1024 dimensions)
    "replicate/e5-large-v2:d4e98c3d31f17eccb67e4d4c6efbef8e7a5c8b97c6c6d4e0e0e5e5e5e5e5e5e5",
]

test_text = "Python programming language"

print("=" * 70)
print("TESTING REPLICATE EMBEDDING MODELS")
print("=" * 70)

for model_id in models_to_test:
    model_name = model_id.split(":")[0].split("/")[-1]
    
    try:
        print(f"\n📦 Testing: {model_name}")
        print(f"   Full ID: {model_id}")
        
        output = replicate.run(
            model_id,
            input={"text": test_text}
        )
        
        # Gérer différents formats de sortie
        if isinstance(output, list):
            embedding = output
        elif isinstance(output, dict):
            embedding = output.get('embedding', output.get('embeddings', []))
        else:
            embedding = list(output)
        
        dimension = len(embedding)
        
        print(f"   ✅ SUCCESS!")
        print(f"   📏 Dimension: {dimension}")
        print(f"   📊 First 5 values: {embedding[:5]}")
        
        if dimension == 1024:
            print(f"   🎯 PERFECT MATCH! This is 1024 dimensions!")
            print(f"\n   🔥 USE THIS MODEL:")
            print(f"   {model_id}")
            
    except Exception as e:
        print(f"   ❌ Failed: {str(e)[:100]}")

print("\n" + "=" * 70)