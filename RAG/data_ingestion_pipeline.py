"""
Data Ingestion Pipeline for Pinecone Knowledge Base
Supports multiple data sources and automatic categorization
What works: Python + Real Python + Java + GitHub 

"""

import os
import json
import requests
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import time
from bs4 import BeautifulSoup
import re

load_dotenv()

# ============ CONFIG ============
PINECONE_API_KEY = os.getenv("PINECONE_API")
INDEX_HOST = os.getenv("INDEX_URL")
NAMESPACE = "quiz-namespace"
BATCH_SIZE = 64

# ============ INIT ============
print("=" * 70)
print("🚀 DATA INGESTION PIPELINE")
print("=" * 70)

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=INDEX_HOST)

print("\n[indexer] Loading local embedding model (BAAI/bge-large-en-v1.5)...")
embedding_model = SentenceTransformer("BAAI/bge-large-en-v1.5")
print("[indexer] ✅ Model loaded successfully\n")


# ============ DATA SOURCES ============

class DataSource:
    """Base class for data sources"""
    
    def fetch(self) -> List[Dict[str, Any]]:
        """Fetch data and return list of records"""
        raise NotImplementedError
    
    def normalize(self, raw_data: List[Dict]) -> List[Dict]:
        """Normalize data to standard format"""
        normalized = []
        for item in raw_data:
            normalized.append({
                "id": item.get("id", f"auto_{len(normalized)}"),
                "text": self._build_text(item),
                "category": item.get("category", "unknown"),
                "difficulty": item.get("difficulty", "medium"),
                "bloom_level": item.get("bloom_level", "Understand"),
                "source": item.get("source", self.__class__.__name__),
                "skill": item.get("skill", "General"),
                "content_type": item.get("content_type", "question")
            })
        return normalized
    
    def _build_text(self, item: Dict) -> str:
        """Build text content from item"""
        text = item.get("question", "")
        if item.get("answer"):
            text += " " + item["answer"]
        if item.get("explanation"):
            text += " " + item["explanation"]
        return text.strip()


