import requests
from bs4 import BeautifulSoup

def scrape_behavioral_questions(url: str) -> list:
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    questions = []
    # Trouver les balises contenant les questions — à adapter si le site change
    for li in soup.select("article li"):
        text = li.get_text(strip=True)
        if text and len(text) > 10:  # filtrer du contenu inutile
            questions.append(text)

    return questions


if __name__ == "__main__":
    url = "https://www.techinterviewhandbook.org/behavioral-interview-questions/"
    questions = scrape_behavioral_questions(url)
    print(f"Scraped {len(questions)} questions")
    for q in questions[:5]:
        print("-", q)

    with open("behavioral_questions.json", "w", encoding="utf-8") as f:
        import json
        json.dump({"soft_skills_questions": questions}, f, indent=4, ensure_ascii=False)
