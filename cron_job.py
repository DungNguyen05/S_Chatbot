#!/usr/bin/env python3
"""
cron_job.py - Script to automate the news crawler execution on a schedule

This script is designed to be run by a cron job every 15 minutes. It:
1. Runs the crawler to fetch latest crypto news
2. Processes the data for the Economic AGENT
3. Logs operation details for monitoring

Usage:
    Set up a crontab entry:
    */15 * * * * /path/to/venv/bin/python /path/to/project/cron_job.py >> /path/to/logs/crawler.log 2>&1
"""

import os
import sys
import logging
import time
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

def run_cron_job():
    """Main function to run the crawler and process data"""
    start_time = time.time()
    job_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    logger.info(f"Starting crawler job {job_id}")
    
    try:
        # Initialize Chrome driver
        logger.info("Initializing Chrome WebDriver...")
        driver = create_chrome_driver(headless=True)
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
            
            # 4. Process the data for the Economic AGENT
            logger.info("Processing and embedding articles for RAG system...")
            new_articles_count = process_data_for_embedding()
            
            # 5. Update the vector store with new embeddings
            if new_articles_count > 0:
                logger.info(f"Updating vector store with {new_articles_count} new articles...")
                update_embeddings()
            
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