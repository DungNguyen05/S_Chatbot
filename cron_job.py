#!/usr/bin/env python3
"""
cron_job.py - Script to automate the news crawler execution on a schedule

This script is designed to be run by a cron job every 15 minutes. It:
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('cron_job')

# Import project modules
from crawler.coin_data_source import fetch_coin_data, save_coin_data, fetch_fear_and_greed, save_fear_and_greed
from crawler.coin_articles_source import fetch_articles_data, save_articles
from crawler.fetch_articles_content import update_article
from chrome_driver import create_chrome_driver
from data_processor import process_data_for_embedding
from database import setup_database, connect_db
from config import COIN_NUMBER, ARTICLE_EN, ARTICLE_VI
from integration_manager import update_embeddings

# Find and update the run_coin68_crawler function in cron_job.py
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
        # Override some settings to ensure proper operation
        settings.update({
            'LOG_ENABLED': False,
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
            with open('articles.json', 'r', encoding='utf-8') as file:
                content = file.read().strip()
                if content:
                    articles = json.loads(content)
                    logger.info(f"Loaded {len(articles)} articles from articles.json")
                    
                    # Save articles to database
                    from crawler.coin_articles_source import save_articles
                    save_articles(articles)
                    return True
                else:
                    logger.warning("articles.json was empty")
                    return False
        except FileNotFoundError:
            logger.error("articles.json was not created by the crawler")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing articles.json: {e}")
            return False
                
    except Exception as e:
        logger.error(f"Error running Coin68 crawler: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# Now fix the call to this function in run_cron_job
def run_cron_job():
    """Main function to run the crawler and process data"""
    start_time = time.time()
    job_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    logger.info(f"Starting crawler job {job_id}")
    
    try:
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
            save_fear_and_greed(fear_and_greed)
            
            # 2. Crawl coin data
            logger.info(f"Fetching data for top {COIN_NUMBER} coins...")
            coins = fetch_coin_data(limit=COIN_NUMBER, convert="USD")
            save_coin_data(coins)
            
            # 3. Crawl crypto news articles (English)
            logger.info(f"Fetching {ARTICLE_EN} English articles...")
            articles = fetch_articles_data(limit=ARTICLE_EN)
            update_article(driver, articles)
            save_articles(articles)
            
            # 4. Crawl Coin68 (Vietnamese articles)
            logger.info(f"Fetching {ARTICLE_VI} Vietnamese articles from Coin68...")
            # FIX: Pass the driver to the function
            success = run_coin68_crawler(driver)
            if success:
                logger.info("Coin68 crawler completed successfully")
            else:
                logger.warning("Coin68 crawler failed or partially failed")
                    
            # 5. Process the data for the Economic AGENT
            logger.info("Processing and embedding articles for RAG system...")
            new_articles_count = process_data_for_embedding()
            
            # 6. Force embedding of all unembedded articles
            logger.info("Forcing embedding of all processed articles...")
            # Keep embedding until no more articles need to be embedded
            total_embedded = 0
            for _ in range(3):  # Try up to 3 times to catch all articles
                embedded_count = update_embeddings(standalone_mode=True)
                total_embedded += embedded_count
                if embedded_count == 0:
                    break  # No more articles to embed
            
            if total_embedded > 0:
                logger.info(f"Successfully embedded {total_embedded} articles")
            else:
                logger.info("No new articles needed embedding")
            
            # 7. Verify embedding status
            conn = connect_db()
            cursor = conn.cursor()
            
            # Check unembedded articles count
            cursor.execute("SELECT COUNT(*) FROM articles WHERE embedded = 0 AND summary IS NOT NULL")
            remaining_count = cursor.fetchone()[0]
            
            if remaining_count > 0:
                logger.warning(f"There are still {remaining_count} articles that need embedding")
                # Try one more time for any remaining articles
                update_embeddings(standalone_mode=True)
            else:
                logger.info("All processed articles have been successfully embedded")
            
            cursor.close()
            conn.close()
            
            elapsed_time = time.time() - start_time
            logger.info(f"Crawler job {job_id} completed successfully in {elapsed_time:.2f} seconds")
            
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