#!/usr/bin/env python3
"""
setup.py - Setup script for the integrated Crypto News Assistant

This script:
1. Sets up the environment (.env file)
2. Installs dependencies
3. Initializes the database
4. Verifies all components
5. Sets up the cron job for automated crawling

Usage:
    python setup.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import getpass
from datetime import datetime

# Constants
PROJECT_DIR = Path(__file__).resolve().parent
ENV_EXAMPLE = PROJECT_DIR / ".env.example"
ENV_FILE = PROJECT_DIR / ".env"
REQUIREMENTS_FILE = PROJECT_DIR / "requirements.txt"
CRON_SCRIPT = PROJECT_DIR / "cron_job.py"

def print_banner():
    """Print a welcome banner"""
    print("\n" + "="*80)
    print(" Crypto News Assistant - Setup".center(80))
    print(" Integrated Crawler and RAG System".center(80))
    print("="*80 + "\n")

def check_python_version():
    """Check if Python version is compatible"""
    print("Checking Python version...")
    major, minor = sys.version_info.major, sys.version_info.minor
    if major < 3 or (major == 3 and minor < 8):
        print(f"❌ Error: Python 3.8+ is required. You have {major}.{minor}")
        sys.exit(1)
    print(f"✅ Python version {major}.{minor} is compatible\n")

def setup_env_file():
    """Set up the .env file with configuration"""
    if ENV_FILE.exists():
        print(f"🔍 Existing .env file found at {ENV_FILE}")
        overwrite = input("Do you want to overwrite it? (y/N): ").lower() == 'y'
        if not overwrite:
            print("➡️ Using existing .env file\n")
            return
    
    if not ENV_EXAMPLE.exists():
        print(f"❌ Error: .env.example file not found at {ENV_EXAMPLE}")
        sys.exit(1)
    
    print("\n" + "="*50)
    print(" Environment Configuration ".center(50))
    print("="*50)
    print("Please provide the following configuration values:")
    
    # Load template from .env.example
    with open(ENV_EXAMPLE, 'r') as f:
        env_template = f.read()
    
    # Database configuration
    print("\n--- Database Configuration ---")
    db_host = input("Database Host (default: localhost): ") or "localhost"
    db_user = input("Database User (default: root): ") or "root"
    db_password = getpass.getpass("Database Password: ")
    db_name = input("Database Name (default: news_crawler): ") or "news_crawler"
    
    # API Keys
    print("\n--- API Keys ---")
    api_key_coinmarketcap = getpass.getpass("CoinMarketCap API Key (press Enter to skip): ")
    api_key_cryptopanic = getpass.getpass("CryptoPanic API Key (press Enter to skip): ")
    api_key_diffbot = getpass.getpass("Diffbot API Key (press Enter to skip): ")
    openai_api_key = getpass.getpass("OpenAI API Key (press Enter to skip): ")
    
    # Crawler settings
    print("\n--- Crawler Settings ---")
    coin_number = input("Number of coins to crawl (default: 1000): ") or "1000"
    article_en = input("Number of English articles to crawl (default: 50): ") or "50"
    article_vi = input("Number of Vietnamese articles to crawl (default: 200): ") or "200"
    
    # Create .env file with user values
    env_content = f"""# Database Configuration
DB_HOST={db_host}
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_NAME={db_name}

# API Keys
API_KEY_COINMARKETCAP={api_key_coinmarketcap}
API_KEY_CRYPTOPANIC={api_key_cryptopanic}
API_KEY_DIFFBOT={api_key_diffbot}
OPENAI_API_KEY={openai_api_key}

# Crawler Settings
COIN_NUMBER={coin_number}
ARTICLE_EN={article_en}
ARTICLE_VI={article_vi}
RESET_DATABASE=False
CRAWL_INTERVAL_MINUTES=15

# RAG Settings
EMBEDDING_MODEL=all-MiniLM-L6-v2
OPENAI_CHAT_MODEL=gpt-3.5-turbo
MAX_SEARCH_RESULTS=5
MAX_TOKENS_RESPONSE=500
TEMPERATURE=0.3

