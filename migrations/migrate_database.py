#!/usr/bin/env python3
"""
migrate_database.py - Database migration script for the integrated system

This script runs SQL migrations to update the database schema for the
integration between the crawler and RAG system.

Usage:
    python migrations/migrate_database.py
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to sys.path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database connection
from database import connect_db, setup_database

def run_migration(migration_file):
    """Run a SQL migration file"""
    logger.info(f"Running migration: {migration_file}")
    
    try:
        # Read migration file
        with open(migration_file, 'r') as f:
            sql_script = f.read()
        
        # Connect to the database
        conn = connect_db()
        if not conn:
            logger.error("Failed to connect to database")
            return False
        
        cursor = conn.cursor()
        
        # Execute migration script
        # Split by semicolon to execute multiple statements
        statements = sql_script.split(';')
        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                    conn.commit()
                except Exception as e:
                    logger.error(f"Error executing SQL: {statement.strip()}")
                    logger.error(f"Error message: {e}")
                    conn.rollback()
        
        # Close connection
        cursor.close()
        conn.close()
        
        logger.info(f"Migration completed successfully: {migration_file}")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def migrate_database():
    """Run all migrations and ensure database structure is setup"""
    logger.info("Starting database migrations")
    
    # First ensure database tables exist
    setup_database(reset_data=False)
    
    # Get migration directory
    migrations_dir = Path(__file__).parent
    
    # List SQL migration files
    migration_files = sorted([f for f in migrations_dir.glob("*.sql")])
    
    if not migration_files:
        logger.warning("No migration files found")
        return
    
    logger.info(f"Found {len(migration_files)} migration files")
    
    # Run each migration
    for migration_file in migration_files:
        success = run_migration(migration_file)
        if not success:
            logger.error(f"Migration failed: {migration_file}")
            return
    
    logger.info("All migrations completed successfully")

if __name__ == "__main__":
    migrate_database()