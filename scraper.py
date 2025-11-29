import requests
from bs4 import BeautifulSoup
import mysql.connector
from datetime import datetime
from config import DB_CONFIG

def get_db_connection():
    """Create database connection"""
    return mysql.connector.connect(**DB_CONFIG)

def get_source_id(conn, source_name):
    """Get source_id from database"""
    cursor = conn.cursor()
    cursor.execute("SELECT source_id FROM news_sources WHERE source_name = %s", (source_name,))
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else None

def detect_category(title, description):
    """Detect category based on keywords in title and description"""
    text = (title + " " + description).lower()
    
    # Category keywords mapping
    categories = {
        'Politics': ['election', 'government', 'minister', 'parliament', 'politics', 'political', 'congress', 'bjp', 'vote', 'pm', 'president'],
        'Technology': ['tech', 'technology', 'ai', 'software', 'hardware', 'computer', 'app', 'digital', 'cyber', 'internet', 'smartphone', 'gadget'],
        'Sports': ['cricket', 'football', 'sports', 'match', 'player', 'ipl', 'fifa', 'olympics', 'tournament', 'champion', 'goal', 'score'],
        'Business': ['business', 'economy', 'market', 'stock', 'finance', 'company', 'corporate', 'industry', 'trade', 'investment', 'rupee', 'revenue'],
        'Entertainment': ['movie', 'film', 'actor', 'actress', 'bollywood', 'hollywood', 'music', 'celebrity', 'entertainment', 'show', 'series'],
        'Health': ['health', 'medical', 'doctor', 'hospital', 'disease', 'vaccine', 'covid', 'medicine', 'treatment', 'patient'],
        'Science': ['science', 'research', 'study', 'scientist', 'space', 'nasa', 'isro', 'discovery', 'experiment'],
        'World': ['world', 'international', 'global', 'country', 'nation', 'usa', 'china', 'europe', 'war', 'peace'],
        'Education': ['education', 'school', 'college', 'university', 'student', 'exam', 'admission', 'degree', 'learning']
    }
    
    # Check each category
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text:
                return category
    
    return 'General'  # Default category

def get_category_id(conn, category_name):
    """Get category_id from database"""
    cursor = conn.cursor()
    cursor.execute("SELECT category_id FROM categories WHERE category_name = %s", (category_name,))
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else 1  # Return 1 (General) if not found

def insert_headline(conn, title, description, url, image_url, source_id, category_id, publish_date):
    """Insert news headline into database"""
    cursor = conn.cursor()
    
    # Check if headline already exists (avoid duplicates)
    cursor.execute("SELECT headline_id FROM news_headlines WHERE url = %s", (url,))
    if cursor.fetchone():
        cursor.close()
        return False  # Already exists
    
    # Insert new headline
    query = """
        INSERT INTO news_headlines (title, description, url, image_url, source_id, category_id, publish_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (title, description, url, image_url, source_id, category_id, publish_date))
    conn.commit()
    cursor.close()
    return True

def scrape_rss(name, url, conn):
    """Scrape RSS feed and save to database"""
    print(f"\n----- Scraping {name} -----")
    
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "xml")
        items = soup.find_all("item")[:10]  # Get top 10 articles
        
        source_id = get_source_id(conn, name)
        if not source_id:
            print(f"Source {name} not found in database!")
            return
        
        count = 0
        for item in items:
            # Extract data
            title = item.title.text if item.title else "No title"
            desc_tag = item.description
            desc = desc_tag.text if desc_tag else "No description"
            
            # Clean description (remove HTML tags if any)
            desc_soup = BeautifulSoup(desc, "html.parser")
            desc = desc_soup.get_text()[:500]  # Limit to 500 chars
            
            # Get article URL
            link = item.link.text if item.link else item.guid.text if item.guid else ""
            
            # Extract image
            media = item.find("media:content")
            if media and media.get("url"):
                img = media["url"]
            else:
                # Try to find image in description
                img_tag = desc_soup.find("img")
                img = img_tag["src"] if img_tag and img_tag.get("src") else None
            
            # Get publish date
            pub_date_tag = item.pubDate
            if pub_date_tag:
                try:
                    pub_date = datetime.strptime(pub_date_tag.text, "%a, %d %b %Y %H:%M:%S %z")
                except:
                    pub_date = datetime.now()
            else:
                pub_date = datetime.now()
            
            # Detect category
            category_name = detect_category(title, desc)
            category_id = get_category_id(conn, category_name)
            
            # Insert into database
            if insert_headline(conn, title, desc, link, img, source_id, category_id, pub_date):
                count += 1
                print(f"✓ Added [{category_name}]: {title[:50]}...")
        
        print(f"Total new headlines from {name}: {count}")
    
    except Exception as e:
        print(f"Error scraping {name}: {e}")

def scrape_all_sources():
    """Main function to scrape all news sources"""
    news_feeds = {
        "NDTV": "https://feeds.feedburner.com/ndtvnews-latest",
        "India Today": "https://www.indiatoday.in/rss/home",
        "Hindustan Times": "https://www.hindustantimes.com/feeds/rss/latest-news/rssfeed.xml"
    }
    
    conn = get_db_connection()
    
    print("=" * 50)
    print("Starting News Scraping...")
    print("=" * 50)
    
    for name, url in news_feeds.items():
        scrape_rss(name, url, conn)
    
    conn.close()
    print("\n" + "=" * 50)
    print("Scraping completed!")
    print("=" * 50)

if __name__ == "__main__":
    scrape_all_sources()