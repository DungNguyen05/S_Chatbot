"""
data_processor.py - Enhanced data processing for Economic AGENT

This is an enhanced version of the original data_processing.py that:
1. Processes raw articles into summaries
2. Translates non-English content to English
3. Prepares the data for embedding
4. Marks articles as ready for the RAG system
"""

import logging
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from nltk.tokenize.punkt import PunktSentenceTokenizer
from database import connect_db
from translatepy import Translator
from langdetect import detect
import os

# Make sure NLTK data directory exists
nltk_data_dir = os.path.expanduser('~/nltk_data')
if not os.path.exists(nltk_data_dir):
    os.makedirs(nltk_data_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Properly download NLTK punkt resources
try:
    nltk.download('punkt', quiet=True)
    # Explicitly download punkt_tab
    nltk.download('punkt_tab', quiet=True)
except Exception as e:
    logger.warning(f"NLTK download error: {e}")
    logger.info("Manual fix: Run the following command in your terminal:")
    logger.info("python -m nltk.downloader punkt")

def translate(text, lang):
    """
    Translate text to specified language.
    
    Args:
        text (str): Text to translate
        lang (str): Target language
        
    Returns:
        str: Translated text or None if translation fails
    """
    try:
        if text is None or text.strip() == "":
            return None

        translator = Translator()
        translation = translator.translate(text, lang)
        return translation.result
    except Exception as e:
        logger.warning(f"Translation error: {e}")
        return None

def extract_key_sentences(text):
    """
    Extract key sentences from different parts of the text to create a balanced summary.
    
    Args:
        text (str): Text to extract key sentences from
        
    Returns:
        list: Key sentences
    """
    # Split text into sentences with better handling of periods in abbreviations
    # First, temporarily replace periods in common abbreviations
    for abbr in ['Mr.', 'Mrs.', 'Dr.', 'Inc.', 'Ltd.', 'Co.', 'etc.', 'vs.', 'e.g.', 'i.e.', 'U.S.']:
        text = text.replace(abbr, abbr.replace('.', '<DOT>'))
    
    # Now split by actual sentence boundaries
    sentences = []
    for part in text.split('. '):
        # Restore the periods in abbreviations
        part = part.replace('<DOT>', '.')
        if part.strip():
            sentences.append(part.strip())
    
    if len(sentences) <= 3:
        return sentences
    
    # Select key sentences from beginning, middle and end
    key_sentences = []
    
    # First sentence is usually important
    key_sentences.append(sentences[0])
    
    # Select sentences from the middle that contain important keywords
    # Common keywords in crypto news articles
    keywords = ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'token', 'defi', 'nft', 
                'exchange', 'market', 'investment', 'trading', 'price', 'regulation',
                'mining', 'wallet', 'transaction', 'altcoin']
    
    # Find sentences in the middle containing keywords
    keyword_sentences = []
    middle_start = 1
    middle_end = len(sentences) - 1
    
    for i in range(middle_start, middle_end):
        sentence = sentences[i].lower()
        for keyword in keywords:
            if keyword in sentence:
                keyword_sentences.append(sentences[i])
                break
    
    # Take 1-3 sentences from the middle based on keywords
    middle_count = min(3, len(keyword_sentences))
    if middle_count > 0:
        # If we have keyword sentences, use them
        key_sentences.extend(keyword_sentences[:middle_count])
    else:
        # Otherwise take a sentence from the middle
        middle_idx = len(sentences) // 2
        key_sentences.append(sentences[middle_idx])
    
    # Last sentence often contains conclusions
    key_sentences.append(sentences[-1])
    
    # Deduplicate
    return list(dict.fromkeys(key_sentences))

def summarize_text(text, num_sentences=4):
    """
    Create a summary using extraction and keyword analysis.
    
    Args:
        text (str): Text to summarize
        num_sentences (int): Target number of sentences for summary
        
    Returns:
        str: Summarized text
    """
    try:
        if not text or len(text.split()) < 30:  # Don't summarize very short texts
            return text

        # Extract key sentences that cover the main points
        key_sentences = extract_key_sentences(text)
        
        # If we have few sentences, just return them all
        if len(key_sentences) <= num_sentences:
            return '. '.join(key_sentences) + '.'
            
        # Otherwise select the most important ones
        # Always include first and last sentences
        selected_sentences = [key_sentences[0]]
        
        # Calculate how many middle sentences to include
        middle_count = num_sentences - 2  # Subtract first and last
        
        # If we have middle sentences to include
        if middle_count > 0 and len(key_sentences) > 2:
            middle_sentences = key_sentences[1:-1]
            # Select middle sentences, preferring those with keywords
            selected_middle = middle_sentences[:middle_count]
            selected_sentences.extend(selected_middle)
        
        # Add the last sentence
        if len(key_sentences) > 1:
            selected_sentences.append(key_sentences[-1])
            
        # Join sentences and ensure proper formatting
        summary = '. '.join(selected_sentences)
        
        # Clean up: ensure we end with a period
        if not summary.endswith('.'):
            summary += '.'
            
        return summary
        
    except Exception as e:
        logger.error(f"Error during text summarization: {e}")
        # Ultimate fallback - extract first and last sentences
        try:
            parts = text.split('. ')
            if len(parts) <= 2:
                return text
            return parts[0] + '. ' + parts[-1] + '.'
        except:
            # If all else fails, return first 20% of the text
            return text[:int(len(text) * 0.2)]