# Server Settings
HOST=0.0.0.0
PORT=8000
RELOAD=False
DEBUG=False
LOG_LEVEL=INFO
"""
    
    # Write to .env file
    with open(ENV_FILE, 'w') as f:
        f.write(env_content)
    
    print(f"✅ .env file created at {ENV_FILE}\n")

def setup_virtual_env():
    """Set up Python virtual environment"""
    venv_dir = PROJECT_DIR / ".venv"
    
    if venv_dir.exists():
        print("🔍 Existing virtual environment found")
        activate_script = "source .venv/bin/activate" if os.name != 'nt' else r".venv\Scripts\activate"
        print(f"➡️ To activate it, run: {activate_script}\n")
        return
    
    print("Setting up virtual environment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print(f"✅ Virtual environment created at {venv_dir}\n")
        
        # Get the path to the pip in the virtual environment
        if os.name == 'nt':  # Windows
            pip_path = venv_dir / "Scripts" / "pip"
        else:  # Unix/Mac
            pip_path = venv_dir / "bin" / "pip"
        
        # Print activation instructions
        if os.name == 'nt':
            activate_cmd = r".venv\Scripts\activate"
        else:
            activate_cmd = "source .venv/bin/activate"
        
        print(f"➡️ To activate the virtual environment, run: {activate_cmd}")
        print(f"➡️ Then install requirements: pip install -r {REQUIREMENTS_FILE}\n")
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating virtual environment: {e}")
        sys.exit(1)

def setup_cron_job():
    """Set up cron job for automated crawling"""
    if os.name == 'nt':  # Windows
        print("ℹ️ Cron jobs are not supported on Windows.")
        print("➡️ To run the crawler periodically, you can use Windows Task Scheduler:")
        print(f"   Create a task that runs {CRON_SCRIPT} every 15 minutes.\n")
        return
    
    print("Setting up cron job for automated crawling...")
    
    # Get absolute paths
    python_path = sys.executable
    cron_script_path = CRON_SCRIPT.absolute()
    log_dir = PROJECT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "crawler.log"
    
    # Create cron job line
    cron_line = f"*/15 * * * * {python_path} {cron_script_path} >> {log_file} 2>&1\n"
    
    # Add to crontab
    try:
        # Get existing crontab
        process = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_crontab = process.stdout
        
        # Check if our job is already there
        if cron_script_path.name in current_crontab:
            print("ℹ️ Cron job already exists. Skipping...")
            return
        
        # Add our job
        new_crontab = current_crontab + cron_line
        
        # Write to temporary file
        temp_file = PROJECT_DIR / f"temp_crontab_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        with open(temp_file, 'w') as f:
            f.write(new_crontab)
        
        # Install new crontab
        subprocess.run(["crontab", str(temp_file)], check=True)
        
        # Remove temporary file
        temp_file.unlink()
        
        print(f"✅ Cron job added: Crawler will run every 15 minutes")
        print(f"✅ Logs will be written to: {log_file}\n")
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up cron job: {e}")
        print("➡️ You can manually add this line to your crontab (using crontab -e):")
        print(f"   {cron_line}\n")

def check_mysql():
    """Check if MySQL is installed and accessible"""
    print("Checking MySQL installation...")
    try:
        # Try to execute mysql --version command
        process = subprocess.run(["mysql", "--version"], capture_output=True, text=True)
        if process.returncode == 0:
            print(f"✅ MySQL is installed: {process.stdout.strip()}\n")
        else:
            raise Exception("Command returned non-zero exit code")
    except Exception as e:
        print("⚠️ Warning: Could not verify MySQL installation.")
        print("➡️ Please ensure MySQL is installed and running.\n")

def main():
    """Main setup function"""
    print_banner()
    check_python_version()
    check_mysql()
    setup_env_file()
    setup_virtual_env()
    setup_cron_job()
    
    print("\n" + "="*80)
    print(" Setup Complete ".center(80))
    print("="*80)
    print("\nNext steps:")
    print("1. Activate the virtual environment")
    print("2. Install requirements: pip install -r requirements.txt")
    print("3. Run the application: python app.py")
    print("4. Access the web interface at http://localhost:8000")
    print("\nThe crawler will run automatically every 15 minutes, or you can run it manually:")
    print("   python cron_job.py\n")

if __name__ == "__main__":
    main()