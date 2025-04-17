#!/usr/bin/env python3
"""
cron_job.py - Script to automate the news crawler execution on a schedule

This script is designed to be run by a cron job every N minutes (configurable in .env). It:
1. Runs the crawler to fetch latest crypto news
2. Processes the data for the Economic AGENT
3. Forces embedding of new articles
4. Logs operation details for monitoring

Usage:
    Set up a crontab entry:
    */15 * * * * /path/to/venv/bin/python /path/to/project/cron_job.py >> /path/to/logs/crawler.log 2>&1
"""

import os
import sys
import logging
import time
import importlib.util
import subprocess
from datetime import datetime
import traceback

# Add the project directory to the path so we can import modules
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Disable tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Configure logging - only important logs
logging.basicConfig(
    level=logging.ERROR,  # Only log errors by default
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('cron_job')
logger.setLevel(logging.INFO)

# Set specific loggers to ERROR level to suppress unnecessary output
logging.getLogger('selenium').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('qdrant_client').setLevel(logging.ERROR)
logging.getLogger('scrapy').setLevel(logging.ERROR)
logging.getLogger('filelock').setLevel(logging.ERROR)

# Import project modules
from crawler.coin_data_source import fetch_coin_data, save_coin_data, fetch_fear_and_greed, save_fear_and_greed
from crawler.coin_articles_source import fetch_articles_data, save_articles
from crawler.fetch_articles_content import update_article
from chrome_driver import create_chrome_driver
from data_processor import process_data_for_embedding
from database import setup_database, connect_db
from config import COIN_NUMBER, ARTICLE_EN, ARTICLE_VI
from integration_manager import update_embeddings, check_embedding_status
from migrations.migrate_database import migrate_database

def run_coin68_crawler(driver):
    """Run the Coin68 crawler to fetch Vietnamese articles"""
    logger.info("Running Coin68 crawler...")
    
    try:
        # Import required modules for Scrapy
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings
        from coin68_crawler.coin68_crawler.spiders.fetch_article_content import ArticleSpider
        import json
        
        # Get project settings
        settings = get_project_settings()
        # Override some settings to ensure proper operation and reduce noise
        settings.update({
            'LOG_ENABLED': False,
            'LOG_LEVEL': 'ERROR',  # Only show errors
            'ROBOTSTXT_OBEY': False,  # Skip robots.txt check for efficiency
            'FEEDS': {
                'articles.json': {
                    'format': 'json',
                    'encoding': 'utf8',
                    'indent': 4,
                    'overwrite': True
                }
            }
        })
        
        # Run the crawler using CrawlerProcess
        logger.info(f"Crawling {ARTICLE_VI} Vietnamese articles using Scrapy...")
        process = CrawlerProcess(settings)
        process.crawl(ArticleSpider, target_count=ARTICLE_VI, driver=driver)
        process.start(stop_after_crawl=True)  # Important: This blocks until crawling is finished
        
        # Load the generated JSON file
        try:
            articles = []
            with open('articles.json', 'r', encoding='utf-8') as file:
                content = file.read().strip()
                if content:
                    articles = json.loads(content)
                    logger.info(f"Loaded {len(articles)} articles from Coin68 crawler")
                    
                    # Save articles to database
                    from crawler.coin_articles_source import save_articles
                    save_articles(articles)
                    return len(articles)
                else:
                    logger.warning("No articles found in articles.json")
                    return 0
        except FileNotFoundError:
            logger.error("articles.json was not created by the crawler")
            return 0
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing articles.json: {e}")
            return 0
                
    except Exception as e:
        logger.error(f"Error running Coin68 crawler: {str(e)}")
        return 0

def verify_embedding_status():
    """Verify if the crawled data has been embedded properly"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Get counts of articles and embedded status
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN embedded = 1 THEN 1 ELSE 0 END) as embedded,
                SUM(CASE WHEN embedded = 0 AND summary IS NOT NULL THEN 1 ELSE 0 END) as pending
            FROM articles
        """)
        
        result = cursor.fetchone()
        total = result[0]
        embedded = result[1]
        pending = result[2]
        
        # Check if all processed articles (with summary) are embedded
        embedding_status = {
            "total_articles": total,
            "embedded_articles": embedded,
            "pending_articles": pending,
            "embedding_percentage": round((embedded / total * 100), 2) if total > 0 else 0
        }
        
        cursor.close()
        conn.close()
        
        logger.info(f"Embedding status: {embedded}/{total} articles embedded ({embedding_status['embedding_percentage']}%)")
        
        return embedding_status
        
    except Exception as e:
        logger.error(f"Error verifying embedding status: {e}")
        return None

