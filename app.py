# app.py - Integrated FastAPI application with crypto news crawler and RAG system
import os
import logging
import sys
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import configuration
import config

# Import components
from rag.embeddings import EmbeddingsManager
from rag.vector_store import QdrantStore
from core.document_manager import DocumentManager
from core.chatbot import Chatbot
from web.templates_manager import create_templates
from database import setup_database
from integration_manager import check_embedding_status
from config import RESET_DATABASE
# Import routers
from api.routes import router as api_router
from web.routes import router as web_router

# Global variables to manage application state
embeddings_manager = None
vector_store = None
document_manager = None
chatbot = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    global embeddings_manager, vector_store, document_manager, chatbot
    
    # Startup logic
    try:
        # Set up the database
        setup_database(reset_data=RESET_DATABASE)
        
        # Verify templates exist
        create_templates()
        
        # Initialize embeddings manager
        try:
            logger.info("Initializing embeddings manager...")
            embeddings_manager = EmbeddingsManager()
        except Exception as e:
            logger.error(f"Failed to initialize embeddings manager: {e}")
            raise
        
        # Initialize vector store
        try:
            logger.info("Initializing vector store...")
            vector_store = QdrantStore(embeddings_manager)
        except Exception as e:
            logger.warning(f"Standard initialization failed: {e}")
            logger.info("Attempting initialization with force reset...")
            vector_store = QdrantStore(embeddings_manager, force_reset=True)
        
        # Initialize document manager
        logger.info("Initializing document manager...")
        document_manager = DocumentManager(vector_store)
        
        # Initialize chatbot
        logger.info("Initializing chatbot with advanced RAG...")
        chatbot = Chatbot(document_manager, vector_store)
        
        # Log configuration
        logger.info(f"Using local embedding model: {config.EMBEDDING_MODEL}")
        logger.info(f"Using OpenAI chat model: {config.OPENAI_CHAT_MODEL}")
        logger.info(f"Chunk size: {config.CHUNK_SIZE}, Chunk overlap: {config.CHUNK_OVERLAP}")
        
        # Check embedding status
        status = check_embedding_status()
        logger.info(f"Embedding status: {status}")
        
        # Check OpenAI API key
        if not config.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set. Set this environment variable for chat functionality.")
        
        logger.info("Integrated application started successfully")
        yield  # This is where the application runs
    
    finally:
        # Cleanup logic
        logger.info("Application is shutting down")

# Initialize FastAPI application with lifespan context
app = FastAPI(
    title="Crypto News Assistant",
    description="An integrated crypto assistant with real-time news crawler and advanced RAG",
    version="1.0.0",
    debug=config.DEBUG,
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

# Include routers
app.include_router(api_router)
app.include_router(web_router)

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "app:app", 
        host=config.HOST, 
        port=config.PORT, 
        reload=config.RELOAD
    )