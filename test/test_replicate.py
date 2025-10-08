import replicate
import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

# Test 1: Générer un embedding
print("=" * 60)
print("TEST 1: Générer embedding avec Replicate")
print("=" * 60)

try:
    output = replicate.run(
        "replicate/all-mpnet-base-v2:b6b7585c9640cd7a9572c6e129c9549d79c9c31f0d3fdce7baac7c67ca38f305",
        input={"text": "Python programming"}
    )
    print(f"✅ Embedding généré!")
    print(f"Dimension: {len(output)}")
    print(f"Premiers éléments: {output[:5]}")
except Exception as e:
    print(f"❌ Erreur: {e}")

# Test 2: Query Pinecone
print("\n" + "=" * 60)
print("TEST 2: Query Pinecone avec l'embedding")
print("=" * 60)

try:
    pc = Pinecone(api_key=os.getenv("PINECONE_API"))
    index = pc.Index(host=os.getenv("INDEX_URL"))
    
    results = index.query(
        namespace="quiz-namespace",
        vector=output,
        top_k=3,
        include_metadata=True
    )
    
    print(f"✅ Query réussie!")
    print(f"Résultats trouvés: {len(results.get('matches', []))}")
    
    for i, match in enumerate(results.get('matches', [])[:3]):
        print(f"\nRésultat {i+1}:")
        print(f"  Score: {match.get('score', 0):.4f}")
        print(f"  Text: {match.get('metadata', {}).get('text', 'N/A')[:100]}...")
        
except Exception as e:
    print(f"❌ Erreur: {e}")