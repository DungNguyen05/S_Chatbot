import requests
import os
from database import connect_db
from config import API_KEY_CRYPTOPANIC  

API_KEY = os.getenv("CRYPTOPANICAPI_KEY", API_KEY_CRYPTOPANIC)  
BASE_URL = "https://cryptopanic.com/api/v1/posts/"


def fetch_articles_data(limit=100):
    params = {
        "auth_token": API_KEY,
        "limit": limit,    
    }
    
    articles = []
    page = 1  

    while len(articles) < limit:
        params["page"] = page  
        try:
            response = requests.get(BASE_URL, params=params)

            if response.status_code == 200:
                data = response.json()
                posts = data["results"]

                if not posts:
                    break

                # Add articles to the list
                for post in posts:
                    source_name = post.get("source", {}).get("domain", "N/A")
                    published_at = post.get("created_at", None)
                    if published_at:
                        # Convert from ISO 8601 to DATETIME (YYYY-MM-DD HH:MM:SS)
                        published_at = published_at.replace('T', ' ').replace('Z', '')

                    # Get unique currency information (only currency code)
                    currencies = ", ".join(set([currency.get("code", "N/A") for currency in post.get("currencies", [])]))

                    articles.append({
                        "title": post["title"],
                        "url": post["url"],
                        "source": source_name,  
                        "published_at": published_at,  
                        "currencies": currencies 
                    })
                
                    if len(articles) >= limit:
                        break

                page += 1 

            else:
                print(f"❌ Error when calling CryptoPanic API: {response.status_code}")
                break

        except Exception as e:
            print(f"❌ Error when calling CryptoPanic API: {e}")
            break

    print(f"✅ Successfully fetched {len(articles)} articles!")
    return articles

def save_articles(articles):
    conn = connect_db()
    cursor = conn.cursor()
    
    skipped = 0
    saved = 0

    try:
        for article in articles:
            # Check if the article URL already exists in the database
            cursor.execute("SELECT COUNT(*) FROM articles WHERE url = %s", (article["url"],))
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                skipped += 1
                continue  # Skip inserting this article if it already exists

            # Insert new article into the database
            cursor.execute(
                "INSERT INTO articles (title, url, source, published_at, currencies, content) VALUES (%s, %s, %s, %s, %s, %s)",
                (article["title"], article["url"], article["source"], article["published_at"], article["currencies"], article.get("content"))
            )
            saved += 1

        conn.commit()
        print(f"✅ Saved {saved} articles, skipped {skipped} duplicates")

    except Exception as e:
        print(f"⚠️ Error when saving article data into DB: {e}")

    finally:
        cursor.close()
        conn.close()