def run_cron_job():
    """Main function to run the crawler and process data"""
    start_time = time.time()
    job_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Only log important information when running as a cron job
    logger.setLevel(logging.INFO)
    
    logger.info(f"Starting crawler job {job_id}")
    
    try:
        # First, ensure database tables are properly set up
        try:
            # Run database migrations
            migrate_database()
            
            logger.info("Database structure verified and ready")
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
            return
        
        # Initialize Chrome driver
        logger.info("Initializing Chrome WebDriver...")
        driver = create_chrome_driver(headless=True, terminate_chrome=False)
        if not driver:
            logger.error("Failed to initialize Chrome driver. Aborting.")
            return
        
        try:
            # 1. Crawl fear and greed data
            logger.info("Fetching Fear and Greed Index...")
            fear_and_greed = fetch_fear_and_greed()
            if fear_and_greed:
                save_fear_and_greed(fear_and_greed)
                logger.info("Fear and Greed data saved successfully")
            
            # 2. Crawl coin data
            logger.info(f"Fetching data for top {COIN_NUMBER} coins...")
            coins = fetch_coin_data(limit=COIN_NUMBER, convert="USD")
            if coins:
                save_coin_data(coins)
                logger.info(f"Saved data for {len(coins)} coins")
            
            # 3. Crawl crypto news articles (English)
            logger.info(f"Fetching {ARTICLE_EN} English articles...")
            articles = fetch_articles_data(limit=ARTICLE_EN)
            if articles:
                update_article(driver, articles)
                save_articles(articles)
                logger.info(f"Saved {len(articles)} English articles")
            
            # 4. Crawl Coin68 (Vietnamese articles)
            logger.info(f"Fetching Vietnamese articles from Coin68...")
            vi_articles_count = run_coin68_crawler(driver)
            if vi_articles_count > 0:
                logger.info(f"Saved {vi_articles_count} Vietnamese articles")
            else:
                logger.warning("No Vietnamese articles were saved")
                    
            # 5. Process the data for the Economic AGENT
            logger.info("Processing articles for embedding...")
            new_articles_count = process_data_for_embedding()
            logger.info(f"Processed {new_articles_count} new articles for embedding")
            
            # 6. Force embedding of all unembedded articles
            logger.info("Embedding all processed articles into vector store...")
            # Run standalone mode with the proper embedding implementation
            total_embedded = update_embeddings(standalone_mode=True)
            logger.info(f"Embedded {total_embedded} articles into vector store")
            
            # 7. Verify embedding status
            embedding_status = verify_embedding_status()
            
            # If there are still unembedded articles, try one more time
            if embedding_status and embedding_status['pending_articles'] > 0:
                logger.warning(f"There are still {embedding_status['pending_articles']} articles that need embedding")
                final_embedded = update_embeddings(standalone_mode=True)
                logger.info(f"Final embedding attempt: Embedded {final_embedded} additional articles")
                
                # Update embedding status
                embedding_status = verify_embedding_status()
            
            # 8. Report completion
            elapsed_time = time.time() - start_time
            logger.info(f"Crawler job {job_id} completed in {elapsed_time:.2f} seconds")
            logger.info(f"Articles: {vi_articles_count + len(articles) if articles else 0} | Processed: {new_articles_count} | Embedded: {total_embedded}")
            
        finally:
            # Always close the driver
            if driver:
                logger.info("Closing Chrome WebDriver...")
                driver.quit()
                
    except Exception as e:
        logger.error(f"Error in crawler job {job_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
if __name__ == "__main__":
    run_cron_job()