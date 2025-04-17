# Crypto News Assistant

A comprehensive crypto news assistant with integrated web crawler and RAG-based chatbot. The system automatically collects real-time cryptocurrency data and news, processes it using natural language processing, and makes it accessible through an intelligent conversational interface.

## Features

- **Automated News Collection**: Crawls multiple cryptocurrency news sources every 15 minutes (configurable)
- **Multi-language Support**: Handles both English and Vietnamese news sources
- **Market Data Integration**: Collects real-time coin data and market sentiment indicators
- **Advanced RAG Chatbot**: Uses relevance-based document retrieval and answer checking
- **Responsive Web Interface**: Dashboard with latest news, charts, and user-friendly chat

## System Components

The system consists of three main components:

1. **Crawler System**:
   - Multiple data sources (CoinMarketCap, CryptoPanic, Coin68)
   - Scheduled crawling with configurable intervals
   - Content extraction and processing

2. **RAG System**:
   - Local embedding model for document vectorization
   - Vector-based similarity search
   - Advanced relevance checking for high-quality responses
   - Seamless fallback to general knowledge

3. **Web Interface**:
   - Interactive chat with history management
   - Market sentiment dashboard
   - Real-time coin data
   - Latest news with search functionality

## Installation

### Prerequisites

- Python 3.11 or later
- MySQL database
- Chrome browser (for web scraping)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/crypto-news-assistant.git
cd crypto-news-assistant
```

### Step 2: Run the Setup Script

The setup script will:
- Configure your environment variables
- Set up virtual environment
- Configure the cron job for automated crawling

```bash
python3.11 setup.py
```

Follow the prompts to configure your database connections, API keys, and crawler settings.

### Step 3: Install Dependencies

Activate the virtual environment and install the required dependencies:

```bash
# Activate virtual environment
source .venv/bin/activate  # On Linux/Mac
# OR
.venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Start the Application

```bash
python app.py
```

Then access the web interface at http://localhost:8000

## Configuration

All configuration is handled through the `.env` file created during setup. Key settings include:

- **Database settings**: Connection parameters for MySQL
- **API keys**: Keys for CoinMarketCap, CryptoPanic, Diffbot, and OpenAI
- **Crawler settings**:
  - `COIN_NUMBER`: Number of coins to track (default: 1000)
  - `ARTICLE_EN`: Number of English articles to crawl (default: 50)
  - `ARTICLE_VI`: Number of Vietnamese articles to crawl (default: 200)
  - `CRAWL_INTERVAL_MINUTES`: How often to run the crawler (default: 15 minutes)
  - `RESET_DATABASE`: Whether to reset the database on startup (default: false)
- **RAG settings**:
  - `EMBEDDING_MODEL`: Model to use for text embeddings
  - `OPENAI_CHAT_MODEL`: OpenAI model for text generation
  - `MAX_SEARCH_RESULTS`: Number of documents to retrieve per query
  - `TEMPERATURE`: Creativity parameter for the LLM

## Manual Crawling

You can trigger a manual crawl at any time:

```bash
python cron_job.py
```

Or use the "Trigger Manual Crawl" button in the web interface.

## Usage Examples

### Asking About Crypto News

You can ask the assistant questions like:
- "What's the current price of Bitcoin?"
- "What's the latest news about Ethereum?"
- "Explain the recent market trends in DeFi"
- "What's causing the current market sentiment?"

### Using the Dashboard

The dashboard provides:
- Real-time market sentiment indicator
- Top cryptocurrency prices and trends
- System status and embedding statistics
- Latest news articles with search functionality

## Customization

### Adding New News Sources

To add a new news source, create a new crawler module in the `crawler/` directory and import it in `cron_job.py`.

### Modifying RAG Behavior

The RAG system can be customized by:
- Changing embedding models in `.env`
- Adjusting relevance thresholds in `core/chatbot.py`
- Modifying document retrieval in `rag/vector_store.py`

## Troubleshooting

### Database Issues

If you encounter database connection issues:
1. Verify database credentials in `.env`
2. Ensure MySQL service is running
3. Check database logs for errors

### Crawler Issues

If the crawler isn't working:
1. Verify Chrome is installed
2. Check if API keys are valid in `.env`
3. Look for errors in the `logs/crawler.log` file

### RAG System Issues

If the RAG system isn't providing good answers:
1. Verify OpenAI API key is valid
2. Check embedding status in the dashboard
3. Look for errors in the application logs

## License

This project is licensed under the MIT License - see the LICENSE file for details.