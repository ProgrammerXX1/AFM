from bs4 import BeautifulSoup
import json

def parse_selected_articles(html_path: str, output_json: str, selected_articles: list):
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    articles = []
    current_article = None
    current_number = None

    for tag in soup.find_all(["p", "h3"]):
        text = tag.get_text(strip=True)

        # Начало новой статьи
        if text.startswith("Статья") and "." in text:
            if current_article and current_number in selected_articles:
                articles.append(current_article)

            try:
                parts = text.replace("Статья", "").strip().split(".", maxsplit=1)
                current_number = parts[0].strip()
                title = parts[1].strip()

                current_article = {
                    "article": current_number,
                    "title": title,
                    "text": "",
                    "tags": []
                }
            except:
                current_article = None
                current_number = None

        elif current_article and current_number in selected_articles:
            current_article["text"] += text + "\n"

    # Последняя статья
    if current_article and current_number in selected_articles:
        articles.append(current_article)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Сохранено {len(articles)} статей → {output_json}")


# 🔧 Основной запуск
if __name__ == "__main__":
    html_path="УПК_РК.html",
    output_json="select_codex.json"

    user_input = input("🔍 Введите номера статей через запятую: ").strip()
    selected = [num.strip() for num in user_input.split(",") if num.strip().isdigit()]

    if not selected:
        print("❌ Не указано ни одной корректной статьи.")
    else:
        parse_selected_articles(html_path, output_json, selected)