def process_data():
    """
    Process articles and update them with English content, summaries, and embeddings flag.
    
    This function does the original work of data_processing.py with improvements:
    1. Translates content to English if needed
    2. Creates a summary of the content
    3. Marks articles as ready for embedding
    
    Returns:
        int: Number of articles processed
    """
    logger.info("Starting to process data")

    try:
        # Establish database connection
        conn = connect_db()
        cursor = conn.cursor()

        # Select unprocessed articles with content
        cursor.execute("""
            SELECT id, content, title 
            FROM articles 
            WHERE content IS NOT NULL AND summary IS NULL
            LIMIT 100
        """)
        articles = cursor.fetchall()

        processed_count = 0
        skipped = 0
        
        # Check NLTK resources before starting
        try:
            nltk.data.find('tokenizers/punkt_tab/english/')
            logger.info("NLTK resources verified")
        except LookupError:
            logger.warning("NLTK resources missing - attempting to download...")
            nltk.download('punkt', quiet=False)
            nltk.download('punkt_tab', quiet=False)

        for article_id, content, title in articles:
            try:
                if not content or len(content.strip()) < 50:  # Skip articles with minimal content
                    logger.info(f"Skipping article #{article_id}: Content too short or empty.")
                    skipped += 1
                    continue

                # Detect language and handle translation
                try:
                    content_language = detect(content)
                except:
                    # If language detection fails, assume English
                    content_language = "en"
                    logger.warning(f"Article #{article_id}: Language detection failed, assuming English")
                
                # Detect language for title
                try:
                    title_language = detect(title) if title else "en"
                except:
                    title_language = "en"
                    logger.warning(f"Article #{article_id}: Title language detection failed, assuming English")

                # Translate content if needed
                if content_language != "en":
                    content_en = translate(content, "English")
                    if content_en is None:
                        logger.info(f"Skipping article #{article_id}: Translation to English failed.")
                        skipped += 1
                        continue
                else:
                    content_en = content

                # Translate title if needed
                if title and title_language != "en":
                    title_en = translate(title, "English")
                    if title_en is None:
                        logger.warning(f"Article #{article_id}: Title translation failed, keeping original")
                        title_en = title
                else:
                    title_en = title

                # Clean up the content for better processing
                content_en = content_en.replace('\n', ' ').replace('  ', ' ')
                
                # Generate summary
                # summary_en = summarize_text(content_en, num_sentences=4)
                summary_en = content_en

                # Update database with translations, summary, and embedding status
                cursor.execute("""
                    UPDATE articles 
                    SET 
                        content = %s, 
                        title = %s, 
                        summary = %s, 
                        embedded = 0
                    WHERE id = %s
                """, (content_en, title_en, summary_en, article_id))

                processed_count += 1
                logger.info(f"Processed {processed_count}/{len(articles)} articles | Skipped: {skipped}")

            except Exception as e:
                logger.error(f"Error processing article #{article_id}: {e}")
                skipped += 1

        logger.info(f"Successfully processed {processed_count}/{len(articles)} articles | Skipped: {skipped}")

        # Commit changes and close the cursor and connection
        conn.commit()
        cursor.close()
        conn.close()
        
        return processed_count

    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return 0

def process_data_for_embedding():
    """
    Process articles specifically for embedding in the RAG system.
    This is a wrapper around process_data() that performs additional
    steps needed for embedding.
    
    Returns:
        int: Number of articles processed and ready for embedding
    """
    # Ensure database has the embedded column
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Add embedded column if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_NAME = 'articles' 
            AND COLUMN_NAME = 'embedded'
        """)
        if cursor.fetchone()[0] == 0:
            logger.info("Adding 'embedded' column to articles table")
            cursor.execute("ALTER TABLE articles ADD COLUMN embedded TINYINT DEFAULT 0")
            conn.commit()
    except Exception as e:
        logger.error(f"Error checking/adding embedded column: {e}")
    finally:
        cursor.close()
        conn.close()
    
    # Process articles normally
    processed_count = process_data()
    
    # Return the number processed
    return processed_count

# Direct execution
if __name__ == "__main__":
    process_data_for_embedding()