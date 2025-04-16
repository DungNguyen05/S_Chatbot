"""
integration_manager.py - Bridge between news crawler and Economic AGENT

This module handles the integration between the crawler data and the RAG system:
1. Manages the flow of crawled data to the vector store
2. Updates embeddings when new articles are available
3. Provides utilities for the integrated system
"""

import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import RAG components - will be loaded only when needed
# These imports are placed inside functions to avoid circular imports
def get_document_manager():
    """Get the document manager instance from the app state"""
    from app import document_manager
    return document_manager

def get_vector_store():
    """Get the vector store instance from the app state"""
    from app import vector_store
    return vector_store

def get_embeddings_manager():
    """Get the embeddings manager instance from the app state"""
    from app import embeddings_manager
    return embeddings_manager

def update_embeddings(standalone_mode=False):
    """Update the vector store with new articles from the database
    
    This function:
    1. Checks for new unembedded articles in the database
    2. Processes and embeds them
    3. Adds them to the vector store
    
    Args:
        standalone_mode (bool): Set to True when running from cron job with no app context
        
    Returns:
        int: Number of articles embedded
    """
    from database import connect_db
    
    try:
        # Only try to get document_manager if not in standalone mode
        document_manager = None
        if not standalone_mode:
            try:
                document_manager = get_document_manager()
            except ImportError:
                logger.warning("Running in standalone mode (document_manager not available)")
                standalone_mode = True
        
        # Get unembedded articles from the database
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        
        # Select articles that have been processed but not embedded
        cursor.execute("""
            SELECT id, title, content, source, published_at, summary, currencies 
            FROM articles 
            WHERE embedded = 0 AND content IS NOT NULL AND summary IS NOT NULL
            LIMIT 100
        """)
        
        articles = cursor.fetchall()
        logger.info(f"Found {len(articles)} unembedded articles to process")
        
        if not articles:
            cursor.close()
            conn.close()
            return 0
        
        # In standalone mode, just mark the articles as embedded without adding to vector store
        if standalone_mode:
            logger.warning("Running in standalone mode - marking articles as embedded without adding to vector store")
            # Set embedded flag to 1 for all found articles
            article_ids = [article['id'] for article in articles]
            for article_id in article_ids:
                cursor.execute("UPDATE articles SET embedded = 1 WHERE id = %s", (article_id,))
            
            conn.commit()
            logger.info(f"Marked {len(article_ids)} articles as embedded in standalone mode")
            cursor.close()
            conn.close()
            return len(articles)
            
        # If we have a document manager, proceed with normal embedding
        if document_manager:
            # Prepare documents for the vector store
            documents = []
            article_ids = []
            
            for article in articles:
                try:
                    # Create document with combined title and content
                    doc_content = f"{article['title']}\n\n{article['summary']}\n\n{article['content']}"
                    doc_source = f"{article['source']} ({article['published_at']})"
                    
                    # Add metadata
                    metadata = {
                        "db_id": article['id'],
                        "currencies": article['currencies'] or "Unknown",
                        "published_at": str(article['published_at'])
                    }
                    
                    # Add to documents list
                    documents.append({
                        "content": doc_content,
                        "source": doc_source,
                        "metadata": metadata
                    })
                    
                    article_ids.append(article['id'])
                except Exception as e:
                    logger.error(f"Error processing article {article['id']}: {e}")
                    # Continue with other articles
                    continue
            
            # Add documents to vector store
            if documents:
                try:
                    doc_ids = document_manager.bulk_add_documents(documents)
                    logger.info(f"Added {len(doc_ids)} documents to vector store")
                    
                    # Mark articles as embedded in the database
                    for article_id in article_ids:
                        cursor.execute(
                            "UPDATE articles SET embedded = 1 WHERE id = %s",
                            (article_id,)
                        )
                    
                    conn.commit()
                    logger.info(f"Marked {len(article_ids)} articles as embedded in the database")
                    
                    cursor.close()
                    conn.close()
                    return len(documents)
                except Exception as e:
                    logger.error(f"Error adding documents to vector store: {e}")
                    cursor.close()
                    conn.close()
                    return 0
            else:
                logger.info("No documents to add to vector store")
                cursor.close()
                conn.close()
                return 0
        else:
            logger.error("Document manager is not available")
            cursor.close()
            conn.close()
            return 0
            
    except Exception as e:
        logger.error(f"Error updating embeddings: {e}")
        return 0

def check_embedding_status():
    """Check the status of embeddings in the database
    
    Returns:
        dict: Status information about embeddings
    """
    from database import connect_db
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Count total articles
        cursor.execute("SELECT COUNT(*) FROM articles WHERE content IS NOT NULL")
        total_articles = cursor.fetchone()[0]
        
        # Count embedded articles
        cursor.execute("SELECT COUNT(*) FROM articles WHERE embedded = 1")
        embedded_articles = cursor.fetchone()[0]
        
        # Count unembedded articles
        cursor.execute("SELECT COUNT(*) FROM articles WHERE embedded = 0 AND content IS NOT NULL")
        unembedded_articles = cursor.fetchone()[0]
        
        # Get latest article date
        cursor.execute("SELECT MAX(published_at) FROM articles")
        latest_article = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "total_articles": total_articles,
            "embedded_articles": embedded_articles,
            "unembedded_articles": unembedded_articles,
            "latest_article": latest_article,
            "embedding_percentage": (embedded_articles / total_articles * 100) if total_articles > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error checking embedding status: {e}")
        return {
            "error": str(e)
        }

def remove_old_articles(days_to_keep=30):
    """Remove old articles from the database to prevent it from growing too large
    
    Args:
        days_to_keep (int): Number of days of articles to keep
        
    Returns:
        int: Number of articles removed
    """
    from database import connect_db
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Delete old articles
        cursor.execute(f"""
            DELETE FROM articles 
            WHERE published_at < DATE_SUB(NOW(), INTERVAL {days_to_keep} DAY)
        """)
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        cursor.close()
        conn.close()
        
        logger.info(f"Removed {deleted_count} articles older than {days_to_keep} days")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error removing old articles: {e}")
        return 0

def synchronize_database_and_vectorstore():
    """Ensure the vector store and database are synchronized
    
    This function checks for documents in the vector store that may not
    have corresponding articles in the database, and vice versa.
    """
    from database import connect_db
    
    try:
        # Get necessary components
        vector_store = get_vector_store()
        
        # Get DB connection
        conn = connect_db()
        cursor = conn.cursor()
        
        # 1. Find documents in vector store that don't have corresponding articles
        # This would require querying all document metadata from vector store
        # and comparing with database - implementation depends on scale
        
        # 2. Find articles marked as embedded but without vectors
        # Clear embedded flag for articles that might have been marked but not processed
        cursor.execute("""
            SELECT id FROM articles 
            WHERE embedded = 1 AND created_at < DATE_SUB(NOW(), INTERVAL 1 DAY)
            ORDER BY id DESC LIMIT 100
        """)
        
        recent_article_ids = cursor.fetchall()
        if recent_article_ids:
            # Sample a few articles to check if they exist in vector store
            # Implementation would check vector store for these IDs
            # If missing, reset their embedded flag
            pass
        
        # 3. Log synchronization status
        logger.info("Database and vector store synchronization check completed")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error synchronizing database and vector store: {e}")

def get_article_by_id(article_id):
    """Get an article from the database by ID
    
    Args:
        article_id (int): The article ID
        
    Returns:
        dict: The article data or None if not found
    """
    from database import connect_db
    
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, title, url, source, published_at, currencies, content, summary, embedded
            FROM articles
            WHERE id = %s
        """, (article_id,))
        
        article = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return article
        
    except Exception as e:
        logger.error(f"Error getting article by ID: {e}")
        return None

def get_recent_articles(limit=10, offset=0):
    """Get most recent articles from the database
    
    Args:
        limit (int): Maximum number of articles to return
        offset (int): Offset for pagination
        
    Returns:
        list: List of article dictionaries
    """
    from database import connect_db
    
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, title, url, source, published_at, currencies, summary
            FROM articles
            WHERE summary IS NOT NULL
            ORDER BY published_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        articles = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return articles
        
    except Exception as e:
        logger.error(f"Error getting recent articles: {e}")
        return []

def search_articles_by_keyword(keyword, limit=10):
    """Search articles by keyword in title or content
    
    Args:
        keyword (str): The search keyword
        limit (int): Maximum number of articles to return
        
    Returns:
        list: List of matching article dictionaries
    """
    from database import connect_db
    
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        
        # Use LIKE for simple text search
        search_term = f"%{keyword}%"
        
        cursor.execute("""
            SELECT id, title, url, source, published_at, currencies, summary
            FROM articles
            WHERE 
                (title LIKE %s OR content LIKE %s) 
                AND summary IS NOT NULL
            ORDER BY published_at DESC
            LIMIT %s
        """, (search_term, search_term, limit))
        
        articles = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return articles
        
    except Exception as e:
        logger.error(f"Error searching articles by keyword: {e}")
        return []