class LocalJSONSource(DataSource):
    """Load from local JSON files"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    def fetch(self) -> List[Dict]:
        print(f"📁 Loading from: {self.filepath}")
        with open(self.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"   ✅ Loaded {len(data)} items")
        return data


class PythonDocsSource(DataSource):
    """Scrape Python official documentation - Updated structure"""
    
    def __init__(self):
        self.base_url = "https://docs.python.org/3/tutorial/"
        self.sections = [
            "introduction.html",
            "controlflow.html",
            "datastructures.html",
            "modules.html",
            "classes.html",
            "errors.html"
        ]
    
    def fetch(self) -> List[Dict]:
        print(f"🌐 Scraping Python documentation...")
        data = []
        
        for section in self.sections:
            try:
                url = self.base_url + section
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try multiple HTML structures
                # Structure 1: section tags
                sections_found = soup.find_all('section')
                
                # Structure 2: div with class 'section'
                if not sections_found:
                    sections_found = soup.find_all('div', class_='section')
                
                # Structure 3: Look for h2 headers and following content
                if not sections_found:
                    headers = soup.find_all(['h2', 'h3'])
                    for header in headers:
                        # Create pseudo-section from header + following siblings
                        content_parts = []
                        for sibling in header.find_next_siblings():
                            if sibling.name in ['h2', 'h3']:
                                break
                            if sibling.name == 'p':
                                content_parts.append(sibling.get_text().strip())
                            if len(content_parts) >= 3:
                                break
                        
                        if content_parts:
                            sections_found.append({
                                'title': header.get_text().strip(),
                                'content': ' '.join(content_parts)
                            })
                
                # Process found sections
                items_in_section = 0
                for i, section_elem in enumerate(sections_found):
                    # Handle different section types
                    if isinstance(section_elem, dict):
                        title = section_elem['title']
                        content = section_elem['content']
                    else:
                        title_elem = section_elem.find(['h1', 'h2', 'h3'])
                        if not title_elem:
                            continue
                        title = title_elem.get_text().strip()
                        
                        # Get text content
                        paragraphs = section_elem.find_all('p')
                        content = ' '.join([p.get_text().strip() for p in paragraphs[:3]])
                    
                    if len(content) > 100:  # Only meaningful content
                        data.append({
                            "id": f"python_docs_{section.replace('.html', '')}_{i}",
                            "question": title,
                            "answer": content,
                            "category": "Technical",
                            "difficulty": "medium",
                            "bloom_level": "Understand",
                            "source": "python_docs",
                            "skill": "Python",
                            "content_type": "documentation"
                        })
                        items_in_section += 1
                
                print(f"   ✅ Scraped {section}: {items_in_section} items")
                time.sleep(1)  # Be polite
                
            except Exception as e:
                print(f"   ⚠️  Failed to scrape {section}: {e}")
        
        print(f"   ✅ Total: {len(data)} items from Python docs")
        return data


class GitHubInterviewQuestionsSource(DataSource):
    """Fetch interview questions from GitHub repos"""
    
    def __init__(self):
        self.repos = [
            {
                "owner": "jwasham",
                "repo": "coding-interview-university",
                "path": "README.md",
                "skill": "Algorithms"
            }
        ]
    
    def fetch(self) -> List[Dict]:
        print(f"🐙 Fetching from GitHub repositories...")
        data = []
        
        for repo_info in self.repos:
            try:
                # GitHub API to get file content
                api_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/contents/{repo_info['path']}"
                headers = {"Accept": "application/vnd.github.v3.raw"}
                
                response = requests.get(api_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                content = response.text
                
                # Extract sections (simple markdown parsing)
                sections = self._parse_markdown_sections(content)
                
                for i, section in enumerate(sections):
                    if len(section['content']) > 100:
                        data.append({
                            "id": f"github_{repo_info['repo']}_{i}",
                            "question": section['title'],
                            "answer": section['content'],
                            "category": "Technical",
                            "difficulty": "medium",
                            "bloom_level": "Apply",
                            "source": f"github_{repo_info['repo']}",
                            "skill": repo_info['skill'],
                            "content_type": "tutorial"
                        })
                
                print(f"   ✅ Fetched {repo_info['repo']}: {len(sections)} sections")
                time.sleep(1)
                
            except Exception as e:
                print(f"   ⚠️  Failed to fetch {repo_info['repo']}: {e}")
        
        print(f"   ✅ Total: {len(data)} items from GitHub")
        return data
    
    def _parse_markdown_sections(self, content: str) -> List[Dict]:
        """Simple markdown section parser"""
        sections = []
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            if line.startswith('## '):
                if current_section and len(current_section['content']) > 50:
                    sections.append(current_section)
                current_section = {
                    'title': line.replace('## ', '').strip(),
                    'content': ''
                }
            elif current_section:
                current_section['content'] += ' ' + line.strip()
        
        if current_section and len(current_section['content']) > 50:
            sections.append(current_section)
        
        return sections[:20]  # Limit to first 20 sections


class RealPythonSource(DataSource):
    """Fetch content from Real Python tutorials (easier than scraping docs)"""
    
    def fetch(self) -> List[Dict]:
        print(f"🐍 Fetching Real Python content...")
        
        # Curated Real Python topics with summaries
        data = [
            {
                "id": "realpython_001",
                "question": "Python List Comprehensions",
                "answer": "List comprehensions provide a concise way to create lists. Syntax: [expression for item in iterable if condition]. Example: squares = [x**2 for x in range(10)]. They're more readable and often faster than equivalent for loops. Can include nested loops and multiple conditions.",
                "category": "Technical",
                "difficulty": "intermediate",
                "bloom_level": "Apply",
                "source": "realpython",
                "skill": "Python",
                "content_type": "tutorial"
            },
            {
                "id": "realpython_002",
                "question": "Python Decorators Explained",
                "answer": "Decorators are functions that modify other functions. Syntax: @decorator_name above function definition. Common uses: timing functions, logging, access control. Example: @staticmethod, @property. Decorators take a function, add functionality, and return it. They use closures and higher-order functions.",
                "category": "Technical",
                "difficulty": "advanced",
                "bloom_level": "Understand",
                "source": "realpython",
                "skill": "Python",
                "content_type": "tutorial"
            },
            {
                "id": "realpython_003",
                "question": "Python Virtual Environments",
                "answer": "Virtual environments isolate project dependencies. Create with: python -m venv env_name. Activate: source env/bin/activate (Linux/Mac) or env\\Scripts\\activate (Windows). Install packages with pip. Deactivate with 'deactivate'. Helps avoid dependency conflicts between projects.",
                "category": "Technical",
                "difficulty": "beginner",
                "bloom_level": "Apply",
                "source": "realpython",
                "skill": "Python",
                "content_type": "tutorial"
            },
            {
                "id": "realpython_004",
                "question": "Python Context Managers (with statement)",
                "answer": "Context managers handle setup and cleanup automatically using 'with' statement. Example: with open('file.txt') as f: data = f.read(). Guarantees file closure even if errors occur. Create custom with __enter__ and __exit__ methods or use @contextmanager decorator. Great for resource management.",
                "category": "Technical",
                "difficulty": "intermediate",
                "bloom_level": "Apply",
                "source": "realpython",
                "skill": "Python",
                "content_type": "tutorial"
            },
            {
                "id": "realpython_005",
                "question": "Python Asyncio Basics",
                "answer": "Asyncio enables concurrent code using async/await syntax. Use for I/O-bound operations. Define async functions with 'async def'. Await them with 'await'. Run with asyncio.run(). Different from threading/multiprocessing - single-threaded cooperative multitasking. Ideal for web scraping, API calls, database queries.",
                "category": "Technical",
                "difficulty": "advanced",
                "bloom_level": "Understand",
                "source": "realpython",
                "skill": "Python",
                "content_type": "tutorial"
            }
        ]
        
        print(f"   ✅ Generated {len(data)} Real Python items")
        return data


class JavaTutorialsSource(DataSource):
    """Curated Java content"""
    
    def fetch(self) -> List[Dict]:
        print(f"☕ Generating Java content...")
        
        data = [
            {
                "id": "java_001",
                "question": "Java Collections Framework Overview",
                "answer": "Main interfaces: List (ordered, duplicates allowed), Set (no duplicates), Map (key-value pairs), Queue (FIFO). Implementations: ArrayList (fast access), LinkedList (fast insertion), HashSet (O(1) lookup), TreeSet (sorted), HashMap (fast lookup), TreeMap (sorted keys). Choose based on use case requirements.",
                "category": "Technical",
                "difficulty": "intermediate",
                "bloom_level": "Understand",
                "source": "java_curated",
                "skill": "Java",
                "content_type": "concept"
            },
            {
                "id": "java_002",
                "question": "Java Stream API",
                "answer": "Streams enable functional-style operations on collections. Common operations: filter(), map(), reduce(), collect(). Example: list.stream().filter(x -> x > 10).map(x -> x * 2).collect(Collectors.toList()). Lazy evaluation - intermediate operations aren't executed until terminal operation. Parallel streams with parallelStream().",
                "category": "Technical",
                "difficulty": "intermediate",
                "bloom_level": "Apply",
                "source": "java_curated",
                "skill": "Java",
                "content_type": "concept"
            },
            {
                "id": "java_003",
                "question": "Java Exception Handling Best Practices",
                "answer": "Use try-catch-finally for cleanup. Catch specific exceptions before generic ones. Use try-with-resources for AutoCloseable objects. Don't catch Exception or Throwable directly. Create custom exceptions when needed. Log exceptions with context. Never empty catch blocks. Use throws for checked exceptions you can't handle.",
                "category": "Technical",
                "difficulty": "intermediate",
                "bloom_level": "Apply",
                "source": "java_curated",
                "skill": "Java",
                "content_type": "best_practice"
            },
            {
                "id": "java_004",
                "question": "Spring Boot Auto-Configuration",
                "answer": "Spring Boot automatically configures beans based on classpath and defined beans. @EnableAutoConfiguration triggers this. Scans META-INF/spring.factories. Can exclude with @SpringBootApplication(exclude=...). Override with application.properties. View with --debug flag. Conditional annotations like @ConditionalOnClass control when configs apply.",
                "category": "Technical",
                "difficulty": "advanced",
                "bloom_level": "Understand",
                "source": "java_curated",
                "skill": "Spring Framework",
                "content_type": "concept"
            }
        ]
        
        print(f"   ✅ Generated {len(data)} Java items")
        return data


class CustomContentSource(DataSource):
    """Create custom educational content"""
    
    def fetch(self) -> List[Dict]:
        print(f"📝 Generating custom content...")
        
        # Custom curated content for gaps in your knowledge base
        data = [
            # Python content
            {
                "id": "custom_python_001",
                "question": "What is the difference between list comprehension and generator expression in Python?",
                "answer": "List comprehension creates a full list in memory immediately, using square brackets [x for x in range(10)]. Generator expressions create an iterator that generates values on-the-fly, using parentheses (x for x in range(10)). Generators are memory-efficient for large datasets.",
                "category": "Technical",
                "difficulty": "intermediate",
                "bloom_level": "Analyze",
                "source": "custom_curated",
                "skill": "Python",
                "content_type": "concept"
            },
            {
                "id": "custom_python_002",
                "question": "Explain Python's Global Interpreter Lock (GIL)",
                "answer": "The GIL is a mutex that protects access to Python objects, preventing multiple threads from executing Python bytecode simultaneously. This means CPU-bound multithreading doesn't improve performance. Use multiprocessing for CPU-bound tasks or asyncio for I/O-bound tasks.",
                "category": "Technical",
                "difficulty": "advanced",
                "bloom_level": "Understand",
                "source": "custom_curated",
                "skill": "Python",
                "content_type": "concept"
            },
            # Java content
            {
                "id": "custom_java_001",
                "question": "What is the difference between ArrayList and LinkedList in Java?",
                "answer": "ArrayList uses a dynamic array internally, offering O(1) random access but O(n) insertion/deletion. LinkedList uses a doubly-linked list, offering O(1) insertion/deletion at ends but O(n) random access. Choose ArrayList for frequent access, LinkedList for frequent modifications.",
                "category": "Technical",
                "difficulty": "intermediate",
                "bloom_level": "Analyze",
                "source": "custom_curated",
                "skill": "Java",
                "content_type": "concept"
            },
            # Leadership content
            {
                "id": "custom_leadership_001",
                "question": "How do you handle conflict between team members?",
                "answer": "Listen to both sides individually, understand the root cause, facilitate a mediated discussion, focus on the problem not personalities, find common ground, agree on action steps, and follow up to ensure resolution. Use active listening and maintain neutrality.",
                "category": "Behavioral",
                "difficulty": "medium",
                "bloom_level": "Apply",
                "source": "custom_curated",
                "skill": "Leadership",
                "content_type": "scenario"
            },
            {
                "id": "custom_leadership_002",
                "question": "Describe a time when you had to make a difficult decision as a leader",
                "answer": "Good answers should follow STAR format: Situation (context), Task (challenge), Action (steps taken including stakeholder consultation, data analysis, risk assessment), Result (outcome and lessons learned). Focus on decision-making process and communication.",
                "category": "Behavioral",
                "difficulty": "medium",
                "bloom_level": "Evaluate",
                "source": "custom_curated",
                "skill": "Leadership",
                "content_type": "interview_prep"
            },
            # Problem Solving
            {
                "id": "custom_problemsolving_001",
                "question": "What is the best approach to debug a production issue?",
                "answer": "1) Gather data: logs, metrics, user reports. 2) Reproduce the issue in a safe environment. 3) Form hypotheses. 4) Test hypotheses systematically. 5) Implement fix. 6) Verify in staging. 7) Monitor after deployment. 8) Document root cause and prevention measures.",
                "category": "Cognitive",
                "difficulty": "advanced",
                "bloom_level": "Evaluate",
                "source": "custom_curated",
                "skill": "Problem Solving",
                "content_type": "process"
            },
            # Analytical Thinking
            {
                "id": "custom_analytical_001",
                "question": "How do you optimize a slow database query?",
                "answer": "1) Use EXPLAIN to analyze query execution plan. 2) Add appropriate indexes on filtered/joined columns. 3) Avoid SELECT *, query only needed columns. 4) Optimize JOINs and subqueries. 5) Use query caching when appropriate. 6) Consider denormalization for read-heavy tables. 7) Monitor query performance metrics.",
                "category": "Cognitive",
                "difficulty": "advanced",
                "bloom_level": "Analyze",
                "source": "custom_curated",
                "skill": "Analytical Thinking",
                "content_type": "process"
            },
        ]
        
        print(f"   ✅ Generated {len(data)} custom items")
        return data


class StackOverflowSource(DataSource):
    """Fetch top-voted questions from Stack Overflow"""
    
    def __init__(self, tags: List[str] = ["python", "java"]):
        self.tags = tags
        self.api_url = "https://api.stackexchange.com/2.3/questions"
    
    def fetch(self) -> List[Dict]:
        print(f"📚 Fetching from Stack Overflow...")
        data = []
        
        for tag in self.tags:
            try:
                params = {
                    "order": "desc",
                    "sort": "votes",
                    "tagged": tag,
                    "site": "stackoverflow",
                    "filter": "withbody",
                    "pagesize": 10  # Top 10 per tag
                }
                
                response = requests.get(self.api_url, params=params, timeout=10)
                response.raise_for_status()
                
                questions = response.json().get("items", [])
                
                for q in questions:
                    # Clean HTML from body
                    clean_body = BeautifulSoup(q.get("body", ""), 'html.parser').get_text()
                    
                    data.append({
                        "id": f"stackoverflow_{q['question_id']}",
                        "question": q.get("title", ""),
                        "answer": clean_body[:500],  # First 500 chars
                        "category": "Technical",
                        "difficulty": "medium",
                        "bloom_level": "Apply",
                        "source": "stackoverflow",
                        "skill": tag.capitalize(),
                        "content_type": "qa"
                    })
                
                print(f"   ✅ Fetched {tag}: {len(questions)} questions")
                time.sleep(1)  # Respect rate limits
                
            except Exception as e:
                print(f"   ⚠️  Failed to fetch {tag}: {e}")
        
        print(f"   ✅ Total: {len(data)} items from Stack Overflow")
        return data


# ============ INGESTION PIPELINE ============

def chunked(lst, size):
    """Split list into chunks"""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def ingest_data(sources: List[DataSource], dry_run: bool = False):
    """
    Main ingestion pipeline
    
    Args:
        sources: List of data sources to ingest
        dry_run: If True, only show what would be uploaded (no actual upload)
    """
    all_records = []
    
    print("\n" + "=" * 70)
    print("📥 FETCHING DATA FROM SOURCES")
    print("=" * 70 + "\n")
    
    # Fetch and normalize data from all sources
    for source in sources:
        try:
            raw_data = source.fetch()
            normalized = source.normalize(raw_data)
            all_records.extend(normalized)
        except Exception as e:
            print(f"❌ Error with {source.__class__.__name__}: {e}")
    
    print(f"\n📊 Total records collected: {len(all_records)}")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No data will be uploaded")
        print("\nSample records:")
        for record in all_records[:3]:
            print(f"\n  ID: {record['id']}")
            print(f"  Skill: {record['skill']}")
            print(f"  Text: {record['text'][:100]}...")
        return
    
    print("\n" + "=" * 70)
    print("⚙️  GENERATING EMBEDDINGS AND UPLOADING")
    print("=" * 70 + "\n")
    
    total_uploaded = 0
    
    for batch in chunked(all_records, BATCH_SIZE):
        # Generate embeddings
        texts = [r["text"] for r in batch]
        embeddings = embedding_model.encode(texts, show_progress_bar=False).tolist()
        
        # Prepare vectors for Pinecone
        vectors = []
        for i, record in enumerate(batch):
            vectors.append({
                "id": str(record["id"]),
                "values": embeddings[i],
                "metadata": {
                    "text": record["text"][:1000],  # Limit metadata size
                    "category": record["category"],
                    "difficulty": record["difficulty"],
                    "bloom_level": record["bloom_level"],
                    "source": record["source"],
                    "skill": record["skill"],
                    "content_type": record["content_type"]
                }
            })
        
        # Upload to Pinecone
        try:
            index.upsert(vectors=vectors, namespace=NAMESPACE)
            total_uploaded += len(batch)
            print(f"✅ Uploaded batch of {len(batch)} records (Total: {total_uploaded})")
        except Exception as e:
            print(f"❌ Failed to upload batch: {e}")
    
    print(f"\n🎉 Finished! Uploaded {total_uploaded}/{len(all_records)} records")
    print(f"   Namespace: {NAMESPACE}")


# ============ MAIN ============

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest data into Pinecone")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded without uploading")
    parser.add_argument("--sources", nargs="+", default=["all"], 
                       help="Sources to use: local, python_docs, realpython, java, github, stackoverflow, custom, all")
    args = parser.parse_args()
    
    # Configure sources
    sources = []
    
    if "all" in args.sources or "local" in args.sources:
        # Add your local JSON files
        if Path("technical_questions_annotated.json").exists():
            sources.append(LocalJSONSource("technical_questions_annotated.json"))
        if Path("behavioral_questions_harmonized.json").exists():
            sources.append(LocalJSONSource("behavioral_questions_harmonized.json"))
    
    if "all" in args.sources or "custom" in args.sources:
        sources.append(CustomContentSource())
    
    if "all" in args.sources or "realpython" in args.sources:
        sources.append(RealPythonSource())
    
    if "all" in args.sources or "java" in args.sources:
        sources.append(JavaTutorialsSource())
    
    if "all" in args.sources or "python_docs" in args.sources:
        sources.append(PythonDocsSource())
    
    if "all" in args.sources or "github" in args.sources:
        sources.append(GitHubInterviewQuestionsSource())
    
    if "all" in args.sources or "stackoverflow" in args.sources:
        sources.append(StackOverflowSource(tags=["python", "java", "spring"]))
    
    print(f"\n🎯 Configured {len(sources)} data sources")
    
    # Run ingestion
    ingest_data(sources, dry_run=args.dry_run)
    
    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETE")
    print("=" * 70)