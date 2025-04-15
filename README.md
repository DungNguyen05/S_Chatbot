# Crypto News Assistant

An integrated system that combines a cryptocurrency news crawler with an advanced RAG-based chatbot. This system automatically crawls for the latest crypto news every 15 minutes and makes it available for intelligent retrieval and response generation.

## Features

- **Automated News Collection**: Crawls cryptocurrency news sources every 15 minutes
- **Real-time Market Data**: Fetches cryptocurrency prices and market sentiment
- **Intelligent RAG System**: Uses relevance-based retrieval to provide accurate answers
- **Context-Aware Responses**: Understands conversation context and query relevance
- **Modern Web Interface**: Dashboard with latest news, sentiment indicators, and more

## System Architecture

The system consists of three main components:

1. **Crawler System**: Automatically fetches news articles, coin data, and market sentiment
2. **RAG System**: Processes, embeds, and retrieves relevant news based on user queries
3. **Web Interface**: Provides a user-friendly way to interact with the system

## Installation

### Prerequisites

- Python 3.8 or later
- MySQL database
- Chrome browser (for web scraping)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/crypto-news-assistant.git
   cd crypto-news-assistant
   ```

2. Run the setup script:
   ```
   python setup.py
   ```
   
   This will:
   - Create a virtual environment
   - Set up configuration in `.env`
   - Configure the cron job for automated crawling

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```
   python migrations/migrate_database.py
   ```

5. Start the application:
   ```
   python app.py
   ```

6. Access the web interface at http://localhost:8000

## Configuration

All configuration is handled in the `.env` file. Key settings include:

- Database connection details
- API keys for CoinMarketCap, CryptoPanic, etc.
- Crawler settings (number of articles, coins, etc.)
- RAG system settings (embedding model, search results, etc.)

## Usage

### Web Interface

The web interface provides:
- A chat interface to ask questions about crypto news
- A dashboard with market data and sentiment indicators
- Latest news articles
- System settings

### Chat Examples

You can ask the assistant questions like:
- "What's the current price of Bitcoin?"
- "What's the latest news about Ethereum?"
- "Explain the recent market trends in DeFi"
- "What's causing the current market sentiment?"

### Manual Crawling

You can trigger a manual crawl from the web interface or by running:
```
python cron_job.py
```

## Cron Job Setup

The system is designed to run a crawler job every 15 minutes. This is set up automatically by the setup script on Unix-based systems. On Windows, you'll need to use Task Scheduler.

The cron job runs:
```
*/15 * * * * /path/to/python /path/to/crypto-news-assistant/cron_job.py >> /path/to/logs/crawler.log 2>&1
```

## Project Structure

```
crypto_news_assistant/
├── api/                      # API endpoints
├── core/                     # Core RAG components
├── crawler/                  # Crawler components
├── coin68_crawler/           # Specific crawler for Coin68
├── migrations/               # Database migrations
├── rag/                      # RAG system components
├── static/                   # Frontend assets
├── templates/                # HTML templates
├── web/                      # Web routes
├── app.py                    # Main application
├── config.py                 # Configuration
├── cron_job.py               # Crawler automation
├── data_processor.py         # Data processing
├── database.py               # Database access
├── integration_manager.py    # Integration between components
├── setup.py                  # Setup script
└── requirements.txt          # Dependencies
```

## Customization

### Adding New News Sources

To add a new news source, you'll need to:
1. Create a new crawler module in the `crawler/` directory
2. Implement the fetching and parsing logic
3. Update the `cron_job.py` script to include the new source

### Modifying the RAG System

The RAG system can be customized by:
1. Changing the embedding model in `config.py`
2. Modifying the relevance checking in `core/chatbot.py`
3. Adjusting the search parameters in `rag/vector_store.py`

## Troubleshooting

### Database Connection Issues

If you encounter database connection issues:
1. Verify the credentials in `.env`
2. Ensure MySQL is running
3. Check if the database exists and is accessible

### Crawler Issues

If the crawler isn't working:
1. Verify Chrome is installed
2. Check if API keys are valid
3. Look for errors in the crawler logs

### RAG System Issues

If the RAG system isn't providing good answers:
1. Check if articles are being embedded (see status in dashboard)
2. Verify embedding model is loading correctly
3. Adjust relevance threshold in `core/chatbot.py`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.