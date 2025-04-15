# rag/embeddings.py - Embeddings manager for local model handling
import os
import logging
import torch
from langchain_community.embeddings import HuggingFaceEmbeddings

import config

logger = logging.getLogger(__name__)

class EmbeddingsManager:
    """Manages embedding models with Langchain integration"""
    
    def __init__(self):
        """Initialize the embeddings manager with the configured model"""
        logger.info(f"Initializing embeddings manager with model: {config.EMBEDDING_MODEL}")
        
        # Set up cache directories
        torch.hub.set_dir(os.path.join(config.DATA_DIR, "torch_hub_cache"))
        os.makedirs(os.path.join(config.DATA_DIR, "transformers_cache"), exist_ok=True)
        
        # Configure model parameters
        model_kwargs = {'device': 'cpu'}
        encode_kwargs = {'normalize_embeddings': True}
        
        try:
            # Initialize the embedding model with Langchain
            self.embedding_model = HuggingFaceEmbeddings(
                model_name=config.EMBEDDING_MODEL,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs,
                cache_folder=os.path.join(config.DATA_DIR, "transformers_cache")
            )
            
            # Test the model and get dimension
            test_embedding = self.embedding_model.embed_query("test")
            self.dimension = len(test_embedding)
            logger.info(f"Embedding model initialized successfully. Dimension: {self.dimension}")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def get_embeddings(self):
        """Return the Langchain embeddings object"""
        return self.embedding_model
    
    def get_dimension(self):
        """Return the embedding dimension"""
        return self.dimension