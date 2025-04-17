# rag/vector_store.py - Enhanced vector database using Qdrant with better similarity search
import os
import shutil
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from langchain_community.vectorstores import Qdrant
from langchain_core.documents import Document

import config
from rag.embeddings import EmbeddingsManager

logger = logging.getLogger(__name__)

class QdrantStore:
    """Enhanced vector store for document embeddings and retrieval using Qdrant with Langchain"""
    
    def __init__(self, embeddings_manager, collection_name="economic_documents", force_reset=False):
        """Initialize the vector store with Qdrant and Langchain"""
        logger.info(f"Initializing Qdrant vector store: {collection_name}")
        
        self.embeddings_manager = embeddings_manager
        self.collection_name = collection_name
        
        # Qdrant storage path
        self.qdrant_path = os.path.join(config.DATA_DIR, "qdrant_storage")
        
        # Optional force reset of the vector store
        if force_reset and os.path.exists(self.qdrant_path):
            logger.warning("Force resetting Qdrant storage...")
            try:
                shutil.rmtree(self.qdrant_path)
            except Exception as e:
                logger.error(f"Error removing Qdrant storage: {e}")
        
        # Ensure directory exists
        os.makedirs(self.qdrant_path, exist_ok=True)
        
        # Initialize Qdrant client
        try:
            logger.info(f"Initializing Qdrant client with local storage: {self.qdrant_path}")
            self.client = QdrantClient(
                path=self.qdrant_path,
                force_disable_check_same_thread=True
            )
            
            # Create collection if it doesn't exist
            self._create_collection_if_not_exists()
            
        except Exception as e:
            logger.error(f"Error initializing Qdrant: {e}")
            self._handle_initialization_error()
        
        # Initialize Langchain Qdrant wrapper
        self.vector_store = Qdrant(
            client=self.client,
            collection_name=self.collection_name,
            embeddings=self.embeddings_manager.get_embeddings()
        )
        
        logger.info("Qdrant vector store initialized successfully")
    
    def _create_collection_if_not_exists(self):
        """Create a new collection if it doesn't already exist"""
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if self.collection_name not in collection_names:
            logger.info(f"Creating new collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=self.embeddings_manager.get_dimension(),
                    distance=qdrant_models.Distance.COSINE
                )
            )
    
    def _handle_initialization_error(self):
        """Handle initialization errors by resetting storage"""
        logger.info("Attempting to resolve by resetting Qdrant storage...")
        try:
            shutil.rmtree(self.qdrant_path)
            os.makedirs(self.qdrant_path, exist_ok=True)
            self.client = QdrantClient(
                path=self.qdrant_path, 
                force_disable_check_same_thread=True
            )
            self._create_collection_if_not_exists()
        except Exception as reset_error:
            logger.critical(f"Could not initialize or reset Qdrant: {reset_error}")
            raise RuntimeError("Unable to initialize vector store") from reset_error
    
    def add_documents(self, documents):
        """Add Langchain documents to the vector store"""
        try:
            self.vector_store.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to the vector store")
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            raise
    
    def similarity_search_with_score(self, query, k=None, score_threshold=None):
        """
        Perform enhanced similarity search with scores and optional threshold filtering
        
        Args:
            query (str): The query text to search for
            k (int): Number of results to return (default: from config)
            score_threshold (float): Minimum similarity score (0-1) to include in results
            
        Returns:
            list: List of (document, score) tuples
        """
        if k is None:
            k = config.MAX_SEARCH_RESULTS
            
        # Get initial results
        results = self.vector_store.similarity_search_with_score(query, k=k)
        
        # Apply score threshold if provided
        if score_threshold is not None:
            results = [(doc, score) for doc, score in results if score >= score_threshold]
            
        return results
    
    def get_retriever(self, search_kwargs=None):
        """Return an enhanced retriever for this vector store"""
        if search_kwargs is None:
            search_kwargs = {
                "k": config.MAX_SEARCH_RESULTS,
                "score_threshold": 0.1  # Default minimum similarity score
            }
            
        return self.vector_store.as_retriever(
            search_type="similarity_score_threshold",  # Use score threshold retrieval
            search_kwargs=search_kwargs
        )
    
    def delete_by_metadata(self, metadata_key, metadata_value):
        """Delete documents by metadata field"""
        filter_condition = qdrant_models.FieldCondition(
            key=metadata_key,
            match=qdrant_models.MatchValue(value=metadata_value)
        )
        
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[filter_condition]
                    )
                )
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting documents with {metadata_key}={metadata_value}: {e}")
            return False
    
    def count_vectors(self):
        """Count vectors in the collection"""
        try:
            return self.client.count(collection_name=self.collection_name).count
        except Exception as e:
            logger.error(f"Error counting vectors: {e}")
            return 0
            
    def search_documents(self, query, k=5, include_metadata=True, score_threshold=0.1):
        """
        Enhanced document search with metadata and threshold filtering
        
        This provides a more controlled and detailed search than the basic similarity_search
        """
        try:
            # Get embeddings for the query
            query_vector = self.embeddings_manager.get_embeddings().embed_query(query)
            
            # Search with Qdrant client directly for more control
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=k,
                with_payload=include_metadata,
                score_threshold=score_threshold
            )
            
            # Process and format results
            results = []
            for scored_point in search_result:
                # Extract content and metadata
                point_id = scored_point.id
                score = scored_point.score
                metadata = scored_point.payload.get("metadata", {})
                content = scored_point.payload.get("page_content", "")
                source = metadata.get("source", "Unknown Source")
                
                # Format result
                result = {
                    "id": str(point_id),
                    "score": score,
                    "content": content,
                    "source": source,
                    "metadata": metadata
                }
                
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Error in enhanced document search: {e}")
            return []