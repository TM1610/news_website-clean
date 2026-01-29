import requests
from bs4 import BeautifulSoup
import psycopg
from psycopg.rows import dict_row
from datetime import datetime

from config import DB_CONFIG


# ==================== DATABASE ====================
def get_db():
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row)


# ==================== HELPERS ====================
def get_source_id(conn, source_name):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT source_id FROM news_sources WHERE source_name = %s",
        (source_name,)
    )
    result = cursor.fetchone()
    cursor.close()
    return result["source_id"] if result else None


def get_category_id(conn, category_name):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT category_id FROM categories WHERE category_name = %s",
        (category_name,)
    )
    result = cursor.fetchone()
    cursor.close()
    return result["category_id"] if result else 1  # fallback = General


def detect_category(title, description):
    text = (title + " " + description).lower()

    categories = {
        "Politics": ["election", "government", "minister", "parliament", "politics", "bjp", "congress"],
        "Technology": ["tech", "technology", "ai", "software", "app", "digital", "internet"],
        "Sports": ["cricket", "football", "sports", "ipl", "fifa", "match"],
        "Business": ["business", "market", "stock", "finance", "company", "economy"],
        "Entertainment": ["movie", "film", "actor", "bollywood", "music", "celebrity"],
        "Health": ["health", "doctor", "hospital", "vaccine", "medicine"],
        "Science": ["science", "research", "space", "nasa", "isro"],
        "World": ["world", "international", "global", "war"],
        "Education": ["education", "school", "college", "exam", "student"]
    }

    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text:
                return category

    return "General"


def insert_headline(conn, title, description, url, image_url, source_id, category_id, publish_date):
    cursor = conn.cursor()

    cursor.execute(
        "SELECT headline_id FROM news_headlines WHERE url = %s",
        (url,)
    )
    if cursor.fetchone():
        cursor.close()
        return False

    cursor.execute(
        """
        INSERT INTO news_headlines
        (title, description, url, image_url, source_id, category_id, publish_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (title, description, url, image_url, source_id, category_id, publish_date)
    )

    conn.commit()
    cursor.close()
    return True


# ==================== SCRAPING ====================
def scrape_rss(name, url, conn):
    print(f"\n--- Scraping {name} ---")

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")[:10]

    source_id = get_source_id(conn, name)
    if not source_id:
        print(f"Source '{name}' not found in DB")
        return

    count = 0

    for item in items:
        title = item.title.text if item.title else "No title"
        desc_html = item.description.text if item.description else ""
        desc = BeautifulSoup(desc_html, "html.parser").get_text()[:500]

        link = item.link.text if item.link else ""

        media = item.find("media:content")
        image_url = media["url"] if media and media.get("url") else None

        try:
            publish_date = datetime.strptime(item.pubDate.text, "%a, %d %b %Y %H:%M:%S %z")
        except Exception:
            publish_date = datetime.now()

        category_name = detect_category(title, desc)
        category_id = get_category_id(conn, category_name)

        if insert_headline(conn, title, desc, link, image_url, source_id, category_id, publish_date):
            count += 1

    print(f"Added {count} new articles from {name}")


def scrape_all_sources():
    feeds = {
        "NDTV": "https://feeds.feedburner.com/ndtvnews-latest",
        "India Today": "https://www.indiatoday.in/rss/home",
        "Hindustan Times": "https://www.hindustantimes.com/feeds/rss/latest-news/rssfeed.xml"
    }

    conn = get_db()

    print("Starting scraping...")
    for name, url in feeds.items():
        scrape_rss(name, url, conn)

    conn.close()
    print("Scraping finished.")


if __name__ == "__main__":
    scrape_all_sources()
