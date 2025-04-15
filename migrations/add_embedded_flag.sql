-- SQL migration to add embedded flag and indexes to the articles table
-- Run this on an existing database to update the schema for RAG integration

-- Check if the embedded column exists, add it if not
SET @columnExists = 0;
SELECT COUNT(*) INTO @columnExists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'articles' 
AND COLUMN_NAME = 'embedded';

SET @sqlStatement = IF(@columnExists = 0, 
    'ALTER TABLE articles ADD COLUMN embedded TINYINT DEFAULT 0',
    'SELECT "Column embedded already exists in articles table"');

PREPARE stmt FROM @sqlStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index on embedded column if it doesn't exist
SET @indexExists = 0;
SELECT COUNT(*) INTO @indexExists 
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'articles' 
AND INDEX_NAME = 'idx_articles_embedded';

SET @sqlStatement = IF(@indexExists = 0, 
    'CREATE INDEX idx_articles_embedded ON articles(embedded)',
    'SELECT "Index idx_articles_embedded already exists"');

PREPARE stmt FROM @sqlStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index on published_at column if it doesn't exist
SET @indexExists = 0;
SELECT COUNT(*) INTO @indexExists 
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'articles' 
AND INDEX_NAME = 'idx_articles_published_at';

SET @sqlStatement = IF(@indexExists = 0, 
    'CREATE INDEX idx_articles_published_at ON articles(published_at)',
    'SELECT "Index idx_articles_published_at already exists"');

PREPARE stmt FROM @sqlStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Reset all articles as not embedded
UPDATE articles SET embedded = 0 WHERE embedded IS NULL OR embedded = 1;

-- Output migration results
SELECT 
    (SELECT COUNT(*) FROM articles) AS total_articles,
    (SELECT COUNT(*) FROM articles WHERE embedded = 1) AS embedded_articles,
    (SELECT COUNT(*) FROM articles WHERE embedded = 0) AS non_embedded_articles;