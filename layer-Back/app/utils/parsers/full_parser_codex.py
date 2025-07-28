from bs4 import BeautifulSoup
import json

def parse_upk_articles_precise_tags(html_path: str, output_json: str):
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    articles = []
    current_article = None
    current_section = None
    current_chapter = None

    for tag in soup.find_all(["p", "h3"]):
        text = tag.get_text(strip=True)

        # Обновление раздела
        if text.startswith("Раздел "):
            current_section = text

        # Обновление главы
        elif text.startswith("Глава "):
            current_chapter = text

        # Начало новой статьи
        elif text.startswith("Статья") and "." in text:
            if current_article:
                articles.append(current_article)

            try:
                parts = text.replace("Статья", "").strip().split(".", maxsplit=1)
                number = parts[0].strip()
                title = parts[1].strip()
                full_tag = f"Статья {number}. {title}"
                current_article = {
                    "article": number,
                    "title": title,
                    "text": "",
                    "tags": full_tag,  # ← сюда идёт точное название статьи
                    "section": current_section or "",
                    "chapter": current_chapter or ""
                }
            except:
                continue

        # Добавление текста к текущей статье
        elif current_article:
            current_article["text"] += text + "\n"

    if current_article:
        articles.append(current_article)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"✅ Сохранено {len(articles)} статей → {output_json}")

# 🚀 Запуск
if __name__ == "__main__":
    parse_upk_articles_precise_tags(
        html_path="УПК_РК.html",
        output_json="full_codex.json"
    )
