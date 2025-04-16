"""
Database module for Crypto News Crawler and Economic AGENT integration.
Handles database connections and schema setup.
"""
import mysql.connector
from config import DB_CONFIG


def connect_db():
    """
    Establish a connection to the MySQL database.
    
    Returns:
        Connection object or None if connection fails
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Error connecting to database: {err}")
        return None


def drop_all_tables():
    """
    Drop all tables from the database.
    
    Returns:
        bool: True if successful, False otherwise
    """
    tables = ['articles', 'coin_data', 'fear_and_greed']
    conn = connect_db()
    if not conn:
        return False
        
    cursor = conn.cursor()
    success = True
    
    try:
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        conn.commit()
        print("✅ All tables dropped successfully!")
        return success
    except mysql.connector.Error as err:
        print(f"❌ Error dropping tables: {err}")
        return False
    finally:
        cursor.close()
        conn.close()


def setup_database(reset_data=False):
    """
    Set up the database schema.
    
    Args:
        reset_data (bool): Whether to reset the database by dropping all tables
    """
    if reset_data:
        drop_all_tables()
    
    conn = connect_db()
    if not conn:
        print("❌ Could not connect to the database.")
        return
        
    cursor = conn.cursor()

    # Create articles table with embedded column
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INT AUTO_INCREMENT PRIMARY KEY, 
            title VARCHAR(1000),
            url TEXT,
            source VARCHAR(50),
            published_at DATETIME,
            currencies VARCHAR(255),
            content TEXT,
            summary TEXT,
            embedded TINYINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create coin_data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coin_data (
            id INT AUTO_INCREMENT PRIMARY KEY, 
            name VARCHAR(100),
            symbol VARCHAR(10),
            price DECIMAL(18, 8),
            market_cap BIGINT,
            volume_24h BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create fear_and_greed table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fear_and_greed (
            id INT AUTO_INCREMENT PRIMARY KEY,
            value INT,
            value_classification VARCHAR(50),
            update_time DATETIME,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add indexes for better performance with the RAG system
    try:
        # Check if index already exists to avoid duplicate index errors
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.statistics 
            WHERE table_schema = DATABASE() 
            AND table_name = 'articles' 
            AND index_name = 'idx_articles_embedded'
        """)
        exists = cursor.fetchone()[0]
        
        if not exists:
            cursor.execute("CREATE INDEX idx_articles_embedded ON articles(embedded)")
        
        # Check if published_at index exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.statistics 
            WHERE table_schema = DATABASE() 
            AND table_name = 'articles' 
            AND index_name = 'idx_articles_published_at'
        """)
        exists = cursor.fetchone()[0]
        
        if not exists:
            cursor.execute("CREATE INDEX idx_articles_published_at ON articles(published_at)")
        
        conn.commit()
        print("✅ Indexes created successfully")
    except Exception as e:
        print(f"⚠️ Warning: Could not create indexes: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database setup completed!")