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

def run_coin68_crawler(driver):
    """Run the Coin68 crawler to fetch Vietnamese articles"""
    logger.info("Running Coin68 crawler...")
    
    try:
        # Extract the user data directory from the driver
        user_data_dir = None
        for option in driver.options.arguments:
            if option.startswith('--user-data-dir='):
                user_data_dir = option.split('=', 1)[1]
                break
        
        if not user_data_dir:
            logger.error("Could not find user data directory in Chrome options")
            return False
        
        # Run the crawler using subprocess
        logger.info("Running Coin68 crawler via subprocess...")
        scrapy_path = os.path.join(project_dir, "coin68_crawler")
        
        if not os.path.exists(scrapy_path):
            logger.error(f"Coin68 crawler directory not found at {scrapy_path}")
            return False
        
        # Set up environment variables including the Chrome profile path
        env = os.environ.copy()
        env["CHROME_USER_DATA_DIR"] = user_data_dir
        
        # Run the crawler
        command = [
            sys.executable, 
            "-m", 
            "scrapy", 
            "crawl", 
            "coin68_content", 
            "-a", 
            f"target_count={ARTICLE_VI}",
            "-a",
            f"user_data_dir={user_data_dir}"
        ]
        
        result = subprocess.run(
            command,
            cwd=scrapy_path,
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Coin68 crawler subprocess completed successfully")
            logger.info(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"Coin68 crawler subprocess failed with code {result.returncode}")
            logger.error(f"Error: {result.stderr}")
            return False
                
    except Exception as e:
        logger.error(f"Error running Coin68 crawler: {str(e)}")
        logger.error(traceback.format_exc())
        return False

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
            success = run_coin68_crawler()  # No longer passing the driver